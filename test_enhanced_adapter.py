#!/usr/bin/env python3
"""
测试增强后的StreamingLLMAdapter工具调用功能
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
from src.models.streaming_adapter import StreamingLLMAdapter
from src.config.config_manager import ConfigManager


def create_test_tool():
    """创建一个测试工具"""
    
    def test_function(input_text: str) -> str:
        print(f"🎯 [REAL_TOOL_EXECUTION] 工具真正被执行了！")
        print(f"📝 [TOOL_INPUT] 输入: {input_text}")
        result = f"工具执行结果: {input_text}"
        print(f"📤 [TOOL_OUTPUT] 输出: {result}")
        return result
    
    return Tool(
        name="TestTool",
        description="A test tool that prints execution logs",
        func=test_function
    )


def test_direct_tool_calling():
    """直接测试工具调用"""
    print("=== 直接测试工具调用 ===")
    
    # 初始化配置
    config = ConfigManager()
    config_dir = Path(__file__).resolve().parent / "src" / "conf"
    config.init(config_dir)
    
    # 创建测试工具
    test_tool = create_test_tool()
    
    # 创建增强的StreamingLLMAdapter
    llm = StreamingLLMAdapter(
        model="qwen-turbo",
        api_key=config.get_config().get("api.qwen.api_key"),
        base_url=config.get_config().get("api.qwen.base_url"),
        default_params={}
    )
    
    # 绑定工具
    llm_with_tools = llm.bind_tools([test_tool])
    
    print("✅ 增强的StreamingLLMAdapter创建成功，工具已绑定")
    
    # 直接调用模型
    from langchain_core.messages import HumanMessage
    
    try:
        response = llm_with_tools.invoke([
            HumanMessage(content="请使用TestTool工具处理一些数据")
        ])
        
        print(f"直接调用结果: {response}")
        
        # 检查是否有工具调用
        if hasattr(response, 'tool_calls') and response.tool_calls:
            print("🎯 检测到工具调用！")
            for tool_call in response.tool_calls:
                print(f"工具名称: {tool_call['name']}")
                print(f"工具参数: {tool_call['args']}")
        else:
            print("⚠️ 没有检测到工具调用")
            print("模型输出内容:")
            print(response.content)
            
    except Exception as e:
        print(f"❌ 直接调用失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_agent():
    """使用Agent测试"""
    print("\n=== 使用Agent测试 ===")
    
    # 初始化配置
    config = ConfigManager()
    config_dir = Path(__file__).resolve().parent / "src" / "conf"
    config.init(config_dir)
    
    # 创建测试工具
    test_tool = create_test_tool()
    
    # 创建增强的StreamingLLMAdapter
    llm = StreamingLLMAdapter(
        model="qwen-turbo",
        api_key=config.get_config().get("api.qwen.api_key"),
        base_url=config.get_config().get("api.qwen.base_url"),
        default_params={}
    )
    
    # 绑定工具
    llm_with_tools = llm.bind_tools([test_tool])
    
    # 创建Agent
    agent = create_react_agent(
        model=llm_with_tools,
        tools=[test_tool]
    )
    
    print("✅ 增强的StreamingLLMAdapter Agent创建成功")
    
    # 测试查询
    query = "请使用TestTool工具处理一些数据"
    print(f"测试查询: {query}")
    
    try:
        result = agent.invoke({
            "messages": [{"role": "user", "content": query}]
        })
        
        print(f"Agent结果: {result}")
        
        # 检查消息
        messages = result.get('messages', [])
        for i, msg in enumerate(messages):
            print(f"消息 {i}: {type(msg).__name__} - {msg.content[:200]}...")
            
            # 检查是否有工具调用
            if hasattr(msg, 'tool_calls') and msg.tool_calls:
                print(f"🎯 消息 {i} 包含工具调用: {msg.tool_calls}")
            
    except Exception as e:
        print(f"❌ Agent执行失败: {e}")
        import traceback
        traceback.print_exc()


def test_tool_parsing():
    """测试工具调用解析"""
    print("\n=== 测试工具调用解析 ===")
    
    # 初始化配置
    config = ConfigManager()
    config_dir = Path(__file__).resolve().parent / "src" / "conf"
    config.init(config_dir)
    
    # 创建增强的StreamingLLMAdapter
    llm = StreamingLLMAdapter(
        model="qwen-turbo",
        api_key=config.get_config().get("api.qwen.api_key"),
        base_url=config.get_config().get("api.qwen.base_url"),
        default_params={}
    )
    
    # 测试不同的输出格式
    test_outputs = [
        "我需要使用TestTool来处理数据。\nAction: TestTool\nAction Input: 一些测试数据",
        "让我调用工具。\nAction: TestTool\nAction Input: {\"data\": \"test\"}",
        "这是一个普通的回复，没有工具调用。",
        "Action: TestTool\nAction Input: 数据1\nAction: AnotherTool\nAction Input: 数据2"
    ]
    
    for i, output in enumerate(test_outputs):
        print(f"\n测试输出 {i+1}:")
        print(f"输出内容: {output}")
        
        tool_calls = llm._parse_tool_calls(output)
        if tool_calls:
            print(f"🎯 解析到工具调用: {tool_calls}")
        else:
            print("⚠️ 没有解析到工具调用")


if __name__ == "__main__":
    test_tool_parsing()
    test_direct_tool_calling()
    test_with_agent() 