from src.prompts import WORD_SEGMENTATION_PROMPT, ENTITY_EXTRACTION_PROMPT, QUERY_UNDERSTANDING_PROMPT
from src.utils.logger import get_logger
from langchain_core.prompts import ChatPromptTemplate
from src.models.streaming_adapter import STREAMING_MODELS, StreamingLLMAdapter

class QuModel:
    def __init__(self, state, node_name):
        self.log = get_logger()
        self.state = state
        self.node_name = node_name
        self.model = self.get_model_by_node_name(node_name)
        self.prompt = self.get_prompt_by_node_name(node_name)
        self.template_variables = self.get_template_variables_by_node_name(node_name)
        self.qwen_llm = StreamingLLMAdapter(
            model=self.model,
            api_key=self.state["config"].get("api.qwen.api_key"),
            base_url=self.state["config"].get("api.qwen.base_url", ""),
            streaming_models=self.state["config"].get("api.qwen.streaming_models", STREAMING_MODELS),
            stream_enabled=self.state["config"].get("api.qwen.stream_enabled", True),
            **self.state["config"].get("api.qwen.default_params", {})
        )
    
    def get_model_by_node_name(self, node_name) -> str:
        if node_name == "word_segmentation":
            return self.state.get("segment_model")
        elif node_name == "ner":
            return self.state.get("ner_model")
        elif node_name == "intent":
            return self.state.get("intent_model")
        else:
            return None
    
    def get_prompt_by_node_name(self, node_name) -> str:
        if node_name == "word_segmentation":
            return WORD_SEGMENTATION_PROMPT
        elif node_name == "ner":
            return ENTITY_EXTRACTION_PROMPT
        elif node_name == "intent":
            return QUERY_UNDERSTANDING_PROMPT
        else:
            return None
    
    def get_template_variables_by_node_name(self, node_name) -> dict:
        if node_name == "word_segmentation":
            return {"INPUT_TEXT": self.state.get("query")}
        elif node_name == "ner":
            return {"INPUT_TEXT": self.state.get("query")}
        elif node_name == "intent":
            return {"INPUT_TEXT": self.state.get("query")}
        else:
            return None

    def call_llm_by_aliyun_api(self) -> dict:
        # 使用 Jinja2 风格的模板语法
        prompt = ChatPromptTemplate.from_template(
            self.prompt,
            template_format="jinja2"
        )
        # 创建链
        chain = prompt | self.qwen_llm
        
        # 查看拼接后的prompt
        formatted_messages = prompt.format_messages(**self.template_variables)
        self.log.info(f"{self.node_name} prompt内容:")
        for message in formatted_messages:
            self.log.info(f"Role: {message.type}, Content: {message.content}")
        
        # 调用模型
        try:
            result = chain.invoke(self.template_variables)
            
            # 检查是否有思考过程
            reasoning = None
            if hasattr(result, 'additional_kwargs') and 'reasoning' in result.additional_kwargs:
                reasoning = result.additional_kwargs['reasoning']
                self.log.info(f"{self.node_name}思考过程: {reasoning}")
            
            self.log.info(f"{self.node_name} 完成，结果长度: {len(result.content)}, 结果: {result.content}")
            
            # 返回结果，包括思考过程（如果有）
            result_dict = {"final_output": result.content}
            if reasoning:
                result_dict["final_reasoning"] = reasoning
                
            return result_dict
        except Exception as e:
            self.log.error(f"{self.node_name}失败: {str(e)}")
            raise