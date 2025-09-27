"""Database metadata extraction utilities."""
from typing import Dict, List, Any, Optional
import logging

from .connection import execute_query
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
    
    def __init__(self, schema_name: str):
        """Initialize with the schema name to extract metadata from."""
        self.schema_name = schema_name.upper()
    
    def get_tables(self) -> List[str]:
        """Get all tables in the schema."""
        query = """
        SELECT table_name 
        FROM all_tables 
        WHERE owner = :owner
        ORDER BY table_name
        """
        result = execute_query(query, (self.schema_name,))
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
            (self.schema_name, table_name),
            fetch_all=False
        )
        
        table_comment = comment_result['COMMENTS'] if comment_result else ""
        
        # Get columns
        columns = self._get_columns(table_name)
        
        # Get primary keys
        primary_keys = self._get_primary_keys(table_name)
        
        # Get foreign keys
        foreign_keys = self._get_foreign_keys(table_name)
        
        return TableMetadata(
            name=table_name,
            comment=table_comment or "",
            columns=columns,
            primary_keys=primary_keys,
            foreign_keys=foreign_keys
        )
    
    def _get_columns(self, table_name: str) -> List[ColumnMetadata]:
        """Get column metadata for a table."""
        # Get column information
        column_query = """
        SELECT 
            column_name, 
            data_type, 
            data_length,
            data_precision,
            data_scale,
            nullable,
            data_default
        FROM all_tab_columns
        WHERE owner = :owner 
        AND table_name = :table_name
        ORDER BY column_id
        """
        columns = execute_query(
            column_query, 
            (self.schema_name, table_name)
        )
        
        # Get column comments
        comment_query = """
        SELECT 
            column_name,
            comments
        FROM all_col_comments
        WHERE owner = :owner
        AND table_name = :table_name
        """
        comments = execute_query(
            comment_query,
            (self.schema_name, table_name)
        )
        
        # Create a mapping of column names to comments
        comment_map = {c['COLUMN_NAME']: c['COMMENTS'] for c in comments}
        
        # Create ColumnMetadata objects
        result = []
        for col in columns:
            result.append(ColumnMetadata(
                name=col['COLUMN_NAME'],
                data_type=col['DATA_TYPE'],
                length=col['DATA_LENGTH'],
                precision=col['DATA_PRECISION'],
                scale=col['DATA_SCALE'],
                nullable=col['NULLABLE'] == 'Y',
                default_value=col['DATA_DEFAULT'],
                comment=comment_map.get(col['COLUMN_NAME'])
            ))
            
        return result
    
    def _get_primary_keys(self, table_name: str) -> List[PrimaryKey]:
        """Get primary key information for a table."""
        query = """
        SELECT cols.column_name, cols.position
        FROM all_constraints cons, all_cons_columns cols
        WHERE cons.constraint_type = 'P'
        AND cons.constraint_name = cols.constraint_name
        AND cons.owner = :owner
        AND cols.owner = :owner
        AND cons.table_name = :table_name
        ORDER BY cols.position
        """
        result = execute_query(
            query,
            (self.schema_name, self.schema_name, table_name)
        )
        
        return [
            PrimaryKey(
                column_name=row['COLUMN_NAME'],
                position=row['POSITION']
            )
            for row in result
        ]
    
    def _get_foreign_keys(self, table_name: str) -> List[ForeignKey]:
        """Get foreign key information for a table."""
        query = """
            SELECT 
                a.column_name as column_name,
                c_pk.owner as referenced_owner,
                c_pk.table_name as referenced_table, 
                b.column_name as referenced_column,
                c.constraint_name as constraint_name
            FROM all_cons_columns a
            JOIN all_constraints c ON a.owner = c.owner AND a.constraint_name = c.constraint_name
            JOIN all_constraints c_pk ON c.r_owner = c_pk.owner AND c.r_constraint_name = c_pk.constraint_name
            JOIN all_cons_columns b ON b.owner = c_pk.owner AND b.constraint_name = c_pk.constraint_name
            WHERE c.constraint_type = 'R' 
            AND a.owner = :owner
            AND a.table_name = :table_name
            AND a.position = b.position
        """
        result = execute_query(
            query,
            (self.schema_name, table_name)
        )
        
        return [
            ForeignKey(
                column_name=row['COLUMN_NAME'],
                referenced_owner=row['REFERENCED_OWNER'],
                referenced_table=row['REFERENCED_TABLE'],
                referenced_column=row['REFERENCED_COLUMN'],
                constraint_name=row['CONSTRAINT_NAME']
            )
            for row in result
        ]
    
    def get_schema_metadata(self) -> SchemaMetadata:
        """Get metadata for the entire schema."""
        tables = self.get_tables()
        table_metadata = {}
        
        for table in tables:
            try:
                table_metadata[table] = self.get_table_metadata(table)
            except Exception as e:
                logger.error(f"Error getting metadata for table {table}: {e}")
                continue
                
        return SchemaMetadata(
            name=self.schema_name,
            tables=table_metadata
        )
