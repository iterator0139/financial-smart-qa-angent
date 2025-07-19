#!/usr/bin/env python3
"""
Simple test script for FinancialKnowledgeManager
Can be run directly from project root
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.knowledge.knowledge import FinancialKnowledgeManager, create_knowledge_manager
from src.config.config_manager import ConfigManager


def main():
    """Main test function"""
    print("=== Financial Knowledge Manager Simple Test ===\n")
    
    try:
        # Create config manager
        config_manager = ConfigManager()
        print("✓ Config manager created")
        
        # Create knowledge manager
        knowledge_manager = create_knowledge_manager("financial", config_manager)
        print("✓ Knowledge manager created")
        
        # Test loading embedding data
        print("\n1. Testing embedding data loading...")
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
        
        print("\n=== All tests passed successfully! ===")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 