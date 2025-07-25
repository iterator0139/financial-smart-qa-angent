import sys
from pathlib import Path
import logging
from typing import TypedDict, List, Dict, Optional, Any, Annotated, Literal
from dataclasses import dataclass, field
from datetime import datetime
import json
import hashlib
from abc import ABC, abstractmethod
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import Tool
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.callbacks import BaseCallbackHandler
import re

# Add project root to path first
project_root = Path(__file__).resolve().parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

# Now import local modules
from src.models.streaming_adapter import StreamingLLMAdapter
from src.utils.logger import get_logger
from src.config.config_manager import ConfigManager
from src.tools.db_tool import query_db, check_db_info
from src.tools.embedding_tool import embedding_search
from src.tools.es_tool import search_es
from src.tools.file_tool import select_file
from src.tools.query2sql import query_to_sql
from src.prompts import REACT_PROMPT


log = get_logger()

tools = [
    Tool(
        name="ESSearch",
        description="Search the ES index",
        func=search_es
    ),
    Tool(
        name="QueryDB",
        description="Query the DB",
        func=query_db
    ),
    Tool(
        name="EmbeddingSearch",
        description="Search the embedding index",
        func=embedding_search
    ),
    Tool(
        name="QueryToSQL",
        description="Query the DB to SQL",
        func=query_to_sql
    ),
    Tool(
        name="SelectFile",
        description="Select the file",
        func=select_file
    ),
    Tool(
        name="CheckDBInfo",
        description="Check the DB info",
        func=check_db_info
    ),
]

# 定义状态类型
class AgentState(TypedDict):
    """Agent执行状态"""
    messages: List[Dict[str, Any]]  # 消息历史
    current_step: int  # 当前步骤
    max_steps: int  # 最大步骤数
    scratchpad: str  # 推理过程记录
    tool_results: List[Dict[str, Any]]  # 工具执行结果
    final_answer: Optional[str]  # 最终答案
    error: Optional[str]  # 错误信息
    is_finished: bool  # 是否完成


class ResponseFormat(BaseModel):
    """Response format for the agent."""
    result: str


class ToolExecutionCallback(BaseCallbackHandler):
    """工具执行回调处理器，用于监控工具调用"""
    
    def __init__(self):
        self.log = get_logger()
        self.tool_calls = []
        self.current_tool = None
    
    def on_tool_start(self, serialized: Dict[str, Any], input_str: str, **kwargs):
        """工具开始执行时的回调"""
        tool_name = serialized.get("name", "unknown")
        self.log.info(f"[TOOL_START] {tool_name} 开始执行")
        self.log.info(f"[TOOL_INPUT] {tool_name} 输入: {input_str}")
        
        self.current_tool = {
            "name": tool_name,
            "input": input_str,
            "start_time": datetime.now()
        }
    
    def on_tool_end(self, output: str, **kwargs):
        """工具执行结束时的回调"""
        if self.current_tool:
            tool_name = self.current_tool["name"]
            end_time = datetime.now()
            duration = (end_time - self.current_tool["start_time"]).total_seconds()
            
            self.log.info(f"[TOOL_END] {tool_name} 执行完成 (耗时: {duration:.2f}s)")
            self.log.info(f"[TOOL_OUTPUT] {tool_name} 输出: {output}")
            
            self.tool_calls.append({
                **self.current_tool,
                "output": output,
                "end_time": end_time,
                "duration": duration
            })
            self.current_tool = None
    
    def on_tool_error(self, error: str, **kwargs):
        """工具执行错误时的回调"""
        if self.current_tool:
            tool_name = self.current_tool["name"]
            self.log.error(f"[TOOL_ERROR] {tool_name} 执行失败: {error}")
            
            self.tool_calls.append({
                **self.current_tool,
                "error": error,
                "end_time": datetime.now()
            })
            self.current_tool = None
    
    def on_llm_start(self, serialized: Dict[str, Any], prompts: List[str], **kwargs):
        """LLM开始执行时的回调"""
        self.log.info(f"[LLM_START] 模型开始推理")
    
    def on_llm_end(self, response, **kwargs):
        """LLM执行结束时的回调"""
        self.log.info(f"[LLM_END] 模型推理完成")
    
    def on_llm_error(self, error: str, **kwargs):
        """LLM执行错误时的回调"""
        self.log.error(f"[LLM_ERROR] 模型推理失败: {error}")
    
    def get_tool_execution_summary(self):
        """获取工具执行摘要"""
        return {
            "total_tools": len(self.tool_calls),
            "tools": self.tool_calls
        }


