"""
SQL数据库信息向量化模块
用于将SQL库的基本信息向量化，作为agent的背景知识
"""

import sqlite3
import json
import pickle
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import numpy as np
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

# 导入embedding相关的库
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available, using fallback embedding")

from src.config.config_manager import ConfigManager
from src.utils.logger import get_logger


@dataclass
class TableSchema:
    """表结构信息"""
    table_name: str
    columns: List[Dict[str, str]]  # [{name, type, nullable, default}]
    indexes: List[str]
    constraints: List[str]
    sample_data: Dict[str, Any]
    business_description: str
    
    
@dataclass
class DatabaseContext:
    """数据库上下文信息"""
    db_path: str
    db_name: str
    tables: List[TableSchema]
    relationships: List[Dict[str, str]]
    business_summary: str
    created_at: str
    

class SQLContextExtractor:
    """SQL上下文提取器"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = get_logger(__name__)
        
    def extract_table_schema(self, table_name: str, conn: sqlite3.Connection) -> TableSchema:
        """提取单个表的schema信息"""
        try:
            # 获取表结构
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = []
            for col_info in cursor.fetchall():
                columns.append({
                    'name': col_info[1],
                    'type': col_info[2],
                    'nullable': 'YES' if col_info[3] == 0 else 'NO',
                    'default': col_info[4] if col_info[4] else None,
                    'primary_key': col_info[5] == 1
                })
            
            # 获取索引信息
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = [idx[1] for idx in cursor.fetchall()]
            
            # 获取约束信息
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            constraints = []
            for fk in cursor.fetchall():
                constraints.append(f"FOREIGN KEY({fk[3]}) REFERENCES {fk[2]}({fk[4]})")
            
            # 获取样本数据（前3行）
            cursor.execute(f"SELECT * FROM `{table_name}` LIMIT 3")
            sample_rows = cursor.fetchall()
            col_names = [desc[0] for desc in cursor.description]
            sample_data = {
                'columns': col_names,
                'rows': sample_rows
            }
            
            # 生成业务描述
            business_description = self._generate_business_description(table_name, columns, sample_data)
            
            return TableSchema(
                table_name=table_name,
                columns=columns,
                indexes=indexes,
                constraints=constraints,
                sample_data=sample_data,
                business_description=business_description
            )
            
        except Exception as e:
            self.logger.error(f"提取表 {table_name} 的schema时出错: {e}")
            return None
    
    def _generate_business_description(self, table_name: str, columns: List[Dict], sample_data: Dict) -> str:
        """生成表的业务描述"""
        descriptions = {
            '基金基本信息': '存储基金的基本信息，包括基金代码、名称、管理人、托管人、成立日期等核心信息',
            '基金股票持仓明细': '记录基金持有股票的详细信息，包括持仓数量、市值、占比等投资组合数据',
            '基金债券持仓明细': '记录基金持有债券的详细信息，包括债券类型、持仓数量、市值占比等',
            '基金可转债持仓明细': '记录基金持有可转债的详细信息，包括对应股票代码、持仓数量等',
            '基金日行情表': '记录基金每日的交易行情数据，包括单位净值、累计净值、资产净值等',
            'A股票日行情表': 'A股市场股票的日行情数据，包括开盘价、收盘价、最高价、最低价、成交量等',
            '港股票日行情表': '港股市场股票的日行情数据，包括开盘价、收盘价、最高价、最低价、成交量等',
            'A股公司行业划分表': 'A股公司的行业分类信息，包括行业划分标准、一级行业、二级行业等',
            '基金规模变动表': '记录基金规模的变动情况，包括申购、赎回、份额变化等信息',
            '基金份额持有人结构': '记录基金份额持有人的结构分布，包括机构投资者和个人投资者的占比'
        }
        
        base_desc = descriptions.get(table_name, f'{table_name}表的相关业务数据')
        
        # 添加字段信息
        key_fields = [col['name'] for col in columns[:5]]  # 前5个字段
        field_desc = f"主要字段包括: {', '.join(key_fields)}"
        
        return f"{base_desc}。{field_desc}。"
    
    def extract_database_context(self) -> DatabaseContext:
        """提取整个数据库的上下文信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 获取所有表名
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            table_names = [row[0] for row in cursor.fetchall()]
            
            self.logger.info(f"发现 {len(table_names)} 个表: {table_names}")
            
            # 提取每个表的schema
            tables = []
            for table_name in table_names:
                schema = self.extract_table_schema(table_name, conn)
                if schema:
                    tables.append(schema)
            
            # 分析表间关系
            relationships = self._analyze_relationships(tables)
            
            # 生成业务总结
            business_summary = self._generate_business_summary(tables)
            
            conn.close()
            
            return DatabaseContext(
                db_path=self.db_path,
                db_name=Path(self.db_path).stem,
                tables=tables,
                relationships=relationships,
                business_summary=business_summary,
                created_at=datetime.now().isoformat()
            )
            
        except Exception as e:
            self.logger.error(f"提取数据库上下文时出错: {e}")
            return None
    
    def _analyze_relationships(self, tables: List[TableSchema]) -> List[Dict[str, str]]:
        """分析表间关系"""
        relationships = []
        
        # 基于字段名推断关系
        field_mappings = {
            '基金代码': ['基金基本信息', '基金股票持仓明细', '基金债券持仓明细', '基金可转债持仓明细', '基金日行情表', '基金规模变动表', '基金份额持有人结构'],
            '股票代码': ['A股票日行情表', '港股票日行情表', 'A股公司行业划分表', '基金股票持仓明细'],
            '交易日': ['A股票日行情表', '港股票日行情表'],
            '交易日期': ['A股公司行业划分表']
        }
        
        for field, related_tables in field_mappings.items():
            if len(related_tables) > 1:
                for i in range(len(related_tables)):
                    for j in range(i + 1, len(related_tables)):
                        relationships.append({
                            'type': 'FOREIGN_KEY',
                            'from_table': related_tables[i],
                            'to_table': related_tables[j],
                            'field': field,
                            'description': f'{related_tables[i]}和{related_tables[j]}通过{field}关联'
                        })
        
        return relationships
    
    def _generate_business_summary(self, tables: List[TableSchema]) -> str:
        """生成业务总结"""
        summary = f"""
这是一个金融数据库，包含{len(tables)}个核心表，涵盖基金、股票、债券等金融产品的完整信息。

数据库主要包含以下业务域：
1. 基金管理：基金基本信息、持仓明细、规模变动、份额持有人结构
2. 股票市场：A股和港股的日行情数据、行业分类信息
3. 债券投资：债券和可转债的持仓明细

核心表关系：
- 基金代码是连接基金相关表的主键
- 股票代码连接股票相关表
- 交易日期用于时间序列数据关联

这个数据库支持金融投资分析、基金管理、市场行情查询等业务场景。
        """.strip()
        
        return summary


