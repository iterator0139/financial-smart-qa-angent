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
from langgraph.prebuilt import ToolNode, create_react_agent
from langchain_core.callbacks import BaseCallbackHandler

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


class ReActAgent:
    """
    标准的ReAct Agent实现
    
    基于LangGraph的create_react_agent构建，支持：
    - 工具调用
    - 流式输出
    - 状态管理
    - 错误处理
    - 详细的执行日志
    """
    
    def __init__(
        self,
        model_name: str = "qwen-turbo",
        tools: Optional[List[Tool]] = None,
        prompt: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,

        **kwargs
    ):
        """
        初始化ReAct Agent
        
        Args:
            model_name: 模型名称
            tools: 工具列表
            prompt: 自定义prompt
            config: 配置管理器
            enable_logging: 是否启用详细日志
            **kwargs: 其他参数
        """
        self.model_name = model_name
        self.tools = tools or []
        self.prompt = prompt or REACT_PROMPT
        self.config = config
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
        
        # 创建ReAct agent（已经是编译好的图）
        self.app = self._create_agent()
        
        self.log.info(f"ReAct Agent initialized with model: {self.model_name}")
    
    def _create_agent(self):
        """
        创建ReAct agent
        
        Returns:
            LangGraph agent实例
        """
        
        agent = create_react_agent(
            model=self.llm,
            tools=self.tools,
            prompt=self.prompt,
        )
        
        return agent
    
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
            
            # 准备输入 - LangGraph期望messages格式
            inputs = {
                "messages": [{"role": "user", "content": input_text}]
            }
            
            # 准备回调
            callbacks = [self.callback_handler] 
            
            # 执行agent
            result = self.app.invoke(inputs, config={"callbacks": callbacks})
            
            self.log.info(f"[AGENT_END] Agent推理完成")
            
            # 添加工具执行摘要到结果中
            if self.callback_handler:
                tool_summary = self.callback_handler.get_tool_execution_summary()
                result["tool_execution_summary"] = tool_summary
                self.log.info(f"[TOOL_SUMMARY] 工具执行摘要: {tool_summary}")
            
            return result
            
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
            
            # 准备输入 - LangGraph期望messages格式
            inputs = {
                "messages": [{"role": "user", "content": input_text}]
            }
            
            # 准备回调
            callbacks = [self.callback_handler] 
            
            # 流式执行agent
            for chunk in self.app.stream(inputs, config={"callbacks": callbacks}):
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
        # 重新创建agent以包含新工具
        self.app = self._create_agent()
        self.log.info(f"Added tool: {tool.name}")
    
    def remove_tool(self, tool_name: str):
        """
        从agent中移除工具
        
        Args:
            tool_name: 要移除的工具名称
        """
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
        # 重新创建agent
        self.app = self._create_agent()
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
        # 重新创建agent
        self.app = self._create_agent()
        self.log.info("Updated agent prompt")
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """
        获取执行摘要
        
        Returns:
            执行摘要信息
        """
        if self.callback_handler:
            return self.callback_handler.get_tool_execution_summary()
        return {"total_tools": 0, "tools": []}


# 创建默认的ReAct Agent实例
def create_default_react_agent(
    model_name: str = "qwen-turbo",
    custom_tools: Optional[List[Tool]] = None,
    custom_prompt: Optional[str] = None,

    **kwargs
) -> ReActAgent:
    """
    创建默认的ReAct Agent实例
    
    Args:
        model_name: 模型名称
        custom_tools: 自定义工具列表
        custom_prompt: 自定义prompt
        enable_logging: 是否启用详细日志
        **kwargs: 其他参数
        
    Returns:
        ReActAgent实例
    """
    # 使用默认工具或自定义工具
    agent_tools = custom_tools if custom_tools is not None else tools
    
    return ReActAgent(
        model_name=model_name,
        tools=agent_tools,
        prompt=custom_prompt,
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
    
    # 创建ReAct Agent
    logger.info("初始化ReAct Agent...")
    agent = create_default_react_agent(
        model_name="qwen-turbo",
        config=config
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
    agent = create_default_react_agent()
    
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
    # demo_custom_tools()
