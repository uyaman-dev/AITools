"""Main service for the Oracle DB Metadata LLM application."""
import os
import logging
from typing import Dict, Any, Optional, List
import json
from pathlib import Path

from langchain.schema import Document

from .config.settings import DB_CONFIG, VECTOR_STORE_DIR
from .database.metadata import MetadataExtractor
from .models.schema import SchemaMetadata, QueryResult, SQLGenerationResult
from .services.embeddings import EmbeddingService
from .services.vector_store import VectorStoreService
from .services.llm import LLMService
from .database.connection import get_db_connection

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OracleMetadataLLM:
    """Main service class for the Oracle DB Metadata LLM application."""
    
    def __init__(self, schema_name: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize the service.
        
        Args:
            schema_name: Name of the database schema to work with
            config: Optional configuration overrides for database connection
        """
        self.config = {**DB_CONFIG, **(config or {})}
        self.schema_name = schema_name or self.config.get('user')
        
        # Initialize services
        self.embedding_service = EmbeddingService()
        self.llm_service = LLMService()
        self.vector_store = VectorStoreService(
            embedding_model=self.embedding_service.model
        )
        
        # Initialize metadata extractor with a connection
        self.db_connection = None
        self.metadata_extractor = None
        
        # Cache for schema metadata
        self._schema_metadata = None
    
    def extract_metadata(self, force_refresh: bool = False) -> SchemaMetadata:
        """Extract and cache database metadata.
        
        Args:
            force_refresh: If True, force a refresh of the metadata
            
        Returns:
            SchemaMetadata object containing the database schema
        """
        if self._schema_metadata is None or force_refresh:
            logger.info(f"Extracting metadata for schema: {self.schema_name}")
            
            # Create a new connection for the metadata extractor
            with get_db_connection() as conn:
                # Initialize the metadata extractor with the connection
                self.metadata_extractor = MetadataExtractor(
                    schema_name=self.schema_name,
                    connection=conn
                )
                # Extract metadata using the single connection
                self._schema_metadata = self.metadata_extractor.get_schema_metadata()
                logger.info(f"Extracted metadata for {len(self._schema_metadata.tables)} tables")
                
        return self._schema_metadata
    
    def prepare_documents(self, metadata: SchemaMetadata) -> List[Document]:
        """Prepare documents for the vector store from database metadata.
        
        Args:
            metadata: SchemaMetadata object
            
        Returns:
            List of Document objects for the vector store
        """
        documents = []
        
        for table_name, table in metadata.tables.items():
            # Table level document
            table_doc = Document(
                page_content=(
                    f"Table: {table_name}\n"
                    f"Description: {table.comment or 'No description available'}\n"
                    f"Primary Keys: {', '.join(pk.column_name for pk in table.primary_keys)}\n"
                    f"Columns: {', '.join(col.name for col in table.columns)}"
                ),
                metadata={
                    "type": "table",
                    "table_name": table_name,
                    "description": table.comment or ""
                }
            )
            documents.append(table_doc)
            
            # Column level documents
            for col in table.columns:
                col_metadata = {
                    "type": "column",
                    "table_name": table_name,
                    "column_name": col.name,
                    "data_type": col.data_type,
                    "is_primary": any(pk.column_name == col.name for pk in table.primary_keys),
                    "is_foreign": any(fk.column_name == col.name for fk in table.foreign_keys)
                }
                
                col_doc = Document(
                    page_content=(
                        f"Column: {table_name}.{col.name}\n"
                        f"Type: {col.data_type}\n"
                        f"Nullable: {col.nullable}\n"
                        f"Description: {col.comment or 'No description available'}"
                    ),
                    metadata=col_metadata
                )
                documents.append(col_doc)
                
        return documents
    
    def build_vector_store(self, force_rebuild: bool = False) -> None:
        """Build or update the vector store with schema information.
        
        Args:
            force_rebuild: If True, force a complete rebuild of the vector store
        """
        if force_rebuild and os.path.exists(VECTOR_STORE_DIR):
            logger.info("Clearing existing vector store")
            self.vector_store.delete_collection()
        
        # Extract metadata and prepare documents
        metadata = self.extract_metadata()
        documents = self.prepare_documents(metadata)
        
        # Add documents to vector store
        self.vector_store.add_documents(documents)
        logger.info(f"Added {len(documents)} documents to vector store")
    
    def generate_sql(self, question: str) -> SQLGenerationResult:
        """Generate SQL from a natural language question.
        
        Args:
            question: Natural language question
            
        Returns:
            SQLGenerationResult containing the generated SQL and metadata
        """
        # First, find relevant schema information
        search_result = self.vector_store.similarity_search(question)
        
        # Format context for the prompt
        schema_context = "\n\n".join([
            f"{item['content']}\n---" 
            for item in search_result.context
        ])
        
        # Generate SQL using the LLM
        return self.llm_service.generate_sql(
            question=question,
            schema_context=schema_context,
            tables=search_result.tables
        )
    
    def execute_query(self, sql: str) -> QueryResult:
        """Execute a SQL query and return the results.
        
        Args:
            sql: SQL query to execute
            
        Returns:
            QueryResult containing the query results or error information
        """
        from .database.connection import execute_query as db_execute_query
        
        try:
            result = db_execute_query(sql, config=self.config)
            return QueryResult(
                success=True,
                columns=result[0].keys() if result else [],
                rows=result,
                row_count=len(result)
            )
        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return QueryResult(
                success=False,
                error=str(e),
                sql=sql
            )
    
    def process_natural_language(self, question: str) -> Dict[str, Any]:
        """Process a natural language question and return the results.
        
        Args:
            question: Natural language question
            
        Returns:
            Dictionary containing the SQL, results, and metadata
        """
        # Generate SQL
        gen_result = self.generate_sql(question)
        
        # Execute the query
        query_result = self.execute_query(gen_result.sql)
        
        # Generate explanation
        explanation = self.llm_service.explain_sql(
            sql=gen_result.sql,
            question=question
        )
        
        return {
            "question": question,
            "sql": gen_result.sql,
            "explanation": explanation,
            "success": query_result.success,
            "error": query_result.error,
            "columns": query_result.columns,
            "rows": query_result.rows,
            "row_count": query_result.row_count,
            "tables": gen_result.tables,
            "context": gen_result.context
        }


def main():
    """Main entry point for the application."""
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Oracle DB Metadata LLM")
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Extract command
    extract_parser = subparsers.add_parser('extract', help='Extract database metadata')
    extract_parser.add_argument('--schema', help='Schema name', default=None)
    extract_parser.add_argument('--output', help='Output file', default='schema_metadata.json')
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Run a natural language query')
    query_parser.add_argument('question', help='Natural language question')
    query_parser.add_argument('--schema', help='Schema name', default=None)
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build the vector store')
    build_parser.add_argument('--schema', help='Schema name', default=None)
    build_parser.add_argument('--force', action='store_true', help='Force rebuild')
    
    args = parser.parse_args()
    
    # Initialize the service
    service = OracleMetadataLLM(schema_name=args.schema)
    
    if args.command == 'extract':
        # Extract and save metadata
        metadata = service.extract_metadata(force_refresh=True)
        with open(args.output, 'w') as f:
            json.dump(metadata.__dict__, f, indent=2, default=lambda x: x.__dict__)
        print(f"Metadata saved to {args.output}")
        
    elif args.command == 'build':
        # Build the vector store
        service.build_vector_store(force_rebuild=args.force)
        print("Vector store built successfully")
        
    elif args.command == 'query':
        # Process a natural language query
        result = service.process_natural_language(args.question)
        
        print("\n=== SQL Query ===")
        print(result['sql'])
        
        if not result['success']:
            print("\n=== Error ===")
            print(result['error'])
            return
            
        print(f"\n=== Results ({result['row_count']} rows) ===")
        if result['rows']:
            # Print column headers
            print(" | ".join(result['columns']))
            print("-" * 50)
            
            # Print first 5 rows
            for row in result['rows'][:5]:
                print(" | ".join(str(row.get(col, '')) for col in result['columns']))
            
            if len(result['rows']) > 5:
                print(f"... and {len(result['rows']) - 5} more rows")
        
        print("\n=== Explanation ===")
        print(result['explanation'])
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