class SQLContextVectorizer:
    """SQL上下文向量化器"""
    
    def __init__(self, config_manager: ConfigManager = None):
        self.config_manager = config_manager or ConfigManager()
        self.logger = get_logger(__name__)
        self.embedding_model = None
        self._init_embedding_model()
    
    def _init_embedding_model(self):
        """初始化embedding模型"""
        try:
            if SENTENCE_TRANSFORMERS_AVAILABLE:
                # 使用sentence-transformers
                model_name = self.config_manager.get('embedding.model_name', 'all-MiniLM-L6-v2')
                self.embedding_model = SentenceTransformer(model_name)
                self.logger.info(f"使用sentence-transformers模型: {model_name}")
            else:
                # 使用简单的fallback方案
                self.logger.warning("sentence-transformers不可用，使用简单的fallback embedding")
                self.embedding_model = None
        except Exception as e:
            self.logger.error(f"初始化embedding模型失败: {e}")
            self.embedding_model = None
    
    def _simple_embedding(self, text: str) -> np.ndarray:
        """简单的文本向量化（fallback方案）"""
        # 简单的词频向量化
        words = text.lower().split()
        vocab = list(set(words))
        vector = np.zeros(len(vocab))
        for i, word in enumerate(vocab):
            vector[i] = words.count(word)
        
        # 归一化
        if np.linalg.norm(vector) > 0:
            vector = vector / np.linalg.norm(vector)
        
        return vector
    
    def generate_context_text(self, db_context: DatabaseContext) -> str:
        """生成完整的SQL上下文文本"""
        context_parts = []
        
        # 数据库概览
        context_parts.append(f"数据库名称: {db_context.db_name}")
        context_parts.append(f"数据库路径: {db_context.db_path}")
        context_parts.append(f"创建时间: {db_context.created_at}")
        context_parts.append(f"包含表数量: {len(db_context.tables)}")
        context_parts.append("")
        
        # 业务总结
        context_parts.append("业务总结:")
        context_parts.append(db_context.business_summary)
        context_parts.append("")
        
        # 表间关系
        if db_context.relationships:
            context_parts.append("表间关系:")
            for rel in db_context.relationships:
                context_parts.append(f"- {rel['description']}")
            context_parts.append("")
        
        # 各表详细信息
        context_parts.append("表详细信息:")
        for table in db_context.tables:
            context_parts.append(f"\n表名: {table.table_name}")
            context_parts.append(f"业务描述: {table.business_description}")
            
            # 字段信息
            context_parts.append("字段信息:")
            for col in table.columns:
                pk_flag = " (主键)" if col.get('primary_key') else ""
                nullable = "可空" if col['nullable'] == 'YES' else "不可空"
                context_parts.append(f"  - {col['name']}: {col['type']}, {nullable}{pk_flag}")
            
            # 索引信息
            if table.indexes:
                context_parts.append(f"索引: {', '.join(table.indexes)}")
            
            # 约束信息
            if table.constraints:
                context_parts.append("约束:")
                for constraint in table.constraints:
                    context_parts.append(f"  - {constraint}")
            
            # 样本数据
            if table.sample_data and table.sample_data['rows']:
                context_parts.append("样本数据:")
                cols = table.sample_data['columns'][:5]  # 只显示前5列
                context_parts.append(f"  列名: {', '.join(cols)}")
                for i, row in enumerate(table.sample_data['rows'][:2]):  # 只显示前2行
                    row_data = [str(row[j]) if j < len(row) else 'NULL' for j in range(len(cols))]
                    context_parts.append(f"  样本{i+1}: {', '.join(row_data)}")
            
            context_parts.append("")
        
        return "\n".join(context_parts)
    
    def vectorize_context(self, context_text: str) -> np.ndarray:
        """向量化上下文文本"""
        try:
            if self.embedding_model and SENTENCE_TRANSFORMERS_AVAILABLE:
                # 使用sentence-transformers
                embedding = self.embedding_model.encode(context_text)
                return embedding
            else:
                # 使用简单的fallback方案
                return self._simple_embedding(context_text)
        except Exception as e:
            self.logger.error(f"向量化上下文时出错: {e}")
            return self._simple_embedding(context_text)
    
    def save_context_and_embedding(self, db_context: DatabaseContext, context_text: str, 
                                 embedding: np.ndarray, output_dir: str = "data/sql_context"):
        """保存上下文和向量化结果"""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # 保存原始上下文
        context_file = output_path / f"{db_context.db_name}_context.json"
        with open(context_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(db_context), f, ensure_ascii=False, indent=2)
        
        # 保存上下文文本
        text_file = output_path / f"{db_context.db_name}_context.txt"
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(context_text)
        
        # 保存向量
        vector_file = output_path / f"{db_context.db_name}_embedding.pkl"
        with open(vector_file, 'wb') as f:
            pickle.dump(embedding, f)
        
        self.logger.info(f"上下文和向量已保存到: {output_path}")
        
        return {
            'context_file': str(context_file),
            'text_file': str(text_file),
            'vector_file': str(vector_file)
        }


