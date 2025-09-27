"""Database schema models for metadata representation."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ColumnMetadata:
    """Metadata for a database column."""
    name: str
    data_type: str
    length: Optional[int] = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    nullable: bool = True
    default_value: Optional[Any] = None
    comment: Optional[str] = None


@dataclass
class PrimaryKey:
    """Primary key information."""
    column_name: str
    position: int


@dataclass
class ForeignKey:
    """Foreign key relationship information."""
    column_name: str
    referenced_owner: str
    referenced_table: str
    referenced_column: str
    constraint_name: str


@dataclass
class TableMetadata:
    """Metadata for a database table."""
    name: str
    comment: str
    columns: List[ColumnMetadata] = field(default_factory=list)
    primary_keys: List[PrimaryKey] = field(default_factory=list)
    foreign_keys: List[ForeignKey] = field(default_factory=list)


@dataclass
class SchemaMetadata:
    """Complete database schema metadata."""
    name: str
    tables: Dict[str, TableMetadata] = field(default_factory=dict)


@dataclass
class QueryResult:
    """Result of a database query."""
    success: bool
    columns: List[str] = field(default_factory=list)
    rows: List[Dict] = field(default_factory=list)
    row_count: int = 0
    error: Optional[str] = None
    sql: Optional[str] = None


@dataclass
class SearchResult:
    """Result of a semantic search."""
    tables: List[str] = field(default_factory=list)
    context: List[Dict] = field(default_factory=list)


@dataclass
class SQLGenerationResult:
    """Result of SQL generation."""
    sql: str
    tables: List[str] = field(default_factory=list)
    context: List[Dict] = field(default_factory=list)
