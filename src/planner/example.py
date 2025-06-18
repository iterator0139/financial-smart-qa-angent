#!/usr/bin/env python3
"""
带记忆模块的Planner Agent使用示例
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.planner.planner import PlannerAgent, InMemoryStore
from src.utils.logger import get_logger


def main():
    """主示例函数"""
    # 初始化日志
    logger = get_logger("planner_example")
    
    # 创建Planner Agent
    logger.info("初始化Planner Agent...")
    planner = PlannerAgent()
    
    # 示例查询列表
    queries = [
        "请查询在20211125日期，中信行业分类下机械一级行业中，当日收盘价波动最大的股票代码是什么？",
        "分析某股票的市盈率是否合理",
        "查询最近一个月内涨幅最大的前10只股票",
        "计算某公司的财务指标分析"
    ]
    
    # 处理每个查询
    for i, query in enumerate(queries, 1):
        logger.info(f"\n{'='*60}")
        logger.info(f"处理查询 {i}: {query}")
        logger.info(f"{'='*60}")
        
        # 执行规划和执行
        result = planner.plan_and_execute(query)
        
        # 输出结果
        logger.info(f"\n--- 执行结果 ---")
        logger.info(f"查询: {result['query']}")
        logger.info(f"执行状态: {'成功' if not result.get('error') else '失败'}")
        
        if result.get('error'):
            logger.error(f"错误信息: {result['error']}")
        else:
            logger.info(f"执行步骤数: {len(result['executed_actions'])}")
            logger.info(f"最终结果: {result['final_result']}")
        
        # 显示执行的步骤
        logger.info(f"\n--- 执行步骤详情 ---")
        for action in result['executed_actions']:
            logger.info(f"步骤 {action['step_id']}: {action['action']} - {action['status']}")
            if action.get('result'):
                logger.info(f"  结果: {action['result']}")
    
    # 显示记忆摘要
    logger.info(f"\n{'='*60}")
    logger.info("记忆库摘要")
    logger.info(f"{'='*60}")
    
    memory_summary = planner.get_memory_summary()
    logger.info(f"最近记忆数量: {memory_summary['total_recent_memories']}")
    logger.info(f"记忆类型分布: {memory_summary['memory_types']}")
    
    if memory_summary['latest_memory']:
        latest = memory_summary['latest_memory']
        logger.info(f"最新记忆: {latest['memory_type']} - {latest['content'][:100]}...")
    
    # 演示记忆检索功能
    logger.info(f"\n{'='*60}")
    logger.info("记忆检索演示")
    logger.info(f"{'='*60}")
    
    search_query = "股票查询"
    relevant_memories = planner.retrieve_relevant_memories(search_query, top_k=3)
    
    logger.info(f"搜索查询: '{search_query}'")
    logger.info(f"找到 {len(relevant_memories)} 条相关记忆:")
    
    for memory in relevant_memories:
        logger.info(f"- [{memory.memory_type}] {memory.content[:80]}... (相关性: {memory.relevance_score:.2f})")


def demo_advanced_features():
    """演示高级功能"""
    logger = get_logger("advanced_demo")
    
    logger.info("=== 高级功能演示 ===")
    
    # 创建自定义内存存储
    custom_memory_store = InMemoryStore()
    planner = PlannerAgent(memory_store=custom_memory_store)
    
    # 预填充一些策略记忆
    logger.info("预填充策略记忆...")
    
    strategy_memories = [
        ("股票价格查询通常需要SQL生成步骤", "strategy"),
        ("财务分析需要多个数据源的信息", "strategy"),
        ("市盈率分析需要当前价格和盈利数据", "strategy")
    ]
    
    for content, memory_type in strategy_memories:
        planner.store_memory(content, memory_type, {"source": "pre-filled"})
    
    # 使用相似查询测试记忆利用
    test_query = "分析股票市盈率的合理性"
    logger.info(f"\n测试查询: {test_query}")
    
    # 检索相关策略记忆
    relevant_strategies = planner.retrieve_relevant_memories(test_query, memory_type="strategy")
    logger.info(f"找到 {len(relevant_strategies)} 条相关策略记忆")
    
    for strategy in relevant_strategies:
        logger.info(f"- {strategy.content} (相关性: {strategy.relevance_score:.2f})")
    
    # 执行查询
    result = planner.plan_and_execute(test_query)
    
    # 显示如何利用了历史记忆
    logger.info(f"\n基于历史记忆生成的执行计划包含 {len(result['executed_actions'])} 个步骤")


if __name__ == "__main__":
    # 运行基本示例
    main()
    
    print("\n" + "="*80 + "\n")
    
    # 运行高级功能演示
    demo_advanced_features() 