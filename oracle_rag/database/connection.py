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
                 fetch_all: bool = True, config: Optional[Dict[str, Any]] = None,
                 connection=None):
    """Execute a query and return the results.
    
    Args:
        query: SQL query to execute
        params: Optional parameters for the query (can be tuple, dict, or list)
        fetch_all: If True, fetch all results; if False, fetch one
        config: Optional database configuration (only used if connection is not provided)
        connection: Optional existing database connection to use
        
    Returns:
        Query results as a list of dictionaries or a single dictionary if fetch_all is False
        Returns None if no results and fetch_all is False
    """
    if config is None:
        config = DB_CONFIG
    
    def execute_with_connection(conn):
        with conn.cursor() as cursor:
            # Convert params to the correct format if it's a list
            if isinstance(params, list):
                params_dict = {f"p{i+1}": val for i, val in enumerate(params)}
            else:
                params_dict = params or {}
            
            # Execute the query
            cursor.execute(query, params_dict)
            
            # If it's a SELECT query, fetch results
            if cursor.description is not None:
                columns = [col[0] for col in cursor.description]
                if fetch_all:
                    results = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in results]
                else:
                    result = cursor.fetchone()
                    return dict(zip(columns, result)) if result else None
            
            # For non-SELECT queries, return rowcount
            return cursor.rowcount
    
    try:
        if connection is not None:
            # Use the provided connection
            return execute_with_connection(connection)
        else:
            # Create a new connection
            with get_db_connection(config) as conn:
                return execute_with_connection(conn)
                
    except oracledb.Error as e:
        logger.error(f"Error executing query: {e}")
        raise