class SQLContextRetriever:
    """SQL上下文检索器"""
    
    def __init__(self, context_dir: str = "data/sql_context"):
        self.context_dir = Path(context_dir)
        self.logger = get_logger(__name__)
        self.contexts = {}
        self.embeddings = {}
        self.load_contexts()
    
    def load_contexts(self):
        """加载所有上下文"""
        if not self.context_dir.exists():
            self.logger.warning(f"上下文目录不存在: {self.context_dir}")
            return
        
        for context_file in self.context_dir.glob("*_context.json"):
            try:
                db_name = context_file.stem.replace('_context', '')
                
                # 加载上下文
                with open(context_file, 'r', encoding='utf-8') as f:
                    context_data = json.load(f)
                    self.contexts[db_name] = context_data
                
                # 加载向量
                vector_file = self.context_dir / f"{db_name}_embedding.pkl"
                if vector_file.exists():
                    with open(vector_file, 'rb') as f:
                        self.embeddings[db_name] = pickle.load(f)
                
                self.logger.info(f"加载上下文: {db_name}")
                
            except Exception as e:
                self.logger.error(f"加载上下文文件 {context_file} 时出错: {e}")
    
    def get_context(self, db_name: str) -> Optional[Dict]:
        """获取指定数据库的上下文"""
        return self.contexts.get(db_name)
    
    def get_context_text(self, db_name: str) -> Optional[str]:
        """获取指定数据库的上下文文本"""
        text_file = self.context_dir / f"{db_name}_context.txt"
        if text_file.exists():
            with open(text_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def get_embedding(self, db_name: str) -> Optional[np.ndarray]:
        """获取指定数据库的向量"""
        return self.embeddings.get(db_name)
    
    def list_available_contexts(self) -> List[str]:
        """列出所有可用的上下文"""
        return list(self.contexts.keys())


def create_sql_context_task(db_path: str, output_dir: str = "data/sql_context", 
                          config_manager: ConfigManager = None) -> Dict[str, Any]:
    """
    创建SQL上下文向量化任务
    
    Args:
        db_path: 数据库文件路径
        output_dir: 输出目录
        config_manager: 配置管理器
    
    Returns:
        任务结果字典
    """
    try:
        logger = get_logger(__name__)
        logger.info(f"开始SQL上下文向量化任务: {db_path}")
        
        # 1. 提取数据库上下文
        extractor = SQLContextExtractor(db_path)
        db_context = extractor.extract_database_context()
        
        if not db_context:
            raise Exception("提取数据库上下文失败")
        
        # 2. 向量化上下文
        vectorizer = SQLContextVectorizer(config_manager)
        context_text = vectorizer.generate_context_text(db_context)
        embedding = vectorizer.vectorize_context(context_text)
        
        # 3. 保存结果
        files = vectorizer.save_context_and_embedding(
            db_context, context_text, embedding, output_dir
        )
        
        logger.info("SQL上下文向量化任务完成")
        
        return {
            'success': True,
            'db_name': db_context.db_name,
            'tables_count': len(db_context.tables),
            'context_length': len(context_text),
            'embedding_shape': embedding.shape,
            'files': files
        }
        
    except Exception as e:
        logger.error(f"SQL上下文向量化任务失败: {e}")
        return {
            'success': False,
            'error': str(e)
        }


if __name__ == "__main__":
    # 示例用法
    from src.config.config_manager import ConfigManager
    
    # 初始化配置
    config_manager = ConfigManager()
    project_root = Path(__file__).resolve().parent.parent.parent
    config_manager.init(project_root / "src" / "conf")
    
    # 执行向量化任务
    db_path = "bs_challenge_financial_14b_dataset/dataset/博金杯比赛数据.db"
    result = create_sql_context_task(db_path, config_manager=config_manager)
    
    print("任务结果:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
    # 测试检索
    if result['success']:
        retriever = SQLContextRetriever()
        contexts = retriever.list_available_contexts()
        print(f"\n可用上下文: {contexts}")
        
        if contexts:
            context_text = retriever.get_context_text(contexts[0])
            print(f"\n上下文文本长度: {len(context_text) if context_text else 0}")
