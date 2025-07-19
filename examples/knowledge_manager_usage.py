#!/usr/bin/env python3
"""
Example usage of FinancialKnowledgeManager for SQL context retrieval
"""

import sys
import os

# Add the project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.knowledge.knowledge import create_knowledge_manager
from src.config.config_manager import ConfigManager


def main():
    """Main function demonstrating knowledge manager usage"""
    
    print("=== Financial Knowledge Manager Example ===\n")
    
    try:
        # Create config manager
        config_manager = ConfigManager()
        
        # Create knowledge manager
        print("1. Creating FinancialKnowledgeManager...")
        knowledge_manager = create_knowledge_manager("financial", config_manager)
        
        # Initialize the manager
        print("2. Initializing knowledge manager...")
        knowledge_manager.init()
        
        # Get database summary
        print("3. Database Summary:")
        summary = knowledge_manager.get_database_summary()
        print(summary)
        print()
        
        # List available tables
        print("4. Available Tables:")
        tables = knowledge_manager.list_tables()
        for i, table in enumerate(tables, 1):
            print(f"   {i}. {table}")
        print()
        
        # Example queries
        example_queries = [
            "基金基本信息",
            "股票持仓",
            "债券类型",
            "基金代码",
            "管理费率",
            "成立日期"
        ]
        
        print("5. Example Knowledge Retrieval:")
        for query in example_queries:
            print(f"\nQuery: '{query}'")
            results = knowledge_manager.retrieve(query, top_k=3)
            
            if results:
                for i, result in enumerate(results, 1):
                    print(f"   Result {i}:")
                    print(f"     Content: {result['content'][:100]}...")
                    print(f"     Table: {result['table_name']}")
                    print(f"     Column: {result['column_name']}")
                    print(f"     Score: {result['score']:.4f}")
            else:
                print("   No results found")
        
        # Get specific table schema
        print("\n6. Table Schema Example:")
        table_name = "基金基本信息"
        schema = knowledge_manager.get_table_schema(table_name)
        if schema:
            print(f"Table: {schema['table_name']}")
            print(f"Description: {schema.get('business_description', 'No description')}")
            print("Columns:")
            for col in schema.get('columns', [])[:5]:  # Show first 5 columns
                print(f"  - {col['name']} ({col['type']})")
        else:
            print(f"Table '{table_name}' not found")
        
        # Close the manager
        print("\n7. Closing knowledge manager...")
        knowledge_manager.close()
        
        print("\n=== Example completed successfully! ===")
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure you have:")
        print("1. Milvus server running on localhost:19530")
        print("2. Required data files in data/sql_context/")
        print("3. All dependencies installed (sentence-transformers, pymilvus)")


if __name__ == "__main__":
    main() 