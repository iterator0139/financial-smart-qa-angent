#!/usr/bin/env python3
"""
测试自定义 ReAct Agent
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.planner.planner import create_default_custom_react_agent
from src.config.config_manager import ConfigManager
from src.utils.logger import get_logger

def test_custom_react_agent():
    """测试自定义 ReAct Agent"""
    
    # 初始化日志
    logger = get_logger()
    logger.info("开始测试自定义 ReAct Agent")
    
    # 初始化配置
    config = ConfigManager()
    config_dir = Path(__file__).resolve().parent / "src" / "conf"
    config.init(config_dir)
    
    # 创建自定义 ReAct Agent
    agent = create_default_custom_react_agent(
        model_name="qwen-turbo",
        config=config,
        max_steps=5
    )
    
    # 测试查询
    test_queries = [
        "请帮我检查数据库信息",
        "请帮我查询出20210415日，建筑材料一级行业涨幅超过5%（不包含）的股票数量。"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"测试 {i}: {query}")
        print(f"{'='*60}")
        
        try:
            # 执行查询
            result = agent.invoke(query)
            
            # 输出结果
            print(f"✅ 执行成功!")
            print(f"📝 最终答案: {result.get('final_answer', 'N/A')}")
            print(f"🔢 推理步骤: {result.get('steps_taken', 0)}")
            print(f"🛠️  工具调用次数: {len(result.get('tool_results', []))}")
            
            if result.get('error'):
                print(f"❌ 错误信息: {result['error']}")
            
            if result.get('tool_results'):
                print(f"\n🛠️  工具调用详情:")
                for tool_result in result['tool_results']:
                    print(f"  - {tool_result['tool']}: {tool_result['output'][:100]}...")
            
            if result.get('scratchpad'):
                print(f"\n📋 推理过程:")
                print(result['scratchpad'][:500] + "..." if len(result['scratchpad']) > 500 else result['scratchpad'])
                
        except Exception as e:
            print(f"❌ 测试失败: {e}")
            logger.error(f"测试失败: {e}")
    
    print(f"\n{'='*60}")
    print("测试完成!")
    print(f"{'='*60}")

if __name__ == "__main__":
    test_custom_react_agent() 