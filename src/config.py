import os
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, ClassVar

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import psutil

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class ModelTier:
    min_ram_gb: float
    model: str


MODELS = [
    ModelTier(1024, "Qwen/Qwen3-Embedding-8B"),
    ModelTier(512, "BAAI/bge-m3"),
    ModelTier(256, "jinaai/jina-embeddings-v3"),
    ModelTier(128, "intfloat/e5-mistral-7b-instruct"),
    ModelTier(64, "BAAI/bge-large-en-v1.5"),
    ModelTier(32, "nomic-ai/nomic-embed-text-v2"),
    ModelTier(16, "sentence-transformers/all-mpnet-base-v2"),
    ModelTier(8, "intfloat/e5-base-v2"),
    ModelTier(4, "sentence-transformers/all-MiniLM-L12-v2"),
    ModelTier(0.5, "sentence-transformers/all-MiniLM-L6-v2"),
]

ram_gb = psutil.virtual_memory().total / (1024 ** 3)

EMBED_MODEL = MODELS[-1].model
for tier in MODELS:
    if ram_gb >= tier.min_ram_gb:
        EMBED_MODEL = tier.model
        break

logger.info(f"📊 System RAM: {ram_gb:.1f}GB | Selected embedding model: {EMBED_MODEL}")

def get_embed_model() -> str:
    """Get embedding model, with override support"""
    env_model = os.getenv("EMBED_MODEL")
    if env_model:
        logger.info(f"⚙️ Using environment-specified embedding model: {env_model}")
        return env_model
    
    force_fast = os.getenv("FORCE_FAST_EMBED", "").lower() in ("true", "1", "yes")
    if force_fast:
        fast_model = "sentence-transformers/all-MiniLM-L6-v2"
        logger.info(f"⚡ Using fast embedding model: {fast_model} (FORCE_FAST_EMBED=true)")
        return fast_model
    
    return EMBED_MODEL

