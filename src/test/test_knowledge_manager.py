#!/usr/bin/env python3
"""
Test script for FinancialKnowledgeManager
"""

import sys
import os
import unittest
from unittest.mock import Mock, patch, MagicMock

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from src.knowledge.knowledge import FinancialKnowledgeManager, create_knowledge_manager
from src.config.config_manager import ConfigManager


class TestFinancialKnowledgeManager(unittest.TestCase):
    """Test cases for FinancialKnowledgeManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config_manager = ConfigManager()
        self.knowledge_manager = FinancialKnowledgeManager(self.config_manager)
    
    def test_initialization(self):
        """Test knowledge manager initialization"""
        self.assertIsNotNone(self.knowledge_manager)
        self.assertEqual(self.knowledge_manager.collection_name, 'financial_sql_context')
        self.assertEqual(self.knowledge_manager.dimension, 384)
    
    @patch('src.knowledge.knowledge.MILVUS_AVAILABLE', False)
    def test_milvus_not_available(self):
        """Test behavior when Milvus is not available"""
        with self.assertRaises(ImportError):
            self.knowledge_manager._init_milvus()
    
    @patch('src.knowledge.knowledge.SENTENCE_TRANSFORMERS_AVAILABLE', False)
    def test_embedding_model_not_available(self):
        """Test behavior when sentence-transformers is not available"""
        with self.assertRaises(ImportError):
            self.knowledge_manager._init_embedding_model()
    
    def test_create_knowledge_manager_factory(self):
        """Test factory function for creating knowledge managers"""
        # Test valid type
        manager = create_knowledge_manager("financial", self.config_manager)
        self.assertIsInstance(manager, FinancialKnowledgeManager)
        
        # Test invalid type
        with self.assertRaises(ValueError):
            create_knowledge_manager("invalid_type", self.config_manager)
    
    def test_generate_context_chunks(self):
        """Test context chunk generation"""
        # Mock context data
        mock_context_data = {
            'tables': [
                {
                    'table_name': '测试表',
                    'business_description': '这是一个测试表',
                    'columns': [
                        {'name': '字段1', 'type': 'TEXT'},
                        {'name': '字段2', 'type': 'INTEGER'}
                    ],
                    'sample_data': {
                        'columns': ['字段1', '字段2'],
                        'rows': [['值1', 1], ['值2', 2]]
                    }
                }
            ]
        }
        
        self.knowledge_manager.context_data = mock_context_data
        chunks = self.knowledge_manager._generate_context_chunks()
        
        # Should generate chunks for table description, columns, and sample data
        self.assertGreater(len(chunks), 0)
        
        # Check table description chunk
        table_chunk = chunks[0]
        self.assertIn('测试表', table_chunk['content'])
        self.assertEqual(table_chunk['table_name'], '测试表')
    
    def test_list_tables(self):
        """Test listing available tables"""
        # Mock context data
        mock_context_data = {
            'tables': [
                {'table_name': '表1'},
                {'table_name': '表2'}
            ]
        }
        
        self.knowledge_manager.context_data = mock_context_data
        tables = self.knowledge_manager.list_tables()
        
        self.assertEqual(len(tables), 2)
        self.assertIn('表1', tables)
        self.assertIn('表2', tables)
    
    def test_get_table_schema(self):
        """Test getting specific table schema"""
        # Mock context data
        mock_context_data = {
            'tables': [
                {
                    'table_name': '目标表',
                    'columns': [{'name': '字段1', 'type': 'TEXT'}],
                    'business_description': '目标表描述'
                }
            ]
        }
        
        self.knowledge_manager.context_data = mock_context_data
        
        # Test existing table
        schema = self.knowledge_manager.get_table_schema('目标表')
        self.assertIsNotNone(schema)
        self.assertEqual(schema['table_name'], '目标表')
        
        # Test non-existing table
        schema = self.knowledge_manager.get_table_schema('不存在的表')
        self.assertIsNone(schema)
    
    def test_get_database_summary(self):
        """Test getting database summary"""
        # Mock context data
        mock_context_data = {
            'db_name': '测试数据库',
            'db_path': '/path/to/db',
            'tables': [{'table_name': '表1'}],
            'business_summary': '数据库业务描述'
        }
        
        self.knowledge_manager.context_data = mock_context_data
        summary = self.knowledge_manager.get_database_summary()
        
        self.assertIn('测试数据库', summary)
        self.assertIn('表数量: 1', summary)
        self.assertIn('数据库业务描述', summary)


def test_without_milvus():
    """Test knowledge manager functionality without Milvus server"""
    print("=== Testing Knowledge Manager (without Milvus) ===\n")
    
    try:
        config_manager = ConfigManager()
        knowledge_manager = FinancialKnowledgeManager(config_manager)
        
        # Test loading embedding data
        print("1. Testing embedding data loading...")
        try:
            knowledge_manager._load_embedding_data()
            print("   ✓ Embedding data loaded successfully")
        except FileNotFoundError as e:
            print(f"   ⚠ Warning: {e}")
            print("   This is expected if data files are not present")
        
        # Test context chunk generation with mock data
        print("\n2. Testing context chunk generation...")
        mock_data = {
            'tables': [
                {
                    'table_name': '基金基本信息',
                    'business_description': '存储基金的基本信息',
                    'columns': [
                        {'name': '基金代码', 'type': 'TEXT'},
                        {'name': '基金名称', 'type': 'TEXT'}
                    ],
                    'sample_data': {
                        'columns': ['基金代码', '基金名称'],
                        'rows': [['000001', '测试基金']]
                    }
                }
            ]
        }
        
        knowledge_manager.context_data = mock_data
        chunks = knowledge_manager._generate_context_chunks()
        print(f"   ✓ Generated {len(chunks)} context chunks")
        
        # Test table listing
        print("\n3. Testing table listing...")
        tables = knowledge_manager.list_tables()
        print(f"   ✓ Found {len(tables)} tables: {tables}")
        
        # Test table schema retrieval
        print("\n4. Testing table schema retrieval...")
        schema = knowledge_manager.get_table_schema('基金基本信息')
        if schema:
            print(f"   ✓ Retrieved schema for '基金基本信息'")
            print(f"     Description: {schema.get('business_description', 'N/A')}")
            print(f"     Columns: {len(schema.get('columns', []))}")
        
        # Test database summary
        print("\n5. Testing database summary...")
        summary = knowledge_manager.get_database_summary()
        print(f"   ✓ Database summary generated")
        print(f"     Length: {len(summary)} characters")
        
        print("\n=== Test completed successfully! ===")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run unit tests
    print("Running unit tests...")
    unittest.main(argv=[''], exit=False, verbosity=2)
    
    print("\n" + "="*50 + "\n")
    
    # Run functional test without Milvus
    test_without_milvus() 