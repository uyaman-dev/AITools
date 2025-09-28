"""Vector store service for managing and querying document embeddings."""
from typing import List, Dict, Any, Optional
import os
import logging

from langchain_chroma import Chroma
from langchain.schema import Document
from langchain.embeddings.base import Embeddings

from ..config.settings import VECTOR_STORE_DIR
from ..models.schema import SearchResult

logger = logging.getLogger(__name__)

class VectorStoreService:
    """Service for managing and querying document embeddings in a vector store."""
    
    def __init__(self, 
                 embedding_model: Embeddings,
                 persist_directory: Optional[str] = None):
        """Initialize the vector store service.
        
        Args:
            embedding_model: Embedding model to use
            persist_directory: Directory to persist the vector store
        """
        self.embedding_model = embedding_model
        self.persist_directory = persist_directory or VECTOR_STORE_DIR
        self._vector_store = None
        
        # Create persist directory if it doesn't exist
        os.makedirs(self.persist_directory, exist_ok=True)
    
    @property
    def vector_store(self) -> Chroma:
        """Lazy load the vector store."""
        if self._vector_store is None:
            self._load_vector_store()
        return self._vector_store
    
    def _load_vector_store(self):
        """Load or create the vector store."""
        try:
            # Try to load existing vector store
            if os.path.exists(os.path.join(self.persist_directory, "chroma.sqlite3")):
                logger.info("Loading existing vector store")
                self._vector_store = Chroma(
                    persist_directory=self.persist_directory,
                    embedding_function=self.embedding_model
                )
            else:
                logger.info("Creating new vector store")
                self._vector_store = Chroma(
                    embedding_function=self.embedding_model,
                    persist_directory=self.persist_directory
                )
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            raise
    
    def add_documents(self, documents: List[Document]) -> None:
        """Add documents to the vector store.
        
        Args:
            documents: List of Document objects to add
        """
        try:
            if not documents:
                logger.warning("No documents provided to add to vector store")
                return
                
            logger.info(f"Adding {len(documents)} documents to vector store")
            
            # Log first document structure for debugging
            if documents:
                first_doc = documents[0]
                logger.debug(f"First document content type: {type(first_doc.page_content)}")
                logger.debug(f"First document metadata: {first_doc.metadata}")
                logger.debug(f"First 100 chars of content: {first_doc.page_content[:100]}...")
            
            # Try to embed a sample text to test the embedding model
            try:
                sample_text = "This is a test document"
                embedding = self.embedding_model.embed_query(sample_text)
                logger.info(f"Successfully generated test embedding. Shape: {len(embedding) if embedding is not None else 'None'}")
            except Exception as e:
                logger.error(f"Failed to generate test embedding: {e}")
                raise
                
            # Add documents to vector store
            self.vector_store.add_documents(documents)
            logger.info(f"Successfully added {len(documents)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Error adding documents to vector store: {e}", exc_info=True)
            raise
    
    def similarity_search(self, query: str, k: int = 5, **kwargs) -> SearchResult:
        """Perform a similarity search on the vector store.
        
        Args:
            query: Query text
            k: Number of results to return
            **kwargs: Additional arguments to pass to the similarity search
            
        Returns:
            SearchResult containing relevant documents and metadata
        """
        try:
            # Perform the search
            docs = self.vector_store.similarity_search(query, k=k, **kwargs)
            
            # Extract relevant information
            tables = set()
            context = []
            
            for doc in docs:
                metadata = doc.metadata
                if metadata.get("table_name"):
                    tables.add(metadata["table_name"])
                
                context.append({
                    "content": doc.page_content,
                    "metadata": metadata,
                    "score": doc.metadata.get("score", 0.0)
                })
            
            return SearchResult(
                tables=list(tables),
                context=context
            )
            
        except Exception as e:
            logger.error(f"Error performing similarity search: {e}")
            raise
    
    def delete_collection(self) -> None:
        """Delete the entire vector store collection."""
        try:
            self.vector_store.delete_collection()
            self.vector_store.persist()
            logger.info("Vector store collection deleted")
        except Exception as e:
            logger.error(f"Error deleting vector store collection: {e}")
            raise
    
    def get_document_count(self) -> int:
        """Get the number of documents in the vector store."""
        try:
            return self.vector_store._collection.count()
        except Exception as e:
            logger.error(f"Error getting document count: {e}")
            return 0
