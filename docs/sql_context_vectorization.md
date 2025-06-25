# SQL上下文向量化模块

## 概述

SQL上下文向量化模块是一个离线数据处理任务，用于将SQL数据库的基本信息向量化，作为AI agent的背景知识。该模块将数据库的表结构、字段信息、业务描述、表间关系等信息提取并向量化，以便在生成SQL查询时为agent提供全局视角的数据库理解。

## 设计理念

### 为什么不分chunk？

根据实际应用场景，我们选择将整个数据库的结构信息作为一个完整的上下文进行向量化，而不是分成多个chunk。这样设计的原因是：

1. **全局视角**：数据库结构信息相对紧凑，保持完整性可以让agent理解表间关系
2. **业务连贯性**：金融数据库的表间关系密切，分chunk可能割裂业务逻辑
3. **检索效率**：单一向量检索比多向量聚合更高效
4. **上下文一致性**：避免因分chunk导致的信息碎片化

## 功能特性

- 🔍 **智能表结构提取**：自动提取表结构、字段类型、索引、约束等信息
- 📊 **样本数据采集**：获取每个表的样本数据，帮助理解数据特征
- 🔗 **关系分析**：基于字段名智能推断表间关系
- 📝 **业务描述生成**：为每个表生成业务层面的描述
- 🎯 **向量化存储**：使用sentence-transformers进行高质量向量化
- 🔄 **检索接口**：提供便捷的上下文检索功能

## 架构设计

```
SQL上下文向量化模块
├── SQLContextExtractor     # 数据库信息提取器
├── SQLContextVectorizer    # 向量化处理器
├── SQLContextRetriever     # 上下文检索器
└── create_sql_context_task # 主任务函数
```

### 核心组件

#### 1. SQLContextExtractor
- 连接SQLite数据库
- 提取表结构信息（字段、类型、约束等）
- 获取样本数据
- 分析表间关系
- 生成业务描述

#### 2. SQLContextVectorizer
- 将提取的信息组织成结构化文本
- 使用sentence-transformers进行向量化
- 支持fallback方案（简单词频向量化）
- 保存向量化结果

#### 3. SQLContextRetriever
- 加载已向量化的上下文
- 提供多种检索接口
- 支持向量相似度搜索

## 使用方法

### 1. 直接运行脚本

```bash
# 使用默认配置向量化数据库
python scripts/create_sql_context.py

# 指定数据库路径和输出目录
python scripts/create_sql_context.py \
  --db-path "path/to/your/database.db" \
  --output-dir "data/sql_context" \
  --verbose

# 列出所有可用的上下文
python scripts/create_sql_context.py --list

# 查看特定数据库的上下文
python scripts/create_sql_context.py --show-context "数据库名称"
```

### 2. 程序化调用

```python
from src.config.config_manager import ConfigManager
from src.embedding.sql_context import create_sql_context_task, SQLContextRetriever

# 初始化配置
config_manager = ConfigManager()
config_manager.init(Path("src/conf"))

# 执行向量化任务
result = create_sql_context_task(
    db_path="path/to/database.db",
    output_dir="data/sql_context",
    config_manager=config_manager
)

# 使用检索器
retriever = SQLContextRetriever("data/sql_context")
context_text = retriever.get_context_text("数据库名称")
embedding = retriever.get_embedding("数据库名称")
```

### 3. 在Agent中使用

```python
from src.embedding.sql_context import SQLContextRetriever

class SQLAgent:
    def __init__(self):
        self.context_retriever = SQLContextRetriever()
    
    def get_database_context(self, db_name: str) -> str:
        """获取数据库的背景知识"""
        return self.context_retriever.get_context_text(db_name)
    
    def generate_sql(self, query: str, db_name: str):
        # 获取数据库上下文
        db_context = self.get_database_context(db_name)
        
        # 结合上下文生成SQL
        prompt = f"""
        数据库上下文:
        {db_context}
        
        用户查询: {query}
        请生成相应的SQL查询。
        """
        # ... 调用LLM生成SQL
```

## 配置说明

在`src/conf/config.yaml`中添加embedding相关配置：

```yaml
embedding:
  model_name: 'all-MiniLM-L6-v2'  # sentence-transformers模型
  cache_dir: '.cache/sentence_transformers'  # 模型缓存目录
  batch_size: 32  # 批处理大小
  max_length: 512  # 最大文本长度
```

## 生成的文件结构

```
data/sql_context/
├── 数据库名称_context.json     # 原始结构化上下文
├── 数据库名称_context.txt      # 格式化的文本上下文
└── 数据库名称_embedding.pkl    # 向量化结果
```

### 上下文文本格式

生成的上下文文本包含以下信息：

1. **数据库概览**：名称、路径、创建时间、表数量
2. **业务总结**：整体业务领域和应用场景描述
3. **表间关系**：基于字段名推断的表间关联关系
4. **表详细信息**：
   - 表名和业务描述
   - 字段信息（名称、类型、可空性、主键等）
   - 索引信息
   - 约束信息
   - 样本数据

## 示例输出

```
数据库名称: 博金杯比赛数据
数据库路径: bs_challenge_financial_14b_dataset/dataset/博金杯比赛数据.db
创建时间: 2025-06-25T18:59:00.583930
包含表数量: 10

业务总结:
这是一个金融数据库，包含10个核心表，涵盖基金、股票、债券等金融产品的完整信息。

数据库主要包含以下业务域：
1. 基金管理：基金基本信息、持仓明细、规模变动、份额持有人结构
2. 股票市场：A股和港股的日行情数据、行业分类信息
3. 债券投资：债券和可转债的持仓明细

表详细信息:

表名: 基金基本信息
业务描述: 存储基金的基本信息，包括基金代码、名称、管理人、托管人、成立日期等核心信息
字段信息:
  - 基金代码: TEXT, 可空
  - 基金全称: TEXT, 可空
  - 基金简称: TEXT, 可空
  ...
```

## 扩展和定制

### 1. 添加新的数据库类型支持
在`SQLContextExtractor`中扩展`_generate_business_description`方法，添加新的表名到业务描述的映射。

### 2. 自定义向量化模型
修改配置文件中的`embedding.model_name`来使用不同的sentence-transformers模型。

### 3. 扩展关系分析
在`_analyze_relationships`方法中添加更复杂的表关系推断逻辑。

## 性能优化

1. **模型缓存**：sentence-transformers模型会自动缓存到本地
2. **批处理**：支持批量处理多个文本（虽然当前场景为单一上下文）
3. **内存管理**：大型数据库可以考虑分批处理表信息

## 故障排除

### 常见问题

1. **sentence-transformers安装失败**
   ```bash
   pip install sentence-transformers
   ```

2. **数据库文件路径错误**
   - 检查数据库文件是否存在
   - 确认路径格式正确

3. **向量化失败**
   - 系统会自动回退到简单的词频向量化方案
   - 检查网络连接（首次下载模型需要网络）

4. **内存不足**
   - 减少`batch_size`配置
   - 考虑使用更小的embedding模型

## 未来改进

1. **支持更多数据库类型**：PostgreSQL、MySQL等
2. **增量更新**：支持数据库结构变化时的增量更新
3. **多语言支持**：支持中英文混合的更好向量化
4. **向量相似度搜索**：支持基于查询的相似表检索
5. **可视化工具**：提供数据库结构的可视化界面

## 贡献指南

欢迎提交Issue和Pull Request来改进这个模块。主要改进方向：

- 更精确的业务描述生成
- 更智能的表关系推断
- 更高效的向量化策略
- 更丰富的检索功能 