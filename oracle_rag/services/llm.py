"""LLM service for natural language to SQL conversion."""
from typing import Dict, List, Any, Optional
import logging

from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

from ..config.settings import LLM_SETTINGS
from ..models.schema import SQLGenerationResult

logger = logging.getLogger(__name__)

class LLMService:
    """Service for interacting with language models."""
    
    def __init__(self, **kwargs):
        """Initialize the LLM service.
        
        Args:
            **kwargs: Override default LLM settings
        """
        self.llm_settings = {**LLM_SETTINGS, **kwargs}
        self._llm = None
    
    @property
    def llm(self):
        """Lazy load the language model."""
        if self._llm is None:
            logger.info(f"Initializing LLM with settings: {self.llm_settings}")
            self._llm = OpenAI(**self.llm_settings)
        return self._llm
    
    def generate_sql(
        self, 
        question: str, 
        schema_context: str, 
        tables: List[str],
        **kwargs
    ) -> SQLGenerationResult:
        """Generate SQL from a natural language question.
        
        Args:
            question: Natural language question
            schema_context: Context about the database schema
            tables: List of relevant tables
            **kwargs: Additional arguments for the LLM chain
            
        Returns:
            SQLGenerationResult containing the generated SQL and metadata
        """
        prompt_template = """
        You are an expert Oracle SQL developer. Given the following database schema information:
        
        {schema_context}
        
        Generate an Oracle SQL query for the following question:
        Question: {question}
        
        Consider these tables that might be relevant: {tables}
        
        Important guidelines:
        1. Use proper table aliases for clarity
        2. Include all necessary joins based on foreign key relationships
        3. Use appropriate WHERE clauses to filter the data
        4. Format the SQL for readability
        
        Return ONLY the SQL query, nothing else.
        """
        
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=["schema_context", "question", "tables"]
        )
        
        try:
            # Create and run the chain
            chain = LLMChain(
                llm=self.llm,
                prompt=prompt,
                **kwargs
            )
            
            # Format the tables list for the prompt
            tables_str = ", ".join(sorted(tables)) if tables else "No tables identified"
            
            # Generate the SQL
            response = chain.run(
                schema_context=schema_context,
                question=question,
                tables=tables_str
            )
            
            # Clean up the response
            sql = self._clean_sql_response(response)
            
            return SQLGenerationResult(
                sql=sql,
                tables=tables,
                context=[{"content": schema_context}]
            )
            
        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            raise
    
    @staticmethod
    def _clean_sql_response(response: str) -> str:
        """Clean up the SQL response from the LLM."""
        sql = response.strip()
        
        # Remove markdown code blocks if present
        if sql.startswith("```sql"):
            sql = sql[6:]
        elif sql.startswith("```"):
            sql = sql[3:]
            
        if sql.endswith("```"):
            sql = sql[:-3]
            
        return sql.strip()
    
    def explain_sql(self, sql: str, question: str) -> str:
        """Generate a natural language explanation of a SQL query.
        
        Args:
            sql: SQL query to explain
            question: Original question that led to this query
            
        Returns:
            Natural language explanation of the query
        """
        prompt_template = """
        Explain what the following SQL query does in simple terms:
        
        Question: {question}
        
        SQL Query:
        ```sql
        {sql}
        ```
        
        Provide a clear, concise explanation that would be understandable to a non-technical user.
        Focus on what data is being retrieved and any important filters or conditions.
        """
        
        try:
            # Create a new chain for explanation
            prompt = PromptTemplate(
                template=prompt_template,
                input_variables=["sql", "question"]
            )
            
            chain = LLMChain(
                llm=self.llm,
                prompt=prompt
            )
            
            # Generate the explanation
            explanation = chain.run(sql=sql, question=question)
            return explanation.strip()
            
        except Exception as e:
            logger.error(f"Error generating SQL explanation: {e}")
            return "Unable to generate explanation for this query."
