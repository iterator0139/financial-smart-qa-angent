import dashscope
from typing import Any, Dict, Optional
from .base import BaseModel
from src.config.config_manager import ConfigManager
from src.utils.logger import get_logger

stream_model_version = ['qwq-32b', 'qwq-plus', "qwq-plus-latest"]

class QWENModel(BaseModel):
    """Implementation for QWEN API calls using DashScope"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.log = get_logger()
        self.log.info("初始化 QWENModel")
        
        # Set API key for dashscope
        dashscope.api_key = config.get('api_key')
        self.model_version = config.get('model_version', 'qwen-turbo')
        self.default_params = config.get('default_params', {})
        
        self.log.debug(f"使用模型版本: {self.model_version}")
        self.log.debug(f"默认参数: {self.default_params}")
        if not dashscope.api_key:
            self.log.error("缺少API密钥，无法初始化QWEN模型")
            raise ValueError("API key is required for QWEN model")

    def generateDistributor(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Distribute the generation task to the model
        """
        if self.model_version in stream_model_version:
            return self.stream_generate(prompt, **kwargs)
        else:
            return self.generate(prompt, **kwargs)
        
    def generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Generate response using QWEN API via DashScope
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters like temperature, top_p, etc.
            
        Returns:
            Dict containing the response and metadata
        """
        try:
            self.log.info(f"生成响应，提示长度: {len(prompt)}")
            self.log.debug(f"生成参数: {kwargs}")
            
            messages = [{'role': 'user', 'content': prompt}]
            
            response = dashscope.Generation.call(
                model=self.model_version,
                messages=messages,
                result_format='message',  # or 'text'
                **kwargs  # Additional parameters like temperature, top_p
            )
            self.log.debug(f"调用完成: {response}")
            if response.status_code == 200:
                content = response.output.choices[0].message.content
                self.log.info(f"生成成功，响应长度: {len(content)}")
                self.log.debug(f"使用令牌: {response.usage}")
                
                return {
                    'success': True,
                    'response': content,
                    'raw_response': response,
                    'status_code': response.status_code,
                    'usage': response.usage
                }
            else:
                self.log.warning(f"生成失败，状态码: {response.status_code}, 错误: {response.message}")
                return {
                    'success': False,
                    'error': response.message,
                    'status_code': response.status_code
                }
                
        except Exception as e:
            self.log.error(f"生成过程中发生异常: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status_code': None
            }

    def stream_generate(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """
        Stream response using QWEN API via DashScope
        
        Args:
            prompt: Input prompt
            **kwargs: Additional parameters like temperature, top_p, etc.
            
        Returns:
            Generator of response chunks
        """
        
        try:
            # 定义完整思考过程
            reasoning_content = ""
            # 定义完整回复
            answer_content = ""
            # 判断是否结束思考过程并开始回复
            is_answering = False
            self.log.info(f"生成响应，提示长度: {len(prompt)}")
            self.log.debug(f"生成参数: {kwargs}")

            messages = [{'role': 'user', 'content': prompt}]

            response = dashscope.Generation.call(
                model=self.model_version,
                messages=messages,
                stream=True,
                **kwargs
            )
            
            for chunk in response:
                # 如果思考过程与回复皆为空，则忽略
                if (chunk.output.choices[0].message.content == "" and 
                    chunk.output.choices[0].message.reasoning_content == ""):
                    pass
                else:
                    # 如果当前为思考过程
                    if (chunk.output.choices[0].message.reasoning_content != "" and 
                        chunk.output.choices[0].message.content == ""):
                        reasoning_content += chunk.output.choices[0].message.reasoning_content
                    # 如果当前为回复
                    elif chunk.output.choices[0].message.content != "":
                        if not is_answering:
                            is_answering = True
                        answer_content += chunk.output.choices[0].message.content
            self.log.info("reasoning: " + reasoning_content)    
            self.log.info("response: " + answer_content)
       
            return {
                'success': True,
                'response': answer_content,
                'reasoning': reasoning_content,
                'status_code': 200
            }
        except Exception as e:
            self.log.error(f"生成过程中发生异常: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'status_code': None
            }