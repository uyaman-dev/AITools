"""Application settings and configuration."""
from pathlib import Path
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database settings
DB_CONFIG: Dict[str, str] = {
    "user": os.getenv("DB_USER", "user"),
    "password": os.getenv("DB_PASSWORD", "password"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "1521"),
    "service_name": os.getenv("DB_SERVICE", "XE"),
}

# Vector store settings
VECTOR_STORE_DIR = os.getenv("VECTOR_STORE_DIR", str(BASE_DIR / "vector_store"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# LLM settings
LLM_SETTINGS = {
    "openai": {
        "model_name": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo-instruct"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1000")),
        "request_timeout": int(os.getenv("LLM_REQUEST_TIMEOUT", "30")),  # seconds
    },
    "gemini": {
        "model_name": os.getenv("GEMINI_MODEL", "gemini-2.5-pro"),
        "temperature": float(os.getenv("LLM_TEMPERATURE", "0.3")),
        "max_tokens": int(os.getenv("LLM_MAX_TOKENS", "1000")),
        "request_timeout": int(os.getenv("LLM_REQUEST_TIMEOUT", "30")),  # seconds
    }
}

# Application settings
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
MAX_RESULTS = int(os.getenv("MAX_RESULTS", "5"))

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": os.getenv("LOG_LEVEL", "INFO"),
        },
    },
    "root": {
        "handlers": ["console"],
        "level": os.getenv("LOG_LEVEL", "INFO"),
    },
}

def get_dsn() -> str:
    """Get the DSN string for Oracle connection."""
    return f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['service_name']}"
