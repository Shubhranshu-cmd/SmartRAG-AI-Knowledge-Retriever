import json
import threading
import hashlib
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional

import requests

from openai import OpenAI
from huggingface_hub import InferenceClient

from src.config import Config
from log.logger import logger

try:
    import torch
    torch_available = True
except ImportError:
    torch_available = False

CACHE_DIR = Path("data/embedding_cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
logger.info(f"Embedding cache directory: {CACHE_DIR}")


def get_file_hash(file_path: Path) -> str:
    """Generate hash of file content"""
    try:
        file_hash = hashlib.md5(file_path.read_bytes()).hexdigest()
        return file_hash
    except Exception as exc:
        logger.warning(f"Failed to compute file hash: {exc}")
        return ""


def get_cached_embeddings(file_hash: str, chunk_hashes: List[str]) -> Optional[Dict[str, Any]]:
    """Retrieve cached embeddings if available"""
    try:
        if not file_hash:
            return None
        
        cache_file = CACHE_DIR / f"{file_hash}.pkl"
        if not cache_file.exists():
            logger.debug(f"Cache miss: {file_hash}")
            return None
        
        cache_data = pickle.load(open(cache_file, 'rb'))
        
        if all(h in cache_data.get('chunk_hashes', {}) for h in chunk_hashes):
            logger.info(f"✓ Cache hit: {file_hash} (all {len(chunk_hashes)} chunks found)")
            return cache_data
        else:
            logger.debug(f"Partial cache hit for {file_hash}, re-computing...")
            return None
    except Exception as exc:
        logger.debug(f"Cache retrieval failed: {exc}")
        return None


def save_cached_embeddings(file_hash: str, embeddings: "Any", chunks: List[str]) -> None:
    """Save embeddings to cache"""
    try:
        if not file_hash or file_hash == "":
            return
        
        chunk_hashes = [hashlib.md5(c.encode()).hexdigest() for c in chunks]
        cache_file = CACHE_DIR / f"{file_hash}.pkl"
        
        cache_data = {
            'embeddings': embeddings,
            'chunk_hashes': {h: i for i, h in enumerate(chunk_hashes)},
            'timestamp': Path(cache_file).stat().st_mtime if cache_file.exists() else 0
        }
        
        pickle.dump(cache_data, open(cache_file, 'wb'))
        logger.info(f"✓ Cached {len(chunks)} embeddings to {cache_file}")
    except Exception as exc:
        logger.warning(f"Failed to cache embeddings: {exc}")

class FAISSStore:
    """Thread-safe vector storage layer with error handling."""

    def __init__(self, dim: int = 384):
        self.dim = dim
        self._lock = threading.Lock()
        config = Config()
        config.INDEX_DIR.mkdir(parents=True, exist_ok=True)

        try:
            import faiss
        except ImportError as exc:
            raise RuntimeError(
                "Failed to import faiss. Install faiss-cpu: pip install faiss-cpu"
            ) from exc
        self.faiss = faiss

        try:
            import numpy as np
        except ImportError as exc:
            raise RuntimeError(
                "Failed to import numpy. Install numpy: pip install numpy"
            ) from exc
        self.np = np

        self.index_path = config.INDEX_DIR / "vectors.index"
        self.metadata_path = config.INDEX_DIR / "metadata.json"

        try:
            if self.index_path.exists():
                self.index = self.faiss.read_index(str(self.index_path))
                logger.info(f"Loaded FAISS index from {self.index_path}")
            else:
                self.index = self.faiss.IndexFlatL2(dim)
                logger.info(f"Created new FAISS index with dimension {dim}")

            if self.metadata_path.exists():
                self.metadata = json.loads(
                    self.metadata_path.read_text(encoding="utf-8")
                )
                logger.info(f"Loaded {len(self.metadata)} metadata entries")
            else:
                self.metadata = []
        except Exception as exc:
            logger.error(f"Failed to initialize FAISS store: {exc}", exc_info=True)
            raise

    def add(self, vectors: "np.ndarray", documents: List[Dict[str, Any]]) -> None:
        """Thread-safe vector addition with validation"""
        if not vectors.size or not documents:
            logger.warning("Attempted to add empty vectors or documents")
            return
        
        with self._lock:
            try:
                vectors = self.np.asarray(vectors, dtype=self.np.float32)
                
                if vectors.shape[0] != len(documents):
                    raise ValueError(
                        f"Vector count ({vectors.shape[0]}) must match document count ({len(documents)})"
                    )
                
                self.index.add(vectors)
                self.metadata.extend(documents)
                self.save()
                logger.info(f"Added {len(documents)} vectors to store")
            except Exception as exc:
                logger.error(f"Failed to add vectors: {exc}", exc_info=True)
                raise

    def search(self, vector: "np.ndarray", k: int = 5) -> List[Dict[str, Any]]:
        """Thread-safe search with validation"""
        if not self.metadata:
            logger.debug("Search on empty store")
            return []
        
        with self._lock:
            try:
                vector = self.np.asarray([vector], dtype=self.np.float32)
                k = min(k, len(self.metadata))
                
                if k <= 0:
                    return []
                
                _, indices = self.index.search(vector, k)
                results = [
                    self.metadata[int(idx)] 
                    for idx in indices[0] 
                    if 0 <= int(idx) < len(self.metadata)
                ]
                return results
            except Exception as exc:
                logger.error(f"Search failed: {exc}", exc_info=True)
                return []

    def save(self) -> None:
        """Save index and metadata with error handling"""
        try:
            self.faiss.write_index(self.index, str(self.index_path))
            self.metadata_path.write_text(
                json.dumps(self.metadata, ensure_ascii=False),
                encoding="utf-8"
            )
            logger.debug("FAISS store saved successfully")
        except Exception as exc:
            logger.error(f"Failed to save FAISS store: {exc}", exc_info=True)
            raise

    def clear(self) -> None:
        """Clear store data with confirmation"""
        with self._lock:
            self.index = self.faiss.IndexFlatL2(self.dim)
            self.metadata = []
            self.save()
            logger.warning("FAISS store cleared")


class HFResponseMessage:
    def __init__(self, text: str):
        self.content = text


class HFResponseChoice:
    def __init__(self, text: str):
        self.message = HFResponseMessage(text)


class HFResponse:
    def __init__(self, text: str):
        self.choices = [HFResponseChoice(text)]

class HFClientAdapter:
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.api = InferenceClient(token=Config().HUGGINGFACE_API_KEY)

    class Chat:
        def __init__(self, api: InferenceClient, model_id: str):
            self.api = api
            self.model_id = model_id

        class Completions:
            def __init__(self, api: InferenceClient, model_id: str):
                self.api = api
                self.model_id = model_id

            def create(self, model: str, messages: List[Dict[str, str]], temperature: float = 0.3, max_tokens: int = 512):
                prompt = "\n".join(
                    f"{m['role'].upper()}: {m['content']}" for m in messages
                )
                try:
                    output = self.api.text_generation(model=self.model_id, inputs=prompt, parameters={"max_new_tokens": max_tokens, "temperature": temperature})
                except TypeError:
                    output = self.api.text_generation(self.model_id, inputs=prompt, parameters={"max_new_tokens": max_tokens, "temperature": temperature})

                text = None
                if isinstance(output, str):
                    text = output
                elif isinstance(output, dict):
                    text = output.get("generated_text") or output.get("text") or str(output)
                elif isinstance(output, list) and len(output) > 0 and isinstance(output[0], dict):
                    text = output[0].get("generated_text") or output[0].get("text") or str(output[0])
                else:
                    text = str(output)

                return HFResponse(text)

        @property
        def completions(self):
            return HFClientAdapter.Chat.Completions(self.api, self.model_id)

    @property
    def chat(self):
        return HFClientAdapter.Chat(self.api, self.model_id)

class AIService:
    """Thread-safe AI service with proper error handling"""
    _client = None
    _embedder = None
    store = None
    lock = threading.Lock()

    @classmethod
    def get_openrouter_client(cls):
        """Get or create OpenRouter client"""
        with cls.lock:
            if cls._client is None:
                try:
                    config = Config()
                    api_key = cls.get_api_key()
                    cls._client = OpenAI(
                        base_url=config.API_URL,
                        api_key=api_key,
                        timeout=30.0
                    )
                    logger.info("OpenRouter client initialized")
                except Exception as exc:
                    logger.error(f"Failed to initialize OpenRouter client: {exc}")
                    raise
            return cls._client

    @classmethod
    def get_client_for_model(cls, model_name: str):
        """Get appropriate client for model"""
        try:
            config = Config()
            if model_name.startswith("hf_") and config.HUGGINGFACE_API_KEY:
                return HFClientAdapter(model_name)
            return cls.get_openrouter_client()
        except Exception as exc:
            logger.error(f"Failed to get client for model {model_name}: {exc}")
            raise

    @classmethod
    def get_embedder(cls):
        """Get or create embedder"""
        with cls.lock:
            if cls._embedder is None:
                try:
                    from sentence_transformers import SentenceTransformer
                    embed_model = Config.get_embed_model()
                    cls._embedder = SentenceTransformer(embed_model)
                    logger.info(f"Embedder initialized with model {embed_model}")
                except ImportError as exc:
                    logger.error("sentence-transformers not installed")
                    raise RuntimeError(
                        "Install sentence-transformers: pip install sentence-transformers"
                    ) from exc
                except Exception as exc:
                    logger.error(f"Failed to initialize embedder: {exc}")
                    raise
            return cls._embedder

    @staticmethod
    def download_file(url: str, timeout: int = 30) -> Path:
        """Download file from URL with timeout and validation"""
        try:
            logger.info(f"Downloading file from {url}")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            filename = Path(url).name
            if not filename or "." not in filename:
                filename = "downloaded_file.txt"
            
            save_path = Config().UPLOAD_DIR / filename
            save_path.write_bytes(response.content)
            logger.info(f"File saved to {save_path}")
            return save_path
        except requests.Timeout:
            logger.error(f"Download timeout for {url}")
            raise
        except Exception as exc:
            logger.error(f"Download failed for {url}: {exc}")
            raise

    @staticmethod
    def extract_text(path: Path) -> str:
        """Extract text from various formats with error handling"""
        try:
            if not path.exists():
                raise FileNotFoundError(f"File not found: {path}")
            
            extension = path.suffix.lower()
            
            if extension == ".pdf":
                try:
                    try:
                        from pypdf import PdfReader
                    except ImportError as exc:
                        logger.error("PDF extraction failed because pypdf is not installed")
                        raise ImportError(
                            "pypdf is required to read .pdf files. Install it with: pip install pypdf"
                        ) from exc

                    reader = PdfReader(path)
                    text = " ".join(
                        (page.extract_text() or "") for page in reader.pages
                    )
                    return text.strip()
                except Exception as exc:
                    logger.error(f"PDF extraction failed: {exc}")
                    raise
            
            elif extension == ".docx":
                try:
                    import docx
                except ImportError as exc:
                    logger.error("DOCX extraction failed because python-docx is not installed")
                    raise ImportError(
                        "python-docx is required to read .docx files. Install it with: pip install python-docx"
                    ) from exc
                try:
                    document = docx.Document(path)
                    text = "\n".join(
                        paragraph.text for paragraph in document.paragraphs
                    )
                    return text.strip()
                except Exception as exc:
                    logger.error(f"DOCX extraction failed: {exc}")
                    raise
            else:
                text = path.read_text(encoding="utf-8", errors="ignore")
                return text.strip()
        
        except Exception as exc:
            logger.error(f"Text extraction failed for {path}: {exc}")
            raise

    @staticmethod
    def chunk_text(
        text: str,
        chunk_size: int = 2500,
        overlap: int = 100,
        min_chunk_length: int = 50
    ) -> List[str]:
        """Chunk text efficiently with validation and filtering"""
        if not text or not text.strip():
            logger.warning("Attempted to chunk empty text")
            return []
        
        if chunk_size <= 0 or overlap < 0:
            raise ValueError("Invalid chunk parameters")
        
        chunks = []
        start = 0
        
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk = text[start:end].strip()
            if len(chunk) >= min_chunk_length:
                chunks.append(chunk)
            start += chunk_size - overlap
        
        logger.info(f"Created {len(chunks)} text chunks from {len(text):,} characters")
        return chunks

    @classmethod
    def ingest_document(cls, path: Path, store: FAISSStore) -> int:
        """Ingest document into vector store with caching and GPU optimization"""
        with cls.lock:
            try:
                logger.info(f"⏳ Ingesting document: {path} (step 1/5: computing hash)")
                
                file_hash = get_file_hash(path)
                
                logger.info(f"⏳ Step 2/5: extracting text from {path.name}")
                text = cls.extract_text(path)
                if not text:
                    logger.warning(f"No text extracted from {path}")
                    return 0
                
                logger.info(f"✓ Extracted {len(text):,} characters (step 3/5: chunking text)")
                chunks = cls.chunk_text(text)
                if not chunks:
                    logger.warning(f"No chunks created from {path}")
                    return 0
                
                logger.info(f"✓ Created {len(chunks)} chunks (step 4/5: checking cache...)")
                
                chunk_hashes = [hashlib.md5(c.encode()).hexdigest() for c in chunks]
                cache_data = get_cached_embeddings(file_hash, chunk_hashes)
                
                if cache_data:
                    embeddings = cache_data['embeddings']
                    logger.info(f"⚡ Using cached embeddings (saving {len(chunks)} embedding computations!)")
                else:
                    logger.info(f"📊 Generating embeddings for {len(chunks)} chunks...")
                    embedder = cls.get_embedder()
                    
                    device = cls._get_device()
                    logger.debug(f"Using device: {device}")
                    
                    embeddings = embedder.encode(
                        chunks,
                        batch_size=32,
                        show_progress_bar=True,
                        device=device
                    )
                    
                    save_cached_embeddings(file_hash, embeddings, chunks)
                
                metadata = [
                    {
                        "content": chunk,
                        "source": path.name,
                        "chunk_id": i
                    }
                    for i, chunk in enumerate(chunks)
                ]
                
                logger.info(f"✓ Embeddings ready (step 5/5: indexing vectors)")
                store.add(embeddings, metadata)
                logger.info(f"✅ Successfully ingested {len(chunks)} chunks from {path}")
                return len(chunks)
            
            except Exception as exc:
                logger.error(f"Document ingestion failed: {exc}", exc_info=True)
                raise
    
    @staticmethod
    def _get_device() -> str:
        """Get optimal device for embeddings (GPU if available, else CPU)"""
        try:
            if torch_available and torch.cuda.is_available():
                device = "cuda"
                gpu_name = torch.cuda.get_device_name(0)
                logger.info(f"🚀 GPU detected: {gpu_name} (computing 5-10x faster!)")
                return device
        except Exception as exc:
            logger.debug(f"GPU check failed: {exc}")
        
        logger.info("💻 Using CPU for embeddings (GPU not available)")
        return "cpu"

    @classmethod
    def retrieve_context(
        cls,
        query: str,
        store: FAISSStore,
        k: int = 5
    ) -> str:
        """Retrieve relevant context using RAG"""
        try:
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            embedder = cls.get_embedder()
            query_embedding = embedder.encode(query)
            results = store.search(query_embedding, k)
            
            context = "\n\n".join(
                item.get("content", "") for item in results
            )
            
            logger.debug(f"Retrieved {len(results)} context items")
            return context
        
        except Exception as exc:
            logger.error(f"Context retrieval failed: {exc}")
            raise

    @classmethod
    def ask(
        cls,
        query: str,
        model: str,
        store: FAISSStore,
        temperature: float = 0.3,
        max_tokens: int = 512
    ) -> str:
        """Ask question with RAG context"""
        try:
            if not query or not query.strip():
                raise ValueError("Query cannot be empty")
            
            context = cls.retrieve_context(query, store)
            if not context.strip():
                logger.warning("No context retrieved for query")
                context = "No relevant context found."
            
            client = cls.get_client_for_model(model)
            
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful assistant. Answer using the provided context."
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion:\n{query}"
                    }
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            answer = response.choices[0].message.content
            logger.info("Query processed successfully")
            return answer
        
        except Exception as exc:
            logger.error(f"Query processing failed: {exc}", exc_info=True)
            raise