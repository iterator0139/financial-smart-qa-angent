#!/usr/bin/env python3
"""
使用官方LangChain模型测试工具调用
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from langchain_core.tools import Tool
from langgraph.prebuilt import create_react_agent
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
    print("\n=== 直接测试工具调用 ===")
    
    # 初始化配置
    config = ConfigManager()
    config_dir = Path(__file__).resolve().parent / "src" / "conf"
    config.init(config_dir)
    
    # 获取OpenAI配置
    openai_api_key = config.get_config().get("api.openai.api_key")
    if not openai_api_key:
        print("❌ 未找到OpenAI API密钥，跳过测试")
        return
    
    # 创建测试工具
    test_tool = create_test_tool()
    
    try:
        # 尝试导入OpenAI
        from langchain_openai import ChatOpenAI
        
        # 创建OpenAI模型
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            api_key=openai_api_key,
            temperature=0
        )
        
        # 绑定工具
        llm_with_tools = llm.bind_tools([test_tool])
        
        print("✅ 模型创建成功，工具已绑定")
        
        # 直接调用模型
        from langchain_core.messages import HumanMessage
        
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
            
    except ImportError:
        print("❌ 未安装langchain_openai，尝试使用其他模型")
        try:
            from langchain_anthropic import ChatAnthropic
            
            # 获取Anthropic配置
            anthropic_api_key = config.get_config().get("api.anthropic.api_key")
            if not anthropic_api_key:
                print("❌ 未找到Anthropic API密钥，跳过测试")
                return
            
            # 创建Anthropic模型
            llm = ChatAnthropic(
                model="claude-3-haiku-20240307",
                api_key=anthropic_api_key,
                temperature=0
            )
            
            # 绑定工具
            llm_with_tools = llm.bind_tools([test_tool])
            
            print("✅ Anthropic模型创建成功，工具已绑定")
            
            # 直接调用模型
            from langchain_core.messages import HumanMessage
            
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
                
        except ImportError:
            print("❌ 未安装相关依赖包")
            print("请安装: pip install langchain-openai langchain-anthropic")
            
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
    
    try:
        # 尝试导入OpenAI
        from langchain_openai import ChatOpenAI
        
        # 获取OpenAI配置
        openai_api_key = config.get_config().get("api.openai.api_key")
        if not openai_api_key:
            print("❌ 未找到OpenAI API密钥，跳过测试")
            return
        
        # 创建OpenAI模型
        llm = ChatOpenAI(
            model="gpt-3.5-turbo",
            api_key=openai_api_key,
            temperature=0
        )
        
        # 绑定工具
        llm_with_tools = llm.bind_tools([test_tool])
        
        # 创建Agent
        agent = create_react_agent(
            model=llm_with_tools,
            tools=[test_tool]
        )
        
        print("✅ OpenAI Agent创建成功")
        
        # 测试查询
        query = "请使用TestTool工具处理一些数据"
        print(f"测试查询: {query}")
        
        result = agent.invoke({
            "messages": [{"role": "user", "content": query}]
        })
        
        print(f"Agent结果: {result}")
        
        # 检查消息
        messages = result.get('messages', [])
        for i, msg in enumerate(messages):
            print(f"消息 {i}: {type(msg).__name__} - {msg.content[:200]}...")
            
    except ImportError:
        print("❌ 未安装langchain_openai，尝试使用其他模型")
        try:
            from langchain_anthropic import ChatAnthropic
            
            # 获取Anthropic配置
            anthropic_api_key = config.get_config().get("api.anthropic.api_key")
            if not anthropic_api_key:
                print("❌ 未找到Anthropic API密钥，跳过测试")
                return
            
            # 创建Anthropic模型
            llm = ChatAnthropic(
                model="claude-3-haiku-20240307",
                api_key=anthropic_api_key,
                temperature=0
            )
            
            # 绑定工具
            llm_with_tools = llm.bind_tools([test_tool])
            
            # 创建Agent
            agent = create_react_agent(
                model=llm_with_tools,
                tools=[test_tool]
            )
            
            print("✅ Anthropic Agent创建成功")
            
            # 测试查询
            query = "请使用TestTool工具处理一些数据"
            print(f"测试查询: {query}")
            
            result = agent.invoke({
                "messages": [{"role": "user", "content": query}]
            })
            
            print(f"Agent结果: {result}")
            
            # 检查消息
            messages = result.get('messages', [])
            for i, msg in enumerate(messages):
                print(f"消息 {i}: {type(msg).__name__} - {msg.content[:200]}...")
                
        except ImportError:
            print("❌ 未安装相关依赖包")
            print("请安装: pip install langchain-openai langchain-anthropic")
            
    except Exception as e:
        print(f"❌ Agent执行失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_direct_tool_calling()
    test_with_agent() 