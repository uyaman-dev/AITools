"""Embedding service for generating and managing text embeddings."""
from typing import List, Dict, Any, Optional
import logging

from langchain_huggingface import HuggingFaceEmbeddings
from ..config.settings import EMBEDDING_MODEL

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating and managing text embeddings."""
    
    def __init__(self, model_name: Optional[str] = None):
        """Initialize the embedding service.
        
        Args:
            model_name: Name of the HuggingFace model to use for embeddings.
                       If not provided, uses the default from settings.
        """
        self.model_name = model_name or EMBEDDING_MODEL
        self._model = None
    
    @property
    def model(self):
        """Lazy load the embedding model."""
        if self._model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            try:
                self._model = HuggingFaceEmbeddings(
                    model_name=self.model_name,
                    model_kwargs={'device': 'cpu'},  # Use 'cuda' if GPU is available
                    encode_kwargs={'normalize_embeddings': True}
                )
                # Test the model with a simple embedding
                test_embedding = self._model.embed_query("test")
                logger.info(f"Successfully loaded embedding model. Test embedding shape: {len(test_embedding) if test_embedding is not None else 'None'}")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return self._model
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            return self.model.embed_documents(texts)
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
    
    def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query text.
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as a list of floats
        """
        try:
            return self.model.embed_query(text)
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            raise
