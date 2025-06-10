from langchain_openai import ChatOpenAI
from src.prompts import qu_prompt
from vllm import VLLMClient
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig, TextStreamer
from modelscope import AutoModelForCausalLM, AutoTokenizer, snapshot_download
from ollama import OllamaClient

class QuModel:
    def __init__(self):
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        self.prompt = qu_prompt.PROMPT_QUERY_UNDERSTANDING

    def call_llm(self, query: str) -> str:
        prompt = self.prompt.format(input_data=query)
        return self.llm.invoke(prompt).content


    # use local vllm server model， localhost:11434
    def call_llm_by_vllm(self, query: str) -> list[str]:
        # use vllm server model
        vllm_client = VLLMClient(host="localhost", port=11434)
        vllm_client.generate(query)
        return vllm_client.generate(query)



    def call_llm_by_huggingface(self, query: str) -> list[str]:
        model_dir = snapshot_download('TongyiFinance/Tongyi-Finance-14B')
        tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(model_dir, device_map="cpu", trust_remote_code=True).eval()
        model.generation_config = GenerationConfig.from_pretrained(model_dir, trust_remote_code=True)
        inputs = tokenizer(query, return_tensors='pt')
        inputs = inputs.to(model.device)
        streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)
        pred = model.generate(**inputs, streamer=streamer)
        return tokenizer.decode(pred.cpu()[0], skip_special_tokens=True).split("\n")

    def call_llm_by_ollama(self, query: str) -> list[str]:
        # use ollama model
        ollama_client = OllamaClient(host="http://localhost:11434")
        ollama_client.generate(query)
        return ollama_client.generate(query)    