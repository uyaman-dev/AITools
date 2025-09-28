# Oracle DB Metadata LLM

A powerful tool that leverages Language Models to interact with Oracle Database metadata through natural language queries. Extract schema information, build vector embeddings, and query your database using plain English.

## Features

- **Schema Extraction**: Automatically extract and analyze Oracle database metadata
- **Vector Embeddings**: Convert database schema into searchable vector representations
- **Natural Language Queries**: Ask questions about your database in plain English
- **SQL Generation**: Automatically generate SQL queries based on natural language
- **Context-Aware Responses**: Get explanations and insights about your database structure

## Prerequisites

- Python 3.8+
- Oracle Database (18c or later)
- [Oracle Instant Client](https://www.oracle.com/database/technologies/instant-client.html) (if not using thin mode)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/oracle-db-metadata-llm.git
   cd oracle-db-metadata-llm
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. Copy the example environment file and update with your credentials:
   ```bash
   cp .env.example .env
   ```

2. Edit the `.env` file with your configuration:
   ```
   # Database Configuration
   DB_USER=your_username
   DB_PASSWORD=your_password
   DB_HOST=your_database_host
   DB_PORT=1521
   DB_SERVICE=XE

   # LLM Configuration (at least one API key is required)
   # For OpenAI (GPT models)
   OPENAI_API_KEY=your_openai_api_key_here
   
   # For Google Gemini
   GEMINI_API_KEY=your_gemini_api_key_here

   # Optional settings
   # VECTOR_STORE_DIR=./vector_store
   # EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
   # LOG_LEVEL=INFO
   ```

### Obtaining API Keys

- **OpenAI API Key**: Get it from [OpenAI API Keys](https://platform.openai.com/account/api-keys)
- **Gemini API Key**: Get it from [Google AI Studio](https://makersuite.google.com/app/apikey)

## Usage

### Extract Database Metadata
```bash
python -m oracle_rag.main extract --schema YOUR_SCHEMA
```

### Build Vector Store
```bash
python -m oracle_rag.main build --schema YOUR_SCHEMA
```

### Query Your Database
```bash
python -m oracle_rag.main query "Show me all tables with their column counts" --schema YOUR_SCHEMA
```

## Project Structure

```
oracle_rag/
├── config/           # Configuration settings
├── database/         # Database connection and metadata extraction
├── models/           # Data models and schemas
├── services/         # Core application services
└── main.py          # Main application entry point
```

## Environment Variables

### Required Variables

| Variable         | Description                          | Default     |
|------------------|--------------------------------------|-------------|
| `DB_USER`        | Database username                    | -           |
| `DB_PASSWORD`    | Database password                    | -           |
| `DB_HOST`        | Database host                        | localhost   |
| `DB_PORT`        | Database port                        | 1521        |
| `DB_SERVICE`     | Database service name                | XE          |

### LLM API Keys (At least one required)

| Variable           | Description                          | Default     |
|--------------------|--------------------------------------|-------------|
| `OPENAI_API_KEY`   | OpenAI API key for GPT models        | -           |
| `GEMINI_API_KEY`   | Google Gemini API key                | -           |

### Optional Variables

| Variable           | Description                          | Default                          |
|--------------------|--------------------------------------|----------------------------------|
| `VECTOR_STORE_DIR` | Directory for vector store data      | ./vector_store                   |
| `EMBEDDING_MODEL`  | Model for text embeddings           | sentence-transformers/all-MiniLM-L6-v2 |
| `LOG_LEVEL`        | Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) | INFO |
| `LLM_PROVIDER`     | Default LLM provider (openai or gemini) | gemini (can be overridden in code) |

## Example Queries

### Schema Exploration
```bash
# List all tables in the schema
python -m oracle_rag.main query "List all tables in the schema" --schema HR

# Show table structure
python -m oracle_rag.main query "Describe the EMPLOYEES table" --schema HR

# Find tables with specific columns
python -m oracle_rag.main query "Which tables contain salary information?" --schema HR

# Get table relationships
python -m oracle_rag.main query "How are EMPLOYEES and DEPARTMENTS related?" --schema HR
```

## Troubleshooting

### Common Issues

#### Database Connection Issues
- **Error: ORA-12541: TNS:no listener**
  - Ensure the database is running and accessible
  - Verify the host and port in your `.env` file
  - Check if your Oracle client is properly configured

#### LLM API Issues
- **Authentication errors**
  - Verify your API key is correctly set in the `.env` file
  - Check if you have sufficient credits/quota with the LLM provider

#### Memory Issues
- If you encounter memory errors with large schemas:
  - Try increasing the chunk size in the configuration
  - Filter the schema to include only necessary tables

## Performance Tips

- For large databases, consider extracting metadata during off-peak hours
- The vector store is persistent between sessions - you only need to rebuild it when the schema changes
- Use more specific queries to get faster and more accurate results

## Contributing

1. Fork the repository
2. Create a new branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Acknowledgments

- Built with [LangChain](https://python.langchain.com/)
- Uses [sentence-transformers](https://www.sbert.net/) for embeddings
- Inspired by the need for better database interaction tools
