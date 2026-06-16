import logging
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, validator

from src.config import Config
from services.faiss_store import FAISSStore, AIService

logger = logging.getLogger("support-ai")

class StoreManager:
    _instance = None
    _lock = None
    
    def __new__(cls):
        if cls._instance is None:
            import threading
            cls._lock = threading.Lock()
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        try:
            self.store = FAISSStore()
            AIService.store = self.store
            logger.info("FAISSStore initialized successfully")
            self._initialized = True
        except Exception as exc:
            logger.error(f"Failed to initialize FAISSStore: {exc}", exc_info=True)
            self.store = None
            self._initialized = True

store_manager = StoreManager()

class QueryRequest(BaseModel):
    question: str = Field(
        min_length=1,
        max_length=4000,
        description="User question"
    )
    context_override: Optional[str] = Field(
        default="",
        max_length=10000,
        description="Optional context for analysis"
    )
    model: Optional[str] = Field(
        default=None,
        description="Model to use for query"
    )
    temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Temperature for model sampling"
    )
    max_tokens: int = Field(
        default=2048,
        ge=1,
        le=4096,
        description="Maximum response tokens"
    )

    @validator('question')
    def validate_question(cls, v):
        """Sanitize question input"""
        if not v or not v.strip():
            raise ValueError("Question cannot be empty or whitespace")
        return v.strip()

    @validator('context_override')
    def validate_context(cls, v):
        """Sanitize context input"""
        if v:
            return v.strip()
        return ""

class QueryResponse(BaseModel):
    status: str = Field(description="Response status")
    answer: str = Field(description="Model response")
    model: str = Field(description="Model used")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    logger.info(f"Starting {Config.PROJECT_NAME} v{Config.VERSION}")
    yield
    logger.info("Shutting down application")

app = FastAPI(
    title=Config.PROJECT_NAME,
    version=Config.VERSION,
    description="Support AI - RAG-powered document analysis API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    lifespan=lifespan
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"]
)

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint information"""
    return {
        "status": "running",
        "service": Config.PROJECT_NAME,
        "version": Config.VERSION,
        "endpoints": ["/docs", "/health", "/ask", "/analyze"]
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    try:
        store_available = store_manager.store is not None
        return {
            "status": "healthy",
            "service": Config.PROJECT_NAME,
            "version": Config.VERSION,
            "store_available": store_available,
            "debug": Config.get_debug()
        }
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service health check failed"
        )

@app.post("/ask", response_model=QueryResponse, tags=["Query"])
async def ask_api(req: QueryRequest):
    """Ask a question with RAG context"""
    model = req.model or Config.get_current_model()
    
    if model not in Config.AVAILABLE_MODELS and not Config.get_debug():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model}' not available. Choose from: {Config.AVAILABLE_MODELS}"
        )
    
    try:
        if not store_manager.store:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Vector store not initialized"
            )
        
        answer = AIService.ask(
            query=req.question,
            model=model,
            store=store_manager.store,
            temperature=req.temperature,
            max_tokens=req.max_tokens
        )
        
        return QueryResponse(
            status="success",
            answer=answer,
            model=model
        )
    
    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        logger.exception(f"Query failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query processing failed. Check server logs for details."
        )

@app.post("/analyze", response_model=QueryResponse, tags=["Analysis"])
async def analyze_document(req: QueryRequest):
    """Analyze document with specified model"""
    model = req.model or Config.get_current_model()
    
    if model not in Config.AVAILABLE_MODELS and not Config.get_debug():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model '{model}' not available"
        )
    
    try:
        if not req.context_override:
            raise ValueError("Context required for analysis")
        
        client = AIService.get_client_for_model(model)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a senior analyst. Provide concise, structured markdown output."
                },
                {
                    "role": "user",
                    "content": f"Task:\n{req.question}\n\nContext:\n{req.context_override}"
                }
            ],
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        
        answer = response.choices[0].message.content
        return QueryResponse(
            status="success",
            answer=answer,
            model=model
        )
    
    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as exc:
        logger.exception(f"Analysis failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analysis failed. Check server logs."
        )