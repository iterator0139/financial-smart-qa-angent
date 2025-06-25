#!/usr/bin/env python3
"""
SQL上下文向量化模块使用示例
展示如何在智能问答agent中集成和使用SQL上下文信息
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.config.config_manager import ConfigManager
from src.embedding.sql_context import SQLContextRetriever, create_sql_context_task
from src.utils.logger import get_logger
import numpy as np
from typing import Optional, Dict, Any


class SQLContextAgent:
    """
    集成SQL上下文的智能问答Agent示例
    """
    
    def __init__(self, context_dir: str = "data/sql_context"):
        self.logger = get_logger(__name__)
        self.context_retriever = SQLContextRetriever(context_dir)
        self.available_contexts = self.context_retriever.list_available_contexts()
        
        if not self.available_contexts:
            self.logger.warning("没有找到可用的SQL上下文，请先运行向量化任务")
        else:
            self.logger.info(f"加载了 {len(self.available_contexts)} 个SQL上下文: {self.available_contexts}")
    
    def get_database_context(self, db_name: str) -> Optional[str]:
        """
        获取指定数据库的上下文信息
        
        Args:
            db_name: 数据库名称
            
        Returns:
            数据库上下文文本，如果不存在则返回None
        """
        if db_name not in self.available_contexts:
            self.logger.warning(f"数据库 '{db_name}' 的上下文不存在")
            return None
        
        context_text = self.context_retriever.get_context_text(db_name)
        return context_text
    
    def get_database_embedding(self, db_name: str) -> Optional[np.ndarray]:
        """
        获取指定数据库的向量表示
        
        Args:
            db_name: 数据库名称
            
        Returns:
            数据库向量，如果不存在则返回None
        """
        if db_name not in self.available_contexts:
            return None
        
        embedding = self.context_retriever.get_embedding(db_name)
        return embedding
    
    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """
        分析查询的复杂度（示例方法）
        
        Args:
            query: 用户查询
            
        Returns:
            查询复杂度分析结果
        """
        # 这里可以添加更复杂的查询分析逻辑
        keywords = ['join', 'group by', 'order by', 'having', 'union', 'subquery']
        complexity_score = sum(1 for keyword in keywords if keyword in query.lower())
        
        return {
            'complexity_score': complexity_score,
            'is_complex': complexity_score > 2,
            'detected_keywords': [kw for kw in keywords if kw in query.lower()]
        }
    
    def generate_sql_with_context(self, query: str, db_name: str) -> Dict[str, Any]:
        """
        结合数据库上下文生成SQL查询（示例方法）
        
        Args:
            query: 用户查询
            db_name: 数据库名称
            
        Returns:
            包含SQL查询和相关信息的字典
        """
        # 获取数据库上下文
        db_context = self.get_database_context(db_name)
        if not db_context:
            return {
                'success': False,
                'error': f'数据库 {db_name} 的上下文不存在'
            }
        
        # 分析查询复杂度
        complexity = self.analyze_query_complexity(query)
        
        # 构建prompt（这里是示例，实际应用中会调用LLM）
        prompt = f"""
        数据库上下文信息:
        {db_context}
        
        用户查询: {query}
        查询复杂度: {complexity['complexity_score']}
        
        请基于上述数据库结构信息生成对应的SQL查询。
        注意：
        1. 确保使用正确的表名和字段名
        2. 注意表间关系和主外键约束
        3. 优化查询性能
        """
        
        # 这里在实际应用中会调用LLM生成SQL
        # 现在只是返回示例结果
        return {
            'success': True,
            'prompt': prompt,
            'query_complexity': complexity,
            'database_context_length': len(db_context),
            'suggested_sql': "-- 这里应该是生成的SQL查询",
            'explanation': "基于数据库上下文，建议的SQL查询解释"
        }
    
    def list_available_databases(self) -> list:
        """
        列出所有可用的数据库上下文
        
        Returns:
            可用数据库名称列表
        """
        return self.available_contexts
    
    def get_database_summary(self, db_name: str) -> Optional[Dict[str, Any]]:
        """
        获取数据库的摘要信息
        
        Args:
            db_name: 数据库名称
            
        Returns:
            数据库摘要信息
        """
        context_data = self.context_retriever.get_context(db_name)
        if not context_data:
            return None
        
        return {
            'db_name': context_data.get('db_name'),
            'tables_count': len(context_data.get('tables', [])),
            'business_summary': context_data.get('business_summary'),
            'created_at': context_data.get('created_at'),
            'table_names': [table['table_name'] for table in context_data.get('tables', [])]
        }


def demo_basic_usage():
    """演示基本用法"""
    print("=== SQL上下文向量化模块基本用法演示 ===\n")
    
    # 创建Agent实例
    agent = SQLContextAgent()
    
    # 列出可用数据库
    databases = agent.list_available_databases()
    print(f"可用数据库: {databases}\n")
    
    if not databases:
        print("没有可用的数据库上下文，请先运行向量化任务")
        return
    
    # 选择第一个数据库进行演示
    db_name = databases[0]
    print(f"使用数据库: {db_name}\n")
    
    # 获取数据库摘要
    summary = agent.get_database_summary(db_name)
    if summary:
        print("数据库摘要:")
        print(f"  - 数据库名称: {summary['db_name']}")
        print(f"  - 表数量: {summary['tables_count']}")
        print(f"  - 创建时间: {summary['created_at']}")
        print(f"  - 表名列表: {', '.join(summary['table_names'][:5])}...")
        print(f"  - 业务摘要: {summary['business_summary'][:100]}...\n")
    
    # 演示SQL生成
    test_queries = [
        "查询基金的基本信息",
        "找出持仓最多的股票",
        "分析基金的收益率趋势",
        "查询某个时间段内的股票行情"
    ]
    
    print("演示SQL生成:")
    for query in test_queries:
        print(f"\n查询: {query}")
        result = agent.generate_sql_with_context(query, db_name)
        if result['success']:
            print(f"  - 复杂度评分: {result['query_complexity']['complexity_score']}")
            print(f"  - 上下文长度: {result['database_context_length']} 字符")
            print(f"  - 建议SQL: {result['suggested_sql']}")
        else:
            print(f"  - 错误: {result['error']}")


def demo_advanced_usage():
    """演示高级用法"""
    print("\n=== 高级用法演示 ===\n")
    
    agent = SQLContextAgent()
    databases = agent.list_available_databases()
    
    if not databases:
        return
    
    db_name = databases[0]
    
    # 获取向量表示
    embedding = agent.get_database_embedding(db_name)
    if embedding is not None:
        print(f"数据库向量维度: {embedding.shape}")
        print(f"向量范数: {np.linalg.norm(embedding):.4f}")
        print(f"向量前5个值: {embedding[:5]}")
    
    # 获取完整上下文
    context = agent.get_database_context(db_name)
    if context:
        print(f"\n完整上下文长度: {len(context)} 字符")
        print("上下文预览:")
        print(context[:200] + "...")


def main():
    """主函数"""
    print("SQL上下文向量化模块使用示例")
    print("=" * 50)
    
    # 检查是否已有向量化结果
    retriever = SQLContextRetriever()
    contexts = retriever.list_available_contexts()
    
    if not contexts:
        print("没有找到向量化结果，正在创建...")
        
        # 初始化配置
        config_manager = ConfigManager()
        project_root = Path(__file__).resolve().parent.parent
        config_manager.init(project_root / "src" / "conf")
        
        # 执行向量化任务
        db_path = "bs_challenge_financial_14b_dataset/dataset/博金杯比赛数据.db"
        if Path(db_path).exists():
            result = create_sql_context_task(db_path, config_manager=config_manager)
            if result['success']:
                print("✅ 向量化任务完成")
            else:
                print(f"❌ 向量化任务失败: {result.get('error')}")
                return
        else:
            print(f"❌ 数据库文件不存在: {db_path}")
            return
    
    # 演示基本用法
    demo_basic_usage()
    
    # 演示高级用法
    demo_advanced_usage()
    
    print("\n" + "=" * 50)
    print("演示完成！")
    print("要了解更多用法，请查看 docs/sql_context_vectorization.md")


if __name__ == "__main__":
    main() 