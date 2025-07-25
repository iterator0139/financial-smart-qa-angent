"""
LangGraph create_react_agent 使用示例
演示如何创建一个智能代理来处理用户查询
"""

from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# 1. 定义工具函数
def search_web(query: str) -> str:
    """搜索网络信息"""
    # 这里应该是实际的网络搜索实现
    return f"搜索结果: {query} 的相关信息"

def calculate(expression: str) -> str:
    """计算数学表达式"""
    try:
        result = eval(expression)
        return f"计算结果: {expression} = {result}"
    except:
        return f"无法计算表达式: {expression}"

def get_weather(location: str) -> str:
    """获取天气信息"""
    # 这里应该是实际的天气API调用
    return f"{location} 的天气: 晴天，25°C"

# 2. 定义状态模式（可选）
class CustomAgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    remaining_steps: int

# 3. 创建代理
def create_my_agent():
    """创建一个具有多个工具的智能代理"""
    
    # 定义系统提示
    system_prompt = """你是一个智能助手，可以帮助用户：
    1. 搜索网络信息
    2. 进行数学计算
    3. 查询天气信息
    
    请根据用户的需求选择合适的工具。如果用户的问题需要多个步骤，请逐步解决。"""
    
    # 创建代理
    agent = create_react_agent(
        model="anthropic:claude-3-5-sonnet-20241022",  # 使用Claude模型
        tools=[search_web, calculate, get_weather],     # 工具列表
        prompt=system_prompt,                           # 系统提示
        version="v2",                                   # 使用v2版本
        name="智能助手",                                # 代理名称
        debug=True                                      # 启用调试模式
    )
    
    return agent

# 4. 使用代理
def use_agent():
    """演示如何使用代理"""
    
    # 创建代理
    agent = create_my_agent()
    
    # 准备输入
    messages = [
        HumanMessage(content="请帮我计算 15 * 23 的结果，然后搜索一下关于人工智能的最新信息")
    ]
    
    # 调用代理
    print("开始处理用户请求...")
    result = agent.invoke({"messages": messages})
    
    # 显示结果
    print("\n=== 代理处理结果 ===")
    for message in result["messages"]:
        print(f"{message.__class__.__name__}: {message.content}")
    
    return result

# 5. 流式处理示例
def stream_agent():
    """演示流式处理"""
    
    agent = create_my_agent()
    messages = [HumanMessage(content="北京今天的天气怎么样？")]
    
    print("开始流式处理...")
    for chunk in agent.stream({"messages": messages}, stream_mode="updates"):
        print(f"更新: {chunk}")

# 6. 带钩子的代理示例
def create_agent_with_hooks():
    """创建带有pre/post钩子的代理"""
    
    def pre_model_hook(state):
        """模型调用前的钩子 - 可以用于消息预处理"""
        messages = state["messages"]
        print(f"预处理: 当前有 {len(messages)} 条消息")
        return {"messages": messages}
    
    def post_model_hook(state):
        """模型调用后的钩子 - 可以用于结果验证"""
        messages = state["messages"]
        last_message = messages[-1]
        print(f"后处理: 最后一条消息类型: {type(last_message).__name__}")
        return {"messages": messages}
    
    agent = create_react_agent(
        model="anthropic:claude-3-5-sonnet-20241022",
        tools=[search_web, calculate, get_weather],
        prompt="你是一个有用的助手",
        pre_model_hook=pre_model_hook,
        post_model_hook=post_model_hook,
        version="v2"
    )
    
    return agent

if __name__ == "__main__":
    print("=== LangGraph ReAct Agent 示例 ===\n")
    
    # 基本使用
    print("1. 基本代理使用:")
    use_agent()
    
    print("\n" + "="*50 + "\n")
    
    # 流式处理
    print("2. 流式处理:")
    stream_agent()
    
    print("\n" + "="*50 + "\n")
    
    # 带钩子的代理
    print("3. 带钩子的代理:")
    hook_agent = create_agent_with_hooks()
    result = hook_agent.invoke({
        "messages": [HumanMessage(content="计算 10 + 20")]
    })
    print("钩子代理处理完成") 