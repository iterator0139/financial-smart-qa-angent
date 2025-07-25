"""
Streaming LLM Adapter for LangChain

提供一个同时支持流式和非流式输出的LangChain适配器。
可以根据模型名称自动判断是否使用流式API并最终返回完整结果。
支持工具调用功能。
"""

from typing import Any, Dict, List, Optional, Union, Iterator, Callable
import time
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    FunctionMessage,
    HumanMessage,
    ToolMessage
)
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.tools import BaseTool
from src.utils.logger import get_logger
import dashscope
from src.config.config_manager import ConfigManager

log = get_logger()

# 流式输出的模型列表
STREAMING_MODELS = ['qwq-32b', 'qwq-plus', 'qwq-plus-latest']


class StreamingLLMAdapter(BaseChatModel):
    """
    同时支持流式和非流式输出的LangChain适配器
    
    特点:
    1. 自动根据模型名称决定使用流式或非流式API
    2. 对于流式API，会积累所有输出最终返回完整结果
    3. 完全兼容LangChain接口
    4. 支持回调，可用于UI展示流式输出
    5. 支持工具调用功能
    """
    
    model_version: str = "qwen-turbo"
    streaming_models: List[str] = STREAMING_MODELS
    stream_enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_params: Dict[str, Any] = {}
    _tools: Optional[List[BaseTool]] = None
    
    def __init__(
        self,
        model: str = "qwen-turbo",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        streaming_models: Optional[List[str]] = None,
        stream_enabled: bool = True,
        **kwargs
    ):
        """
        初始化适配器
        
        Args:
            model: 模型名称
            api_key: API密钥
            base_url: API基础URL
            streaming_models: 支持流式输出的模型列表
            stream_enabled: 是否启用流式输出(如设为False将强制禁用流式)
            **kwargs: 其他参数，将作为默认参数传递给模型
        """
        super().__init__(**kwargs)
        self.model_version = model
        self.api_key = api_key
        self.base_url = base_url
        self.default_params = kwargs
        self.stream_enabled = stream_enabled
        self._tools = []
        
        if streaming_models:
            self.streaming_models = streaming_models
        
        # 如果未提供API密钥，从配置中获取
        if not self.api_key:
            config = ConfigManager()
            self.api_key = config.get("api.qwen.api_key")
            if not self.api_key:
                raise ValueError("API key is required")
        
        # 设置DashScope API密钥
        dashscope.api_key = self.api_key
        
    @property
    def _llm_type(self) -> str:
        """返回LLM类型"""
        return "streaming-llm-adapter"
    
    def bind_tools(self, tools: List[BaseTool]) -> "StreamingLLMAdapter":
        """
        绑定工具到模型
        
        Args:
            tools: 工具列表
            
        Returns:
            绑定工具后的模型实例
        """
        # 创建一个新的实例，保持原有配置
        new_instance = StreamingLLMAdapter(
            model=self.model_version,
            api_key=self.api_key,
            base_url=self.base_url,
            streaming_models=self.streaming_models,
            stream_enabled=self.stream_enabled,
            **self.default_params
        )
        
        # 存储工具信息
        new_instance._tools = tools
        
        return new_instance
    
    def is_streaming_model(self) -> bool:
        """
        根据当前配置判断是否使用流式API
        
        Returns:
            是否使用流式API
        """
        return (
            self.stream_enabled and 
            self.model_version in self.streaming_models
        )

    def _convert_messages_to_prompt(self, messages: List[BaseMessage]) -> List[Dict[str, str]]:
        """
        将LangChain消息转换为DashScope API所需的格式
        
        Args:
            messages: LangChain消息列表
            
        Returns:
            DashScope API格式的消息列表
        """
        dashscope_messages = []
        
        for message in messages:
            if isinstance(message, HumanMessage):
                dashscope_messages.append({
                    "role": "user",
                    "content": message.content
                })
            elif isinstance(message, AIMessage):
                dashscope_messages.append({
                    "role": "assistant",
                    "content": message.content
                })
            elif isinstance(message, FunctionMessage):
                dashscope_messages.append({
                    "role": "function",
                    "name": message.name,
                    "content": message.content
                })
            elif isinstance(message, ToolMessage):
                dashscope_messages.append({
                    "role": "function",
                    "name": message.name,
                    "content": message.content
                })
            else:
                dashscope_messages.append({
                    "role": "user",  # 默认角色
                    "content": str(message.content)
                })
        
        return dashscope_messages
    
    def _create_tool_calling_prompt(self, messages: List[BaseMessage]) -> str:
        """
        创建包含工具信息的prompt
        
        Args:
            messages: 消息列表
            
        Returns:
            包含工具信息的prompt
        """
        if not self._tools:
            return messages[-1].content if messages else ""
        
        # 构建工具描述
        tools_description = "可用工具:\n"
        for tool in self._tools:
            tools_description += f"- {tool.name}: {tool.description}\n"
        
        # 构建工具调用格式说明
        format_instruction = """
请使用以下格式调用工具:
Action: 工具名称
Action Input: 工具输入参数

例如:
Action: TestTool
Action Input: 要处理的数据

请根据用户需求选择合适的工具并调用。
"""
        
        # 获取用户消息
        user_message = messages[-1].content if messages else ""
        
        # 组合完整的prompt
        full_prompt = f"{tools_description}\n{format_instruction}\n\n用户问题: {user_message}\n\n请回答:"
        
        return full_prompt
    
    def _parse_tool_calls(self, content: str) -> List[Dict[str, Any]]:
        """
        从模型输出中解析工具调用
        
        Args:
            content: 模型输出内容
            
        Returns:
            工具调用列表
        """
        tool_calls = []
        
        # 简单的解析逻辑，查找Action和Action Input模式
        lines = content.split('\n')
        current_action = None
        current_input = None
        
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith('Action:'):
                current_action = line.replace('Action:', '').strip()
            elif line.startswith('Action Input:'):
                current_input = line.replace('Action Input:', '').strip()
                
                # 如果找到了工具名称和输入，创建工具调用
                if current_action and current_input:
                    # 尝试解析JSON格式的参数
                    try:
                        import json
                        args = json.loads(current_input)
                    except (json.JSONDecodeError, ValueError):
                        # 如果不是JSON格式，将其作为字符串参数
                        args = {"input": current_input}
                    
                    tool_calls.append({
                        "id": f"call_{len(tool_calls)}_{i}",
                        "name": current_action,
                        "args": args
                    })
                    current_action = None
                    current_input = None
        
        return tool_calls
    
    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        生成回复
        
        Args:
            messages: 输入消息列表
            stop: 停止序列
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            ChatResult对象
        """
        # 合并默认参数和传入的参数
        params = {**self.default_params, **kwargs}
        
        # 添加停止序列
        if stop:
            params["stop_sequences"] = stop
        
        # 如果有工具绑定，创建包含工具信息的prompt
        if self._tools:
            # 创建包含工具信息的prompt
            tool_prompt = self._create_tool_calling_prompt(messages)
            
            # 转换消息格式，使用工具prompt
            dashscope_messages = [{
                "role": "user",
                "content": tool_prompt
            }]
        else:
            # 转换消息格式
            dashscope_messages = self._convert_messages_to_prompt(messages)
        
        # 是否使用流式API
        use_stream = self.is_streaming_model()
        
        if use_stream:
            return self._stream_generate(dashscope_messages, run_manager, **params)
        else:
            return self._non_stream_generate(dashscope_messages, run_manager, **params)
    
    def _non_stream_generate(
        self,
        messages: List[Dict[str, str]],
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        非流式生成回复
        
        Args:
            messages: DashScope格式的消息列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            ChatResult对象
        """
        start_time = time.time()
        log.info(f"非流式调用模型 {self.model_version}")
        
        try:
            response = dashscope.Generation.call(
                model=self.model_version,
                messages=messages,
                result_format='message',
                **kwargs
            )
            
            end_time = time.time()
            log.info(f"模型调用完成，耗时: {end_time - start_time:.2f}秒")
            
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                
                # 如果有工具绑定，尝试解析工具调用
                if self._tools:
                    tool_calls = self._parse_tool_calls(content)
                    if tool_calls:
                        # 创建包含工具调用的AIMessage
                        message = AIMessage(
                            content=content,
                            tool_calls=tool_calls
                        )
                        log.info(f"检测到工具调用: {tool_calls}")
                    else:
                        # 创建普通AIMessage
                        message = AIMessage(content=content)
                else:
                    # 创建普通AIMessage
                    message = AIMessage(content=content)
                
                # 回调
                if run_manager:
                    run_manager.on_llm_new_token(content)
                
                return ChatResult(generations=[{"message": message}])
            else:
                error_msg = response.message
                log.error(f"模型调用失败: {error_msg}")
                raise ValueError(f"Model call failed: {error_msg}")
                
        except Exception as e:
            log.error(f"模型调用异常: {str(e)}")
            raise
    
    def _stream_generate(
        self,
        messages: List[Dict[str, str]],
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> ChatResult:
        """
        流式生成回复
        
        Args:
            messages: DashScope格式的消息列表
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Returns:
            ChatResult对象
        """
        start_time = time.time()
        log.info(f"流式调用模型 {self.model_version}")
        
        try:
            # 完整回复内容
            answer_content = ""
            # 完整思考过程
            reasoning_content = ""
            
            response = dashscope.Generation.call(
                model=self.model_version,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            for chunk in response:
                if (chunk.output.choices[0].message.content == "" and 
                    hasattr(chunk.output.choices[0].message, 'reasoning_content') and
                    chunk.output.choices[0].message.reasoning_content == ""):
                    continue
                    
                # 处理思考过程
                if (hasattr(chunk.output.choices[0].message, 'reasoning_content') and
                    chunk.output.choices[0].message.reasoning_content != "" and 
                    chunk.output.choices[0].message.content == ""):
                    reasoning_chunk = chunk.output.choices[0].message.reasoning_content
                    reasoning_content += reasoning_chunk
                    
                    # 回调思考过程
                    if run_manager:
                        run_manager.on_llm_new_token(reasoning_chunk)
                        
                # 处理回复内容
                elif chunk.output.choices[0].message.content != "":
                    content_chunk = chunk.output.choices[0].message.content
                    answer_content += content_chunk
                    
                    # 回调回复内容
                    if run_manager:
                        run_manager.on_llm_new_token(content_chunk)
            
            end_time = time.time()
            log.info(f"流式调用完成，耗时: {end_time - start_time:.2f}秒")
            
            # 组合最终内容
            final_content = reasoning_content + answer_content
            
            # 如果有工具绑定，尝试解析工具调用
            if self._tools:
                tool_calls = self._parse_tool_calls(final_content)
                if tool_calls:
                    # 创建包含工具调用的AIMessage
                    message = AIMessage(
                        content=final_content,
                        tool_calls=tool_calls
                    )
                    log.info(f"检测到工具调用: {tool_calls}")
                else:
                    # 创建普通AIMessage
                    message = AIMessage(content=final_content)
            else:
                # 创建普通AIMessage
                message = AIMessage(content=final_content)
            
            return ChatResult(generations=[{"message": message}])
            
        except Exception as e:
            log.error(f"流式调用异常: {str(e)}")
            raise
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> Iterator[ChatGenerationChunk]:
        """
        流式生成回复
        
        Args:
            messages: 输入消息列表
            stop: 停止序列
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Yields:
            ChatGenerationChunk对象
        """
        # 合并默认参数和传入的参数
        params = {**self.default_params, **kwargs}
        
        # 添加停止序列
        if stop:
            params["stop_sequences"] = stop
        
        # 如果有工具绑定，创建包含工具信息的prompt
        if self._tools:
            # 创建包含工具信息的prompt
            tool_prompt = self._create_tool_calling_prompt(messages)
            
            # 转换消息格式，使用工具prompt
            dashscope_messages = [{
                "role": "user",
                "content": tool_prompt
            }]
        else:
            # 转换消息格式
            dashscope_messages = self._convert_messages_to_prompt(messages)
        
        # 是否使用流式API
        use_stream = self.is_streaming_model()
        
        if not use_stream:
            # 如果不支持流式，使用非流式API并模拟流式输出
            result = self._non_stream_generate(dashscope_messages, run_manager, **params)
            message = result.generations[0]["message"]
            
            # 模拟流式输出
            content = message.content
            for i in range(0, len(content), 10):  # 每次输出10个字符
                chunk_content = content[i:i+10]
                chunk = ChatGenerationChunk(message=AIMessageChunk(content=chunk_content))
                yield chunk
        else:
            # 使用真正的流式API
            start_time = time.time()
            log.info(f"流式调用模型 {self.model_version}")
            
            try:
                response = dashscope.Generation.call(
                    model=self.model_version,
                    messages=dashscope_messages,
                    stream=True,
                    **params
                )
                
                for chunk in response:
                    if (chunk.output.choices[0].message.content == "" and 
                        hasattr(chunk.output.choices[0].message, 'reasoning_content') and
                        chunk.output.choices[0].message.reasoning_content == ""):
                        continue
                        
                    # 处理思考过程
                    if (hasattr(chunk.output.choices[0].message, 'reasoning_content') and
                        chunk.output.choices[0].message.reasoning_content != "" and 
                        chunk.output.choices[0].message.content == ""):
                        reasoning_chunk = chunk.output.choices[0].message.reasoning_content
                        
                        # 回调思考过程
                        if run_manager:
                            run_manager.on_llm_new_token(reasoning_chunk)
                        
                        # 生成chunk
                        chunk_obj = ChatGenerationChunk(
                            message=AIMessageChunk(content=reasoning_chunk)
                        )
                        yield chunk_obj
                        
                    # 处理回复内容
                    elif chunk.output.choices[0].message.content != "":
                        content_chunk = chunk.output.choices[0].message.content
                        
                        # 回调回复内容
                        if run_manager:
                            run_manager.on_llm_new_token(content_chunk)
                        
                        # 生成chunk
                        chunk_obj = ChatGenerationChunk(
                            message=AIMessageChunk(content=content_chunk)
                        )
                        yield chunk_obj
                
                end_time = time.time()
                log.info(f"流式调用完成，耗时: {end_time - start_time:.2f}秒")
                
            except Exception as e:
                log.error(f"流式调用异常: {str(e)}")
                raise 