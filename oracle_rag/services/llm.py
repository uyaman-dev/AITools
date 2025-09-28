"""LLM service for natural language to SQL conversion with multiple provider support."""
import os
from enum import Enum
from typing import Dict, List, Any, Optional, Union
import logging

from langchain_community.llms import OpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from ..config.settings import LLM_SETTINGS
from ..models.schema import SQLGenerationResult

class LLMProvider(str, Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    GEMINI = "gemini"

DEFAULT_PROVIDER = LLMProvider.GEMINI

class LLMService:
    """Service for interacting with language models with multiple provider support."""

    def __init__(
            self,
            provider: Union[str, LLMProvider] = DEFAULT_PROVIDER,
            api_key: Optional[str] = None,
            **kwargs
    ):
        """Initialize the LLM service.

        Args:
            provider: LLM provider to use ('openai' or 'gemini')
            api_key: API key for the provider (can also be set via environment variables)
            **kwargs: Additional provider-specific parameters
        """
        self.provider = LLMProvider(provider.lower())
        self.api_key = api_key or os.getenv(f"{self.provider.upper()}_API_KEY")

        if not self.api_key:
            raise ValueError(
                f"{self.provider.upper()}_API_KEY environment variable or api_key parameter is required"
            )

        self.llm_settings = {**LLM_SETTINGS, **kwargs}
        self._llm = None

    @property
    def llm(self):
        """Lazy load the language model."""
        if self._llm is None:
            provider_settings = self.llm_settings.get(self.provider.value, {})
            logger.info(f"Initializing {self.provider} LLM with settings: {provider_settings}")

            if self.provider == LLMProvider.OPENAI:
                self._llm = OpenAI(
                    openai_api_key=self.api_key,
                    **{k: v for k, v in provider_settings.items() 
                       if k not in ["model_name"]}
                )
            elif self.provider == LLMProvider.GEMINI:
                self._llm = ChatGoogleGenerativeAI(
                    api_key=self.api_key,
                    model=provider_settings.get("model_name", "gemini-pro"),
                    temperature=provider_settings.get("temperature", 0.3),
                    **{k: v for k, v in provider_settings.items()
                       if k not in ["model_name", "temperature"]}
                )
            else:
                raise ValueError(f"Unsupported LLM provider: {self.provider}")

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

        try:
            # Create the prompt template
            prompt = ChatPromptTemplate.from_template(prompt_template)
            
            # Format the tables list for the prompt
            tables_str = ", ".join(sorted(tables)) if tables else "No tables identified"
            
            # Create the chain using the new Runnable interface
            chain = (
                {
                    "schema_context": lambda x: x["schema_context"],
                    "question": lambda x: x["question"],
                    "tables": lambda x: x["tables"]
                }
                | prompt
                | self.llm
            )
            
            # Generate the SQL
            response = chain.invoke({
                "schema_context": schema_context,
                "question": question,
                "tables": tables_str
            })

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
        """Clean up the SQL response from the LLM.

        Args:
            response: Raw response from the LLM

        Returns:
            Cleaned SQL query
        """
        # Remove markdown code block markers if present
        if "```sql" in response:
            response = response.split("```sql")[1].split("```")[0].strip()
        elif "```" in response:
            response = response.split("```")[1].split("```")[0].strip()

        # Remove any leading/trailing whitespace and newlines
        return response.strip()

    def get_llm_chain(self, prompt_template: str, **kwargs) -> LLMChain:
        """Create a generic LLM chain with the given prompt template.

        Args:
            prompt_template: Template for the prompt
            **kwargs: Additional arguments for the LLM chain

        Returns:
            Configured LLMChain instance
        """
        prompt = PromptTemplate(
            template=prompt_template,
            input_variables=kwargs.pop("input_variables", None)
        )

        return LLMChain(
            llm=self.llm,
            prompt=prompt,
            **kwargs
        )
        
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
            # Use the generic chain method for explanation
            chain = self.get_llm_chain(
                prompt_template=prompt_template,
                input_variables=["sql", "question"]
            )
            
            # Generate the explanation
            explanation = chain.run(sql=sql, question=question)
            return explanation.strip()
            
        except Exception as e:
            logger.error(f"Error generating SQL explanation: {e}")
            return "Unable to generate explanation for this query."

logger = logging.getLogger(__name__)