import pickle
import json
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Any, Tuple
from pathlib import Path
import logging

# Milvus imports
try:
    from pymilvus import connections, Collection, CollectionSchema, FieldSchema, DataType, utility
    MILVUS_AVAILABLE = True
except ImportError:
    MILVUS_AVAILABLE = False
    print("Warning: pymilvus not available. Please install with: pip install pymilvus")

# Sentence transformers for embedding
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available")

from src.config.config_manager import ConfigManager
from src.utils.logger import get_logger


class KnowledgeManager(ABC):
    """Abstract base class for knowledge managers"""
    
    @abstractmethod
    def init(self) -> None:
        """Initialize the knowledge manager"""
        pass

    @abstractmethod
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant knowledge based on query"""
        pass


class FinancialKnowledgeManager(KnowledgeManager):
    """Financial knowledge manager using Milvus for vector search"""
    
    def __init__(self, config_manager: ConfigManager = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(__name__)
        
        # Milvus configuration
        self.milvus_host = self.config_manager.get('milvus.host', 'localhost')
        self.milvus_port = self.config_manager.get('milvus.port', '19530')
        self.collection_name = 'financial_sql_context'
        self.dimension = 384  # Default dimension for all-MiniLM-L6-v2
        
        # Embedding model
        self.embedding_model = None
        self.embedding_data = None
        self.context_data = None
        
        # Milvus collection
        self.collection = None
        
    def init(self) -> None:
        """Initialize the knowledge manager with Milvus and embedding data"""
        try:
            # Load embedding file
            self._load_embedding_data()
            
            # Initialize embedding model
            self._init_embedding_model()
            
            # Initialize Milvus connection and collection
            self._init_milvus()
            
            # Load data into Milvus if collection is empty
            self._load_data_to_milvus()
            
            self.logger.info("FinancialKnowledgeManager initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize FinancialKnowledgeManager: {e}")
            raise
    
    def _load_embedding_data(self):
        """Load embedding data from pickle file"""
        embedding_path = Path('/home/hom/project/financial-smart-qa-angent/data/sql_context/博金杯比赛数据_embedding.pkl')
        context_path = Path('/home/hom/project/financial-smart-qa-angent/data/sql_context/博金杯比赛数据_context.json')
        
        if not embedding_path.exists():
            raise FileNotFoundError(f"Embedding file not found: {embedding_path}")
        
        if not context_path.exists():
            raise FileNotFoundError(f"Context file not found: {context_path}")
        
        # Load embedding data
        with open(embedding_path, 'rb') as f:
            self.embedding_data = pickle.load(f)
        
        # Load context data
        with open(context_path, 'r', encoding='utf-8') as f:
            self.context_data = json.load(f)
        
        self.logger.info(f"Loaded embedding data with shape: {self.embedding_data.shape if hasattr(self.embedding_data, 'shape') else 'unknown'}")
    
    def _init_embedding_model(self):
        """Initialize the embedding model"""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            raise ImportError("sentence-transformers is required for embedding functionality")
        
        model_name = self.config_manager.get('embedding.model_name', 'all-MiniLM-L6-v2')
        cache_dir = self.config_manager.get('embedding.cache_dir', '.cache/sentence_transformers')
        
        self.embedding_model = SentenceTransformer(model_name, cache_folder=cache_dir)
        self.dimension = self.embedding_model.get_sentence_embedding_dimension()
        
        self.logger.info(f"Initialized embedding model: {model_name} with dimension: {self.dimension}")
    
    def _init_milvus(self):
        """Initialize Milvus connection and collection"""
        if not MILVUS_AVAILABLE:
            raise ImportError("pymilvus is required for vector database functionality")
        
        # Connect to Milvus
        connections.connect(
            alias="default",
            host=self.milvus_host,
            port=self.milvus_port
        )
        
        # Check if collection exists
        if utility.has_collection(self.collection_name):
            self.collection = Collection(self.collection_name)
            self.logger.info(f"Connected to existing collection: {self.collection_name}")
        else:
            # Create collection
            self._create_collection()
            self.logger.info(f"Created new collection: {self.collection_name}")
    
    def _create_collection(self):
        """Create Milvus collection with proper schema"""
        # Define schema
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
            FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=self.dimension),
            FieldSchema(name="table_name", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="column_name", dtype=DataType.VARCHAR, max_length=100),
            FieldSchema(name="data_type", dtype=DataType.VARCHAR, max_length=50),
            FieldSchema(name="description", dtype=DataType.VARCHAR, max_length=500)
        ]
        
        schema = CollectionSchema(fields=fields, description="Financial SQL context collection")
        
        # Create collection
        self.collection = Collection(
            name=self.collection_name,
            schema=schema,
            using='default'
        )
        
        # Create index
        index_params = {
            "metric_type": "COSINE",
            "index_type": "IVF_FLAT",
            "params": {"nlist": 128}
        }
        
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params
        )
        
        self.logger.info("Created index on embedding field")
    
    def _load_data_to_milvus(self):
        """Load SQL context data into Milvus"""
        if self.collection.num_entities > 0:
            self.logger.info("Collection already has data, skipping data loading")
            return
        
        # Generate context chunks from SQL data
        context_chunks = self._generate_context_chunks()
        
        # Prepare data for insertion
        data_to_insert = []
        
        for i, chunk in enumerate(context_chunks):
            # Generate embedding for the chunk
            embedding = self.embedding_model.encode(chunk['content'])
            
            data_to_insert.append({
                'content': chunk['content'],
                'embedding': embedding.tolist(),
                'table_name': chunk.get('table_name', ''),
                'column_name': chunk.get('column_name', ''),
                'data_type': chunk.get('data_type', ''),
                'description': chunk.get('description', '')
            })
        
        # Insert data
        self.collection.insert(data_to_insert)
        self.collection.flush()
        
        self.logger.info(f"Loaded {len(data_to_insert)} chunks into Milvus")
    
    def _generate_context_chunks(self) -> List[Dict[str, str]]:
        """Generate context chunks from SQL context data"""
        chunks = []
        
        if not self.context_data or 'tables' not in self.context_data:
            return chunks
        
        for table in self.context_data['tables']:
            table_name = table['table_name']
            
            # Table description chunk
            table_desc = f"表名: {table_name}\n业务描述: {table.get('business_description', '')}"
            chunks.append({
                'content': table_desc,
                'table_name': table_name,
                'description': table.get('business_description', '')
            })
            
            # Column information chunks
            for column in table.get('columns', []):
                col_name = column['name']
                col_type = column['type']
                col_desc = f"表 {table_name} 的字段 {col_name}，类型为 {col_type}"
                
                chunks.append({
                    'content': col_desc,
                    'table_name': table_name,
                    'column_name': col_name,
                    'data_type': col_type,
                    'description': f"字段 {col_name} 的类型为 {col_type}"
                })
            
            # Sample data chunk
            if 'sample_data' in table and table['sample_data'].get('rows'):
                sample_text = f"表 {table_name} 的示例数据:\n"
                sample_text += f"字段: {', '.join(table['sample_data']['columns'])}\n"
                sample_text += f"示例行数: {len(table['sample_data']['rows'])}"
                
                chunks.append({
                    'content': sample_text,
                    'table_name': table_name,
                    'description': f"表 {table_name} 的示例数据"
                })
        
        return chunks
    
    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve relevant SQL context based on query"""
        try:
            if not self.collection:
                raise RuntimeError("Collection not initialized. Call init() first.")
            
            # Generate query embedding
            query_embedding = self.embedding_model.encode(query)
            
            # Search in Milvus
            search_params = {
                "metric_type": "COSINE",
                "params": {"nprobe": 10}
            }
            
            results = self.collection.search(
                data=[query_embedding.tolist()],
                anns_field="embedding",
                param=search_params,
                limit=top_k,
                output_fields=["content", "table_name", "column_name", "data_type", "description"]
            )
            
            # Format results
            formatted_results = []
            for hits in results:
                for hit in hits:
                    formatted_results.append({
                        'content': hit.entity.get('content'),
                        'table_name': hit.entity.get('table_name'),
                        'column_name': hit.entity.get('column_name'),
                        'data_type': hit.entity.get('data_type'),
                        'description': hit.entity.get('description'),
                        'score': hit.score
                    })
            
            self.logger.info(f"Retrieved {len(formatted_results)} results for query: {query}")
            return formatted_results
            
        except Exception as e:
            self.logger.error(f"Error retrieving knowledge for query '{query}': {e}")
            return []
    
    def get_table_schema(self, table_name: str) -> Optional[Dict[str, Any]]:
        """Get specific table schema information"""
        if not self.context_data or 'tables' not in self.context_data:
            return None
        
        for table in self.context_data['tables']:
            if table['table_name'] == table_name:
                return table
        
        return None
    
    def list_tables(self) -> List[str]:
        """List all available tables"""
        if not self.context_data or 'tables' not in self.context_data:
            return []
        
        return [table['table_name'] for table in self.context_data['tables']]
    
    def get_database_summary(self) -> str:
        """Get database summary information"""
        if not self.context_data:
            return "No database context available"
        
        summary = f"数据库名称: {self.context_data.get('db_name', 'Unknown')}\n"
        summary += f"数据库路径: {self.context_data.get('db_path', 'Unknown')}\n"
        summary += f"表数量: {len(self.context_data.get('tables', []))}\n"
        summary += f"业务描述: {self.context_data.get('business_summary', 'No description available')}"
        
        return summary
    
    def close(self):
        """Close Milvus connection"""
        if self.collection:
            self.collection.release()
        
        try:
            connections.disconnect("default")
            self.logger.info("Disconnected from Milvus")
        except Exception as e:
            self.logger.warning(f"Error disconnecting from Milvus: {e}")


# Factory function for creating knowledge managers
def create_knowledge_manager(manager_type: str = "financial", config_manager: ConfigManager = None) -> KnowledgeManager:
    """Create a knowledge manager instance"""
    if manager_type == "financial":
        return FinancialKnowledgeManager(config_manager)
    else:
        raise ValueError(f"Unknown knowledge manager type: {manager_type}")