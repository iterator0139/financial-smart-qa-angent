# Financial Knowledge Manager Guide

## Overview

The `FinancialKnowledgeManager` is a knowledge context manager that uses Milvus vector database to store and retrieve SQL context information for financial data. It provides semantic search capabilities for database schemas, table structures, and business descriptions.

## Features

- **Vector-based Semantic Search**: Uses sentence transformers to encode queries and database context
- **Milvus Integration**: Leverages Milvus for efficient vector similarity search
- **SQL Context Management**: Manages database schemas, table structures, and business descriptions
- **Configurable**: Supports configuration through YAML files
- **Error Handling**: Robust error handling with graceful fallbacks

## Installation

### Prerequisites

1. **Python 3.9+**
2. **Milvus Server** (for vector database functionality)
3. **Required Python packages**

### Setup

1. **Install dependencies**:
   ```bash
   conda env create -f environment.yml
   conda activate smart-qa
   ```

2. **Install Milvus** (using Docker):
   ```bash
   # Download Milvus standalone
   wget https://github.com/milvus-io/milvus/releases/download/v2.3.3/milvus-standalone-docker-compose.yml -O docker-compose.yml
   
   # Start Milvus
   docker-compose up -d
   ```

3. **Verify Milvus is running**:
   ```bash
   docker ps | grep milvus
   ```

## Configuration

### Milvus Configuration

Add Milvus configuration to `src/conf/config.yaml`:

```yaml
milvus:
  host: 'localhost'  # Milvus server address
  port: '19530'      # Milvus port
  collection_name: 'financial_sql_context'  # Collection name
  index_params:
    metric_type: 'COSINE'  # Distance metric
    index_type: 'IVF_FLAT'  # Index type
    nlist: 128  # Number of clusters
```

### Embedding Configuration

```yaml
embedding:
  model_name: 'all-MiniLM-L6-v2'  # Sentence transformers model
  cache_dir: '.cache/sentence_transformers'  # Model cache directory
  batch_size: 32  # Batch size for processing
  max_length: 512  # Maximum text length
```

## Usage

### Basic Usage

```python
from src.knowledge.knowledge import create_knowledge_manager
from src.config.config_manager import ConfigManager

# Create config manager
config_manager = ConfigManager()

# Create knowledge manager
knowledge_manager = create_knowledge_manager("financial", config_manager)

# Initialize (loads data and connects to Milvus)
knowledge_manager.init()

# Retrieve relevant context
results = knowledge_manager.retrieve("基金基本信息", top_k=5)

# Close connection
knowledge_manager.close()
```

### Advanced Usage

```python
# Get database summary
summary = knowledge_manager.get_database_summary()
print(summary)

# List available tables
tables = knowledge_manager.list_tables()
print(f"Available tables: {tables}")

# Get specific table schema
schema = knowledge_manager.get_table_schema("基金基本信息")
if schema:
    print(f"Table: {schema['table_name']}")
    print(f"Description: {schema['business_description']}")
    print("Columns:")
    for col in schema['columns']:
        print(f"  - {col['name']} ({col['type']})")

# Semantic search with different queries
queries = [
    "股票持仓信息",
    "债券类型",
    "基金代码",
    "管理费率",
    "成立日期"
]

for query in queries:
    results = knowledge_manager.retrieve(query, top_k=3)
    print(f"\nQuery: {query}")
    for result in results:
        print(f"  - {result['content'][:100]}... (Score: {result['score']:.4f})")
```

## Data Structure

### Required Data Files

The knowledge manager expects the following files in `data/sql_context/`:

1. **`博金杯比赛数据_embedding.pkl`**: Pre-computed embeddings
2. **`博金杯比赛数据_context.json`**: Database context information

### Context Data Format

The context JSON file should contain:

```json
{
  "db_path": "path/to/database.db",
  "db_name": "数据库名称",
  "tables": [
    {
      "table_name": "表名",
      "columns": [
        {
          "name": "字段名",
          "type": "字段类型",
          "nullable": "YES/NO",
          "default": "默认值",
          "primary_key": false
        }
      ],
      "indexes": [],
      "constraints": [],
      "sample_data": {
        "columns": ["字段1", "字段2"],
        "rows": [["值1", "值2"]]
      },
      "business_description": "业务描述"
    }
  ],
  "relationships": [],
  "business_summary": "数据库业务总结"
}
```

## API Reference

### FinancialKnowledgeManager

#### Methods

- **`init()`**: Initialize the knowledge manager
- **`retrieve(query: str, top_k: int = 5) -> List[Dict]`**: Retrieve relevant context
- **`get_table_schema(table_name: str) -> Optional[Dict]`**: Get specific table schema
- **`list_tables() -> List[str]`**: List all available tables
- **`get_database_summary() -> str`**: Get database summary
- **`close()`**: Close Milvus connection

#### Return Format for `retrieve()`

```python
[
    {
        'content': 'Context content',
        'table_name': 'Table name',
        'column_name': 'Column name',
        'data_type': 'Data type',
        'description': 'Description',
        'score': 0.95  # Similarity score
    }
]
```

## Examples

### Example 1: Basic Context Retrieval

