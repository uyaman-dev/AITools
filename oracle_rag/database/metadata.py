"""Database metadata extraction utilities."""
from typing import Dict, List, Any, Optional
import logging

from .connection import execute_query, get_db_connection
from ..models.schema import (
    TableMetadata, 
    ColumnMetadata, 
    ForeignKey, 
    PrimaryKey,
    SchemaMetadata
)

logger = logging.getLogger(__name__)

class MetadataExtractor:
    """Extracts metadata from a database schema."""
    
    def __init__(self, schema_name: str, connection=None):
        """Initialize with the schema name to extract metadata from.
        
        Args:
            schema_name: Name of the schema to extract metadata from
            connection: Optional database connection to reuse. If not provided,
                      a new connection will be created for each query.
        """
        self.schema_name = schema_name.upper()
        self.connection = connection
    
    def get_tables(self) -> List[str]:
        """Get all tables in the schema."""
        query = """
        SELECT table_name 
        FROM all_tables 
        WHERE owner = :owner
        ORDER BY table_name
        """
        result = execute_query(query, params={"owner": self.schema_name}, connection=self.connection)
        return [row['TABLE_NAME'] for row in result]
    
    def get_table_metadata(self, table_name: str) -> TableMetadata:
        """Get metadata for a specific table."""
        # Get table comments
        comment_query = """
        SELECT comments 
        FROM all_tab_comments 
        WHERE owner = :owner 
        AND table_name = :table_name
        """
        comment_result = execute_query(
            comment_query,
            params={"owner": self.schema_name, "table_name": table_name},
            connection=self.connection
        )
        
        table_comment = comment_result[0]['COMMENTS'] if comment_result else None
        
        # Get columns
        columns = self.get_columns(table_name)
        
        # Get primary keys
        primary_keys = self.get_primary_keys(table_name)
        
        # Get foreign keys
        foreign_keys = self.get_foreign_keys(table_name)
        
        return TableMetadata(
            name=table_name,
            comment=table_comment,
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys
        )
    
    def get_columns(self, table_name: str) -> List[ColumnMetadata]:
        """Get column information for a table."""
        # First get the basic column information
        query = """
        SELECT 
            c.column_name, 
            c.data_type,
            c.data_length,
            c.data_precision,
            c.data_scale,
            c.nullable,
            c.data_default,
            c.char_length,
            cc.comments
        FROM all_tab_columns c
        LEFT JOIN all_col_comments cc 
            ON c.owner = cc.owner 
            AND c.table_name = cc.table_name 
            AND c.column_name = cc.column_name
        WHERE c.owner = :owner 
        AND c.table_name = :table_name
        ORDER BY c.column_id
        """
        result = execute_query(
            query, 
            params={"owner": self.schema_name, "table_name": table_name},
            connection=self.connection
        )
        
        columns = []
        for row in result:
            columns.append(ColumnMetadata(
                name=row['COLUMN_NAME'],
                data_type=row['DATA_TYPE'],
                length=row['CHAR_LENGTH'] or row['DATA_LENGTH'],
                precision=row['DATA_PRECISION'],
                scale=row['DATA_SCALE'],
                nullable=row['NULLABLE'] == 'Y',
                default_value=row['DATA_DEFAULT'],
                comment=row['COMMENTS']
            ))
        return columns
    
    def get_primary_keys(self, table_name: str) -> List[PrimaryKey]:
        """Get primary key information for a table."""
        query = """
        SELECT 
            cols.column_name,
            cons.constraint_name,
            cols.position
        FROM all_cons_columns cols
        JOIN all_constraints cons 
            ON cols.owner = cons.owner 
            AND cols.constraint_name = cons.constraint_name
        WHERE cons.owner = :owner
        AND cons.table_name = :table_name
        AND cons.constraint_type = 'P'
        ORDER BY cols.position
        """
        result = execute_query(
            query,
            params={"owner": self.schema_name, "table_name": table_name},
            connection=self.connection
        )
        
        return [
            PrimaryKey(
                column_name=row['COLUMN_NAME'],
                constraint_name=row['CONSTRAINT_NAME'],
                position=row['POSITION']
            )
            for row in result
        ]
    
    def get_foreign_keys(self, table_name: str) -> List[ForeignKey]:
        """Get foreign key information for a table."""
        query = """
        SELECT 
            a.constraint_name,
            a.column_name,
            a.position,
            c_pk.owner as referenced_owner,
            c_pk.table_name as referenced_table,
            b.column_name as referenced_column
        FROM all_cons_columns a
        JOIN all_constraints c 
            ON a.owner = c.owner 
            AND a.constraint_name = c.constraint_name
        JOIN all_constraints c_pk 
            ON c.r_owner = c_pk.owner 
            AND c.r_constraint_name = c_pk.constraint_name
        JOIN all_cons_columns b 
            ON c_pk.owner = b.owner 
            AND c_pk.constraint_name = b.constraint_name 
            AND b.position = a.position
        WHERE c.constraint_type = 'R'
        AND a.owner = :owner
        AND a.table_name = :table_name
        ORDER BY a.constraint_name, a.position
        """
        
        result = execute_query(
            query,
            params={"owner": self.schema_name, "table_name": table_name},
            connection=self.connection
        )
        
        return [
            ForeignKey(
                constraint_name=row['CONSTRAINT_NAME'],
                column_name=row['COLUMN_NAME'],
                referenced_owner=row['REFERENCED_OWNER'],
                referenced_table=row['REFERENCED_TABLE'],
                referenced_column=row['REFERENCED_COLUMN']
            )
            for row in result
        ]
    
    def get_schema_metadata(self) -> SchemaMetadata:
        """Get metadata for all tables in the schema using a single connection."""
        tables = {}
        
        # Get all table names first
        table_names = self.get_tables()
        
        # If we don't have a connection yet, create one and use it for all operations
        if self.connection is None:
            with get_db_connection() as conn:
                self.connection = conn
                for table_name in table_names:
                    try:
                        table_metadata = self.get_table_metadata(table_name)
                        tables[table_name] = table_metadata
                        logger.debug(f"Extracted metadata for table: {table_name}")
                    except Exception as e:
                        logger.error(f"Error extracting metadata for table {table_name}: {e}")
                        continue
                # Clear the connection after we're done
                self.connection = None
        else:
            # If we were given a connection, use it but don't close it
            for table_name in table_names:
                try:
                    table_metadata = self.get_table_metadata(table_name)
                    tables[table_name] = table_metadata
                    logger.debug(f"Extracted metadata for table: {table_name}")
                except Exception as e:
                    logger.error(f"Error extracting metadata for table {table_name}: {e}")
                    continue
                
        return SchemaMetadata(name=self.schema_name, tables=tables)
