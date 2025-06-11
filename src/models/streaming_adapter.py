"""
Streaming LLM Adapter for LangChain

提供一个同时支持流式和非流式输出的LangChain适配器。
可以根据模型名称自动判断是否使用流式API并最终返回完整结果。
"""

from typing import Any, Dict, List, Optional, Union, Iterator, Callable
import time
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    FunctionMessage,
    HumanMessage
)
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
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
    """
    
    model_version: str = "qwen-turbo"
    streaming_models: List[str] = STREAMING_MODELS
    stream_enabled: bool = True
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    default_params: Dict[str, Any] = {}
    
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
            else:
                dashscope_messages.append({
                    "role": "user",  # 默认角色
                    "content": str(message.content)
                })
        
        return dashscope_messages
    
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
                
                # 构建AIMessage
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
                    
                    # 如果有回调并且需要展示思考过程，可以在此处添加回调
                    # 例如: run_manager.on_llm_new_token("[思考] " + reasoning_chunk)
                
                # 处理回复内容
                if chunk.output.choices[0].message.content != "":
                    content_chunk = chunk.output.choices[0].message.content
                    answer_content += content_chunk
                    
                    # 回调传递token，用于UI流式展示
                    if run_manager:
                        run_manager.on_llm_new_token(content_chunk)
            
            end_time = time.time()
            log.info(f"流式输出完成，耗时: {end_time - start_time:.2f}秒")
            
            # 构建最终消息
            message = AIMessage(content=answer_content)
            
            # 如果有思考过程，可以添加到message的metadata
            if reasoning_content:
                message.additional_kwargs["reasoning"] = reasoning_content
            
            return ChatResult(generations=[{"message": message}])
                
        except Exception as e:
            log.error(f"流式输出异常: {str(e)}")
            raise
    
    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs
    ) -> Iterator[ChatGenerationChunk]:
        """
        LangChain流式回调接口实现
        
        注意: 此方法返回迭代器用于LangChain框架内部流式处理，
        但在我们的实现中依然会收集完整结果。这保证了完全兼容LangChain API。
        
        Args:
            messages: 输入消息列表
            stop: 停止序列
            run_manager: 回调管理器
            **kwargs: 其他参数
            
        Yields:
            ChatGenerationChunk对象
        """
        result = self._generate(messages, stop, run_manager, **kwargs)
        yield ChatGenerationChunk(
            message=result.generations[0]["message"],
            generation_info=result.generations[0].get("generation_info", {})
        ) 