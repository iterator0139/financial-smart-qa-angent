from modelscope import AutoModelForCausalLM, AutoTokenizer, snapshot_download
from modelscope import GenerationConfig
from transformers import TextStreamer

model_dir = snapshot_download('TongyiFinance/Tongyi-Finance-14B')
print(f"Model directory: {model_dir}")

# Note: The default behavior now has injection attack prevention off.
tokenizer = AutoTokenizer.from_pretrained(model_dir, trust_remote_code=True)
print("tokenizer loaded")
# use bf16
# model = AutoModelForCausalLM.from_pretrained(model_dir, device_map="cuda:0", trust_remote_code=True, bf16=True).eval()
# use cpu only
print("start load model")
model = AutoModelForCausalLM.from_pretrained(model_dir, device_map="cpu", trust_remote_code=True).eval()
print("model loaded")
# model = AutoModelForCausalLM.from_pretrained(model_dir, device_map="cuda:0", trust_remote_code=True).eval()
# 模型加载指定device_map='cuda:0'，更改成device_map='auto'会使用所有可用显卡

# Specify hyperparameters for generation
model.generation_config = GenerationConfig.from_pretrained(model_dir, trust_remote_code=True)
print(f"Generation config: {model.generation_config}")

inputs = tokenizer('市盈率是最常用来评估股价水平是否合理的指标之一，是指', return_tensors='pt')
inputs = inputs.to(model.device)

streamer = TextStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

print("start generate")
pred = model.generate(**inputs, streamer=streamer)
# print(tokenizer.decode(pred.cpu()[0], skip_special_tokens=True))
# 市盈率是最常用来评估股价水平是否合理的指标之一，是指股票价格与每股盈利的比率。

# llm_pipeline = pipeline('text-generation', model=model, tokenizer=tokenizer)
# llm = HuggingFacePipeline(pipeline=llm_pipeline)

# llm.invoke('市盈率是最常用来评估股价水平是否合理的指标之一，是指')