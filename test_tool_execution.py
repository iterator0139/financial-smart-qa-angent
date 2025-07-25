#!/usr/bin/env python3
"""
测试工具执行
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage
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


def test_direct_tool():
    """直接测试工具"""
    print("=== 直接测试工具 ===")
    tool = create_test_tool()
    result = tool.func("测试输入")
    print(f"直接调用结果: {result}")


def test_langgraph_agent():
    """测试LangGraph Agent"""
    print("\n=== 测试LangGraph Agent ===")
    
    # 初始化配置
    config = ConfigManager()
    config_dir = Path(__file__).resolve().parent / "src" / "conf"
    config.init(config_dir)
    
    # 创建测试工具
    tool = create_test_tool()
    
    # 创建LLM
    llm = StreamingLLMAdapter(
        model="qwen-turbo",
        api_key=config.get_config().get("api.qwen.api_key"),
        base_url=config.get_config().get("api.qwen.base_url"),
        default_params={}
    )
    
    # 创建Agent
    agent = create_react_agent(
        model=llm,
        tools=[tool],
        prompt="Answer the following questions as best you can. You have access to the following tools:\n\n{tools}\n\nUse the following format:\n\nQuestion: {input}\nThought: I should use a tool to help answer this question.\nAction: {tool_names}\nObservation: {tool_outputs}\nThought: I now know the final answer.\nFinal Answer: {output}\n\nBegin!\n\nQuestion: {input}\nThought:{agent_scratchpad}"
    )
    
    print("✅ Agent创建成功")
    
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
            print(f"消息 {i}: {type(msg).__name__} - {msg.content[:100]}...")
            
    except Exception as e:
        print(f"❌ Agent执行失败: {e}")
        import traceback
        traceback.print_exc()


def test_with_custom_prompt():
    """使用自定义prompt测试"""
    print("\n=== 使用自定义prompt测试 ===")
    
    # 初始化配置
    config = ConfigManager()
    config_dir = Path(__file__).resolve().parent / "src" / "conf"
    config.init(config_dir)
    
    # 创建测试工具
    tool = create_test_tool()
    
    # 创建LLM
    llm = StreamingLLMAdapter(
        model="qwen-turbo",
        api_key=config.get_config().get("api.qwen.api_key"),
        base_url=config.get_config().get("api.qwen.base_url"),
        default_params={}
    )
    
    # 自定义prompt，强制使用工具
    custom_prompt = """你是一个智能助手，可以使用工具来完成任务。

可用工具：
{tools}

使用以下格式：
Question: 用户问题
Thought: 我需要思考如何解决这个问题
Action: 工具名称
Action Input: 工具输入
Observation: 工具输出
... (可以重复多次)
Thought: 我现在知道答案了
Final Answer: 最终答案

开始！

Question: {input}
{agent_scratchpad}"""
    
    # 创建Agent
    agent = create_react_agent(
        model=llm,
        tools=[tool],
        prompt=custom_prompt
    )
    
    print("✅ 自定义Agent创建成功")
    
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
            
    except Exception as e:
        print(f"❌ Agent执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_direct_tool()
    test_langgraph_agent()
    test_with_custom_prompt() 