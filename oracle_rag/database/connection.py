"""Database connection handling."""
from typing import Optional, Dict, Any, Union, List
import oracledb
from contextlib import contextmanager
import logging

from ..config.settings import DB_CONFIG, get_dsn

logger = logging.getLogger(__name__)

class DatabaseConnection:
    """Handles database connections and provides a context manager for transactions."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize with optional custom configuration."""
        self.config = config or DB_CONFIG
        self.connection = None
        
    def connect(self):
        """Establish a database connection using oracledb."""
        try:
            # thin mode
            self.connection = oracledb.connect(
                user=self.config['user'],
                password=self.config['password'],
                dsn=get_dsn()
            )
            logger.info("Database connection established using oracledb thin mode")
            return self.connection
        except oracledb.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise
    
    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Enter the runtime context related to this object."""
        return self.connect()
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context and close the connection."""
        self.close()


@contextmanager
def get_db_connection(config: Optional[Dict[str, Any]] = None):
    """Context manager for database connections.
    
    Example:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM employees")
            result = cursor.fetchall()
    """
    db = DatabaseConnection(config)
    connection = None
    try:
        connection = db.connect()
        yield connection
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        raise
    finally:
        if connection:
            db.close()


def execute_query(query: str, params: Optional[Union[tuple, dict, list]] = None, 
                 fetch_all: bool = True, config: Optional[Dict[str, Any]] = None) -> Union[List[Dict[str, Any]], Dict[str, Any], None]:
    """Execute a query and return the results.
    
    Args:
        query: SQL query to execute
        params: Optional parameters for the query (can be tuple, dict, or list)
        fetch_all: If True, fetch all results; if False, fetch one
        config: Optional database configuration
        
    Returns:
        Query results as a list of dictionaries or a single dictionary if fetch_all is False
        Returns None if no results and fetch_all is False
    """
    with get_db_connection(config) as conn:
        cursor = conn.cursor()
        try:
            # Execute the query with parameters
            if params is None:
                cursor.execute(query)
            else:
                cursor.execute(query, params)
            
            # Process results if this is a SELECT query
            if cursor.description:
                columns = [col[0] for col in cursor.description]
                if fetch_all:
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
                else:
                    row = cursor.fetchone()
                    return dict(zip(columns, row)) if row else None
            else:
                # For non-SELECT queries, commit the transaction
                conn.commit()
                return {"rowcount": cursor.rowcount}
                
        except oracledb.Error as e:
            conn.rollback()
            logger.error(f"Query failed: {query}\nError: {e}")
            raise