```python
# Initialize manager
knowledge_manager = create_knowledge_manager("financial")
knowledge_manager.init()

# Search for fund information
results = knowledge_manager.retrieve("基金代码", top_k=3)

for result in results:
    print(f"Content: {result['content']}")
    print(f"Table: {result['table_name']}")
    print(f"Score: {result['score']:.4f}")
    print("---")

knowledge_manager.close()
```

### Example 2: Table Schema Analysis

```python
knowledge_manager = create_knowledge_manager("financial")
knowledge_manager.init()

# Get all tables
tables = knowledge_manager.list_tables()
print(f"Database contains {len(tables)} tables")

# Analyze each table
for table_name in tables:
    schema = knowledge_manager.get_table_schema(table_name)
    if schema:
        print(f"\nTable: {table_name}")
        print(f"Description: {schema['business_description']}")
        print(f"Columns: {len(schema['columns'])}")
        
        # Show first few columns
        for col in schema['columns'][:3]:
            print(f"  - {col['name']} ({col['type']})")

knowledge_manager.close()
```

### Example 3: Semantic Search for Business Logic

```python
knowledge_manager = create_knowledge_manager("financial")
knowledge_manager.init()

# Search for investment-related information
investment_queries = [
    "股票投资",
    "债券持仓",
    "基金规模",
    "收益率",
    "风险控制"
]

for query in investment_queries:
    print(f"\nSearching for: {query}")
    results = knowledge_manager.retrieve(query, top_k=2)
    
    if results:
        for result in results:
            print(f"  ✓ {result['content'][:80]}...")
            print(f"    Table: {result['table_name']}, Score: {result['score']:.3f}")
    else:
        print("  No relevant results found")

knowledge_manager.close()
```

## Testing

### Run Tests

```bash
# Run unit tests
python src/test/test_knowledge_manager.py

# Run example
python examples/knowledge_manager_usage.py
```

### Test Without Milvus

The test script includes functionality to test the knowledge manager without requiring a running Milvus server:

```python
# This will test basic functionality without Milvus
python src/test/test_knowledge_manager.py
```

## Troubleshooting

### Common Issues

1. **Milvus Connection Error**:
   ```
   Error: Connection refused
   Solution: Ensure Milvus server is running on localhost:19530
   ```

2. **Missing Data Files**:
   ```
   FileNotFoundError: Embedding file not found
   Solution: Ensure data files exist in data/sql_context/
   ```

3. **Import Errors**:
   ```
   ImportError: pymilvus not available
   Solution: Install with: pip install pymilvus
   ```

4. **Memory Issues**:
   ```
   MemoryError: Insufficient memory
   Solution: Reduce batch_size in embedding configuration
   ```

### Performance Optimization

1. **Index Optimization**: Adjust `nlist` parameter in Milvus configuration
2. **Batch Processing**: Use appropriate `batch_size` for embedding generation
3. **Caching**: Enable model caching in embedding configuration
4. **Connection Pooling**: Reuse knowledge manager instances when possible

## Integration with Other Components

### Integration with Query Understanding

```python
from src.query_understanding.qu_subgraph import QueryUnderstandingSubgraph
from src.knowledge.knowledge import create_knowledge_manager

# Initialize components
knowledge_manager = create_knowledge_manager("financial")
knowledge_manager.init()

qu_subgraph = QueryUnderstandingSubgraph()

# Use knowledge context in query understanding
def enhanced_query_understanding(query: str):
    # Get relevant context
    context_results = knowledge_manager.retrieve(query, top_k=3)
    
    # Extract context information
    context_info = "\n".join([r['content'] for r in context_results])
    
    # Use in query understanding
    result = qu_subgraph.process_query(query, context_info)
    
    return result
```

### Integration with SQL Agent

```python
from src.sql_agent import SQLAgent
from src.knowledge.knowledge import create_knowledge_manager

# Initialize components
knowledge_manager = create_knowledge_manager("financial")
knowledge_manager.init()

sql_agent = SQLAgent()

# Enhanced SQL generation with context
def generate_sql_with_context(query: str):
    # Get relevant database context
    context_results = knowledge_manager.retrieve(query, top_k=5)
    
    # Build context prompt
    context_prompt = "Database Context:\n"
    for result in context_results:
        context_prompt += f"- {result['content']}\n"
    
    # Generate SQL with context
    sql_result = sql_agent.generate_sql(query, context_prompt)
    
    return sql_result
```

## Best Practices

1. **Initialize Once**: Initialize the knowledge manager once and reuse it
2. **Close Connections**: Always call `close()` when done
3. **Error Handling**: Wrap operations in try-catch blocks
4. **Configuration**: Use configuration files for different environments
5. **Testing**: Test without Milvus for development
6. **Monitoring**: Monitor search performance and adjust parameters

## Future Enhancements

1. **Multi-database Support**: Support for multiple databases
2. **Dynamic Updates**: Real-time context updates
3. **Advanced Indexing**: Support for different index types
4. **Caching Layer**: Redis-based caching for frequently accessed data
5. **Analytics**: Search analytics and performance metrics
6. **API Endpoints**: REST API for knowledge retrieval 