class CustomReActAgent:
    """
    自定义ReAct Agent实现
    
    基于LangGraph构建，支持：
    - 完全可控的推理流程
    - 工具调用
    - 流式输出
    - 状态管理
    - 错误处理
    - 详细的执行日志
    - 可定制的推理步骤
    """
    
    def __init__(
        self,
        model_name: str = "qwen-turbo",
        tools: Optional[List[Tool]] = None,
        prompt: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        max_steps: int = 10,
        **kwargs
    ):
        """
        初始化自定义ReAct Agent
        
        Args:
            model_name: 模型名称
            tools: 工具列表
            prompt: 自定义prompt
            config: 配置管理器
            max_steps: 最大推理步骤数
            **kwargs: 其他参数
        """
        self.model_name = model_name
        self.tools = tools or []
        self.prompt = prompt or REACT_PROMPT
        self.config = config
        self.max_steps = max_steps
        self.log = get_logger()
        
        # 初始化回调处理器
        self.callback_handler = ToolExecutionCallback()
        
        # 初始化模型
        self.llm = StreamingLLMAdapter(
            model=model_name,
            api_key=self.config.get("api.qwen.api_key"),
            base_url=self.config.get("api.qwen.base_url"),
            streaming_models=self.config.get("api.qwen.streaming_models"),
            stream_enabled=self.config.get("api.qwen.stream_enabled"),
            default_params=self.config.get("api.qwen.default_params"),
            **kwargs
        )
        
        # 创建工具映射
        self.tool_map = {tool.name: tool for tool in self.tools}
        
        # 创建自定义ReAct图
        self.app = self._create_custom_react_graph()
        
        self.log.info(f"Custom ReAct Agent initialized with model: {model_name}, max_steps: {max_steps}")
    
    def _create_custom_react_graph(self):
        """
        创建自定义ReAct执行图
        
        Returns:
            LangGraph StateGraph实例
        """
        # 创建状态图
        workflow = StateGraph(AgentState)
        
        # 添加节点
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", self._tools_node)
        
        # 设置入口和出口
        workflow.set_entry_point("agent")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "tools": "tools",
                "end": END
            }
        )
        
        workflow.add_edge("tools", "agent")
        
        # 编译图
        return workflow.compile()
    
    def _agent_node(self, state: AgentState) -> AgentState:
        """
        Agent推理节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        try:
            # 增加步骤计数
            state["current_step"] += 1
            self.log.info(f"[AGENT_NODE] 步骤 {state['current_step']} - 开始推理")
            
            # 构建完整的prompt
            full_prompt = self._build_prompt(state)
            
            # 调用LLM
            response = self.llm.invoke(full_prompt)
            
            # 解析响应
            parsed_response = self._parse_agent_response(response)
            
            # 更新状态
            state["scratchpad"] += f"\n{parsed_response['thought']}\n{parsed_response['action']}"
            
            if parsed_response["action_type"] == "finish":
                state["final_answer"] = parsed_response["action_input"]
                state["is_finished"] = True
                self.log.info(f"[AGENT_NODE] 推理完成，最终答案: {state['final_answer']}")
            else:
                # 准备工具调用
                state["next_tool"] = {
                    "name": parsed_response["action_input"],
                    "input": parsed_response.get("tool_input", "")
                }
                self.log.info(f"[AGENT_NODE] 准备调用工具: {parsed_response['action_input']}")
            
            return state
            
        except Exception as e:
            self.log.error(f"[AGENT_NODE] 推理失败: {e}")
            state["error"] = str(e)
            state["is_finished"] = True
            return state
    
    def _tools_node(self, state: AgentState) -> AgentState:
        """
        工具执行节点
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        try:
            tool_info = state.get("next_tool")
            if not tool_info:
                state["error"] = "No tool to execute"
                state["is_finished"] = True
                return state
            
            tool_name = tool_info["name"]
            tool_input = tool_info["input"]
            
            self.log.info(f"[TOOLS_NODE] 执行工具: {tool_name}")
            
            # 查找工具
            if tool_name not in self.tool_map:
                error_msg = f"Tool '{tool_name}' not found"
                self.log.error(f"[TOOLS_NODE] {error_msg}")
                state["error"] = error_msg
                state["is_finished"] = True
                return state
            
            tool = self.tool_map[tool_name]
            
            # 执行工具
            try:
                tool_result = tool.func(tool_input)
                self.log.info(f"[TOOLS_NODE] 工具执行成功: {tool_result}")
                
                # 添加工具结果到状态
                state["tool_results"].append({
                    "tool": tool_name,
                    "input": tool_input,
                    "output": tool_result,
                    "step": state["current_step"]
                })
                
                # 添加观察结果到scratchpad
                state["scratchpad"] += f"\nObservation: {tool_result}"
                
            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                self.log.error(f"[TOOLS_NODE] {error_msg}")
                state["error"] = error_msg
                state["is_finished"] = True
                return state
            
            # 清理next_tool
            if "next_tool" in state:
                del state["next_tool"]
            
            return state
            
        except Exception as e:
            self.log.error(f"[TOOLS_NODE] 工具节点执行失败: {e}")
            state["error"] = str(e)
            state["is_finished"] = True
            return state
    
    def _should_continue(self, state: AgentState) -> str:
        """
        判断是否应该继续执行
        
        Args:
            state: 当前状态
            
        Returns:
            下一个节点名称
        """
        # 检查是否完成
        if state.get("is_finished", False):
            return "end"
        
        # 检查步骤数限制
        if state["current_step"] >= state["max_steps"]:
            state["error"] = f"Maximum steps ({state['max_steps']}) reached"
            state["is_finished"] = True
            return "end"
        
        # 检查是否有工具需要执行
        if "next_tool" in state:
            return "tools"
        
        # 继续推理
        return "end"
    
    def _build_prompt(self, state: AgentState) -> str:
        """
        构建完整的prompt
        
        Args:
            state: 当前状态
            
        Returns:
            完整的prompt字符串
        """
        # 获取工具描述
        tools_description = "\n".join([
            f"- {tool.name}: {tool.description}" 
            for tool in self.tools
        ])
        
        # 获取用户输入
        user_input = ""
        if state["messages"]:
            user_input = state["messages"][-1].get("content", "")
        
        # 构建prompt
        prompt = self.prompt.format(
            tools=tools_description,
            input=user_input,
            agent_scratchpad=state["scratchpad"]
        )
        
        return prompt
    
    def _parse_agent_response(self, response: str) -> Dict[str, Any]:
        """
        解析Agent响应
        
        Args:
            response: LLM响应
            
        Returns:
            解析后的响应字典
        """
        try:
            # 提取Thought
            thought_match = re.search(r'Thought\s*\d*:\s*(.*?)(?=\nAction|\n$)', response, re.DOTALL)
            thought = thought_match.group(1).strip() if thought_match else ""
            
            # 提取Action
            action_match = re.search(r'Action\s*\d*:\s*(.*?)(?=\n|$)', response, re.DOTALL)
            action = action_match.group(1).strip() if action_match else ""
            
            # 解析Action
            if action.lower().startswith("finish"):
                # 提取最终答案
                answer_match = re.search(r'finish\[(.*?)\]', action, re.IGNORECASE)
                answer = answer_match.group(1) if answer_match else action
                
                return {
                    "thought": thought,
                    "action": action,
                    "action_type": "finish",
                    "action_input": answer
                }
            else:
                # 工具调用
                tool_name = action.strip()
                return {
                    "thought": thought,
                    "action": action,
                    "action_type": "tool",
                    "action_input": tool_name
                }
                
        except Exception as e:
            self.log.error(f"Failed to parse agent response: {e}")
            return {
                "thought": "",
                "action": "",
                "action_type": "error",
                "action_input": str(e)
            }
    
    def invoke(self, input_text: str) -> Dict[str, Any]:
        """
        执行agent推理
        
        Args:
            input_text: 输入文本
        Returns:
            agent执行结果
        """
        try:
            self.log.info(f"[AGENT_START] 开始执行Agent推理")
            self.log.info(f"[AGENT_INPUT] 输入: {input_text}")
            
            # 初始化状态
            initial_state = {
                "messages": [{"role": "user", "content": input_text}],
                "current_step": 0,
                "max_steps": self.max_steps,
                "scratchpad": "",
                "tool_results": [],
                "final_answer": None,
                "error": None,
                "is_finished": False
            }
            
            # 准备回调
            callbacks = [self.callback_handler]
            
            # 执行图
            result = self.app.invoke(initial_state, config={"callbacks": callbacks})
            
            self.log.info(f"[AGENT_END] Agent推理完成")
            
            # 构建返回结果
            response = {
                "final_answer": result.get("final_answer"),
                "error": result.get("error"),
                "scratchpad": result.get("scratchpad"),
                "tool_results": result.get("tool_results", []),
                "steps_taken": result.get("current_step", 0)
            }
            
            # 添加工具执行摘要
            if self.callback_handler:
                tool_summary = self.callback_handler.get_tool_execution_summary()
                response["tool_execution_summary"] = tool_summary
                self.log.info(f"[TOOL_SUMMARY] 工具执行摘要: {tool_summary}")
            
            return response
            
        except Exception as e:
            self.log.error(f"[AGENT_ERROR] Agent执行失败: {e}")
            raise
    
    def stream(self, input_text: str):
        """
        流式执行agent推理
        
        Args:
            input_text: 输入文本
            
        Yields:
            流式输出结果
        """
        try:
            self.log.info(f"[AGENT_STREAM_START] 开始流式执行Agent推理")
            self.log.info(f"[AGENT_INPUT] 输入: {input_text}")
            
            # 初始化状态
            initial_state = {
                "messages": [{"role": "user", "content": input_text}],
                "current_step": 0,
                "max_steps": self.max_steps,
                "scratchpad": "",
                "tool_results": [],
                "final_answer": None,
                "error": None,
                "is_finished": False
            }
            
            # 准备回调
            callbacks = [self.callback_handler]
            
            # 流式执行图
            for chunk in self.app.stream(initial_state, config={"callbacks": callbacks}):
                yield chunk
                
            self.log.info(f"[AGENT_STREAM_END] 流式执行完成")
                
        except Exception as e:
            self.log.error(f"[AGENT_STREAM_ERROR] 流式执行失败: {e}")
            raise
    
    def add_tool(self, tool: Tool):
        """
        添加工具到agent
        
        Args:
            tool: 要添加的工具
        """
        self.tools.append(tool)
        self.tool_map[tool.name] = tool
        self.log.info(f"Added tool: {tool.name}")
    
    def remove_tool(self, tool_name: str):
        """
        从agent中移除工具
        
        Args:
            tool_name: 要移除的工具名称
        """
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
        if tool_name in self.tool_map:
            del self.tool_map[tool_name]
        self.log.info(f"Removed tool: {tool_name}")
    
    def get_tools(self) -> List[Tool]:
        """
        获取当前所有工具
        
        Returns:
            工具列表
        """
        return self.tools.copy()
    
    def update_prompt(self, new_prompt: str):
        """
        更新agent的prompt
        
        Args:
            new_prompt: 新的prompt模板
        """
        self.prompt = new_prompt
        self.log.info("Updated agent prompt")
    
    def set_max_steps(self, max_steps: int):
        """
        设置最大推理步骤数
        
        Args:
            max_steps: 最大步骤数
        """
        self.max_steps = max_steps
        self.log.info(f"Updated max steps to: {max_steps}")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            执行摘要信息
        """
        if self.callback_handler:
            return self.callback_handler.get_tool_execution_summary()
        return {"total_tools": 0, "tools": []}


# 创建默认的自定义ReAct Agent实例
def create_default_custom_react_agent(
    model_name: str = "qwen-turbo",
    custom_tools: Optional[List[Tool]] = None,
    custom_prompt: Optional[str] = None,
    max_steps: int = 10,
    **kwargs
) -> CustomReActAgent:
    """
    创建默认的自定义ReAct Agent实例
    
    Args:
        model_name: 模型名称
        custom_tools: 自定义工具列表
        custom_prompt: 自定义prompt
        max_steps: 最大推理步骤数
        **kwargs: 其他参数
        
    Returns:
        CustomReActAgent实例
    """
    # 使用默认工具或自定义工具
    agent_tools = custom_tools if custom_tools is not None else tools
    
    return CustomReActAgent(
        model_name=model_name,
        tools=agent_tools,
        prompt=custom_prompt,
        max_steps=max_steps,
        **kwargs
    )


def main():
    """主示例函数"""
    # 初始化日志系统
    from src.utils.logger import logger as async_logger
    async_logger.init()  # 初始化日志系统
    
    # 获取日志器
    logger = get_logger()
    config = ConfigManager()
    
    # 初始化配置
    config_dir = Path(__file__).resolve().parent.parent / "conf"
    config.init(config_dir)
    
    # 创建自定义ReAct Agent
    logger.info("初始化自定义ReAct Agent...")
    agent = create_default_custom_react_agent(
        model_name="qwen-turbo",
        config=config,
        max_steps=8
    )
    
    # 示例查询列表
    query = "请帮我查询出20210415日，建筑材料一级行业涨幅超过5%（不包含）的股票数量。"
    
    logger.info("开始执行查询...")
    print("=" * 50)
    print("查询结果:")
    print("=" * 50)
    
    try:
        # 使用新版本的invoke方法
        result = agent.invoke(query)
        
        print(f"最终答案: {result.get('final_answer')}")
        print(f"推理步骤: {result.get('steps_taken')}")
        print(f"工具调用次数: {len(result.get('tool_results', []))}")
        
        if result.get('error'):
            print(f"错误信息: {result['error']}")
        
        logger.info(f"查询结果: {result}")
        
    except Exception as e:
        print(f"❌ 查询执行失败: {e}")
        logger.error(f"查询执行失败: {e}")
    
    print("=" * 50)
    logger.info("查询完成")


def demo_streaming():
    """演示流式输出功能"""
    print("\n" + "="*60)
    print("🔄 流式输出演示")
    print("="*60)
    
    # 创建agent
    agent = create_default_custom_react_agent()
    
    # 流式查询
    query = "请帮我检查数据库信息"
    
    try:
        print(f"🔍 流式查询: {query}")
        print("-" * 40)
        
        for chunk in agent.stream(query):
            print(f"📦 数据块: {chunk}")
            
    except Exception as e:
        print(f"❌ 流式查询失败: {e}")


if __name__ == "__main__":
    # 运行基本示例
    main()    
    # 运行其他演示
    # demo_streaming()
