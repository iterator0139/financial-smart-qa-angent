# financial-smart-qa-angent
天池LLM智能问答练习赛

## 数据集
数据集需要单独下载，下载地址: https://www.modelscope.cn/datasets/BJQW14B/bs_challenge_financial_14b_dataset/summary?spm=a2c22.12281978.0.0.5f974ea4t6khjz

下载后请将数据集文件夹 `bs_challenge_financial_14b_dataset` 放在项目根目录下。

## 环境配置

### 创建新的conda环境
conda env create --name smart-qa -f environment.yml

### 激活环境
conda activate smart-qa

### 依赖更新
conda env update --file environment.yml --prune