class Config(BaseSettings):
    """Secure configuration for RAG Support AI using Pydantic Settings"""

    PROJECT_NAME: ClassVar[str] = "Support AI"
    VERSION: ClassVar[str] = "1.3.7"
    DEBUG: bool = False

    OPENROUTER_API_KEY: str = ""
    HUGGINGFACE_API_KEY: str = ""

    API_URL: str = "https://openrouter.ai/api/v1"
    CURRENT_MODEL: str = "nvidia/nemotron-3-ultra-500b-a55b:free"

    # Paths
    UPLOAD_DIR: Path = Path("data/uploads")
    INDEX_DIR: Path = Path("data/index")
    LOG_DIR: Path = Path("logs")

    AVAILABLE_MODELS: ClassVar[List[str]] = [
        "openrouter/free",
        "openrouter/owl-alpha",
        "huggingface/transformers-1b:free",

        "deepseek/deepseek-r1",
        "deepseek/deepseek-r1-distill:free",
        "deepseek/deepseek-r1-distill-llama-70b:free",
        "deepseek-ai/DeepSeek-V3",
        "deepseek-ai/DeepSeek-V4-Pro",
        "deepseek-ai/DeepSeek-V4-Flash",
        "deepseek/deepseek-v4-flash:free",

        "qwen/qwen3-coder:free",
        "qwen/qwen3.5-omni",
        "Qwen/Qwen3.6-Plus",
        "qwen3/qwen3.6b:free",
        "Qwen/Qwen3.7-Max",
        "Qwen/Qwen3.7-Plus",
         
        "replit/replit-code-v1_5-3b",

        "nvidia/nemotron-3-super-120b-a12b:free",
        "nvidia/nemotron-3-ultra-500b-a55b:free",
        "nvidia/Nemotron-Nano-12B-v2-VL",

        "google/gemini-omni",
        "google/flan-t5-small",
        "google/gemini-3-deep-think",
        "google/gemini-3.1-pro",
        "google/gemini-3.1-flash-lite",
        "google/gemini-3.5-flash",
        "google/gemma-4-31b-it:free",

        "gpt-oss-120b:free",
        "openai:gpt-oss-120b:free",
        "openai/gpt-5.4-nano:free",
        "gpt-5.5b:free",
        "openai/gpt-5.5",
        "openai/gpt-5.5-pro",
        "openai/gpt-5.5-thinking",
        "openai/gpt-5.5-instant",

        "antropic/claude-2.3-100k:free",
        "anthropic/claude-4.3-1b:free",
        "anthropic/claude-sonnet-4-6",
        "anthropic/claude-opus-4.8",
        "anthropic/claude-fable-5",
        "anthropic/claude-mythos-5",

        "mistralai/Mistral-Medium-3.5",
        "mistralai/Mistral-Small-4",
        "mistralai/Mistral-Large-3",
        "mistral/mistral-7b-instruct-v0.1:free",
        "mistralai/mistral-small-3.1-24b-instruct:free",

        "xai/xai-3-7b:free",
        "x-ai/grok-4-3",
        "x-ai/grok-4-20-heavy",

        "meta/muse-spark",
        "llama-4-maverick:free",
        "meta-llama/llama-4-maverick:free",

        "moonshotai/Kimi-K2-Thinking",
        "moonshotai/kimi-k2.5",
        "moonshotai/kimi-k2.6",
        "moonshotai/kimi-k2.6:free",
        "moonshotai/kimi-k2.7-code",

        "microsoft/mai-thinking-1",
        "microsoft/mai-code-1-flash",
        "microsoft/phi-4-1.5b-it:free",

        "perplexity/sonar",

        "cohere/command-a",
        "CohereForAI/c4ai-command-a-plus",
        "cohere/command-xlarge-nightly:free",

        "nex-agi/nex-n2-pro:free",

        "zhipuai/glm-4.7-flash:free",

        "baidu/ernie-5.0",

        "bytedance-seed/seed-1.6",

        "minimax/minimax-m2.7",

        "tencent/hunyuan-large-3",

        "tii/falcon-3",

        "nousresearch/hermes-3-llama-3.1-405b:free",

        "bigscience/bloom-560m",

        "EleutherAI/gpt-neo-125M",

        "tiiuae/falcon-7b-instruct",

        "amazon/bedrock/amazon.titan-1b:free",

        "apple/avalon-1b:free",

        "samsung/phoenix-1b:free",

        "naver/clova-1b:free",
        "naver-clova-ix/HyperCLOVA-x-SEED-Think-32B",

        "lg/clairvoyant-1b:free",

        "ai21/ai21-studio-1b:free",
        "ai21labs/Jamba-Large-1.7",

        "ai-sage/Kandinsky-5.0",
        "ai-sage/GigaChat-3-Ultra-Preview",

        "sakana/sakana-1b:free",

        "aleph-alpha/luminous-supreme",
        "aleph-alpha/aleph-alpha-1b:free",

        "THUDM/glm-5.1",

        "XiaomiMiMo/MiMo-72B-A52B-RL",

        "sdaia/allam-1-13b-instruct",

        "LGAI-EXAONE/K-EXAONE-236B-A23B",

        "upstage/SOLAR-10.7B-Instruct",

        "pfnet/plamo-100b",

        "llm-jp/llm-jp-3-172b-instruct3",

        "sarvamai/sarvam-105b",

        "aisingapore/sea-lion-7b-instruct",

        "maritaca-ai/sabia-3",
    ]

    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"

    def __init__(self, **data):
        super().__init__(**data)
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.INDEX_DIR.mkdir(parents=True, exist_ok=True)
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def get_api_key(cls) -> str:
        """Safely retrieve API key from environment"""
        config = cls()
        key = config.OPENROUTER_API_KEY or config.HUGGINGFACE_API_KEY
        if not key:
            raise ValueError(
                "No API key configured. Set OPENROUTER_API_KEY or HUGGINGFACE_API_KEY environment variables."
            )
        return key

    @classmethod
    def get_available_models(cls) -> List[str]:
        return list(cls.AVAILABLE_MODELS)

    @classmethod
    def get_current_model(cls) -> str:
        env = os.getenv("CURRENT_MODEL")
        if env:
            return env
        return cls().CURRENT_MODEL

    @classmethod
    def get_api_url(cls) -> str:
        return cls().API_URL

    @classmethod
    def get_debug(cls) -> bool:
        return bool(cls().DEBUG)

    @classmethod
    def get_embed_model(cls) -> str:
        env = os.getenv("EMBED_MODEL")
        if env:
            return env
        return EMBED_MODEL

    @classmethod
    def get_default_model(cls) -> str:
        env = os.getenv("CURRENT_MODEL")
        if env:
            return env
        if os.getenv("OPENROUTER_API_KEY"):
            return cls.AVAILABLE_MODELS[0]
        if os.getenv("HUGGINGFACE_API_KEY"):
            return cls.AVAILABLE_MODELS[0]
        return "deepseek/deepseek-v4-flash:free"

    FEATURES: ClassVar[List[str]] = [
        "Document ingestion for PDF, DOCX, TXT, MD, and URL content",
        "Text extraction and preprocessing",
        "Embedding generation using SentenceTransformers",
        "FAISS-based vector storage and similarity search",
        "Retrieval-augmented generation (RAG) over indexed documents",
        "Context-aware question answering",
        "Multi-turn conversational chat",
        "Summarization, keyword extraction, and quiz generation",
        "Gradio UI for chat, analytics, and uploads",
        "Optional webcam object detection support",
        "Optional text-to-speech via gTTS",
        "Upload and index persistence",
        "Configurable model selection through environment settings",
        "Logging and error handling",
        "Multi-modal support for text, documents, and vision inputs",
    ]

def initialize(create_dirs: bool = True) -> None:
    config = Config()
    if create_dirs:
        for path in (config.UPLOAD_DIR, config.INDEX_DIR):
            path.mkdir(parents=True, exist_ok=True)

    if not (config.OPENROUTER_API_KEY or config.HUGGINGFACE_API_KEY):
        logger.warning(
            "No OPENROUTER_API_KEY or HUGGINGFACE_API_KEY found. External model calls will be disabled."
        )

    logger.info("%s v%s initialized successfully", Config.PROJECT_NAME, Config.VERSION)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )
    initialize()