#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库结构分析脚本
读取SQLite数据库文件，分析表结构和字段信息
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Dict, List, Any


class DatabaseSchemaAnalyzer:
    def __init__(self, db_path: str):
        """
        初始化数据库分析器
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = db_path
        self.connection = None
        
    def connect(self):
        """连接到数据库"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            print(f"成功连接到数据库: {self.db_path}")
        except Exception as e:
            print(f"连接数据库失败: {e}")
            raise
    
    def disconnect(self):
        """断开数据库连接"""
        if self.connection:
            self.connection.close()
            print("数据库连接已关闭")
    
    def get_table_list(self) -> List[str]:
        """获取所有表名"""
        cursor = self.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return tables
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """获取表的结构信息"""
        cursor = self.connection.cursor()
        
        # 获取表的基本信息
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        
        # 获取表的SQL创建语句
        cursor.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        create_sql = cursor.fetchone()
        
        # 获取表的行数
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        row_count = cursor.fetchone()[0]
        
        # 获取表的索引信息
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = cursor.fetchall()
        
        cursor.close()
        
        # 解析列信息
        columns = []
        for col in columns_info:
            column_info = {
                'name': col[1],
                'type': col[2],
                'not_null': bool(col[3]),
                'default_value': col[4],
                'primary_key': bool(col[5])
            }
            columns.append(column_info)
        
        return {
            'table_name': table_name,
            'columns': columns,
            'create_sql': create_sql[0] if create_sql else None,
            'row_count': row_count,
            'indexes': [idx[1] for idx in indexes]
        }
    
    def get_sample_data(self, table_name: str, limit: int = 5) -> List[tuple]:
        """获取表的样本数据"""
        cursor = self.connection.cursor()
        cursor.execute(f"SELECT * FROM {table_name} LIMIT {limit}")
        sample_data = cursor.fetchall()
        cursor.close()
        return sample_data
    
    def analyze_database(self) -> Dict[str, Any]:
        """分析整个数据库"""
        print("开始分析数据库结构...")
        
        tables = self.get_table_list()
        print(f"发现 {len(tables)} 个表: {tables}")
        
        database_info = {
            'database_path': self.db_path,
            'analysis_time': datetime.now().isoformat(),
            'total_tables': len(tables),
            'tables': {}
        }
        
        for table_name in tables:
            print(f"分析表: {table_name}")
            table_info = self.get_table_schema(table_name)
            
            # 获取样本数据
            try:
                sample_data = self.get_sample_data(table_name, 3)
                table_info['sample_data'] = sample_data
            except Exception as e:
                print(f"获取表 {table_name} 样本数据失败: {e}")
                table_info['sample_data'] = []
            
            database_info['tables'][table_name] = table_info
        
        return database_info
    
    def generate_markdown_report(self, database_info: Dict[str, Any], output_path: str):
        """生成Markdown格式的报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# 数据库结构分析报告\n\n")
            f.write(f"**数据库路径:** {database_info['database_path']}\n\n")
            f.write(f"**分析时间:** {database_info['analysis_time']}\n\n")
            f.write(f"**总表数:** {database_info['total_tables']}\n\n")
            
            f.write("## 表结构详情\n\n")
            
            for table_name, table_info in database_info['tables'].items():
                f.write(f"### 表名: {table_name}\n\n")
                f.write(f"**行数:** {table_info['row_count']}\n\n")
                f.write(f"**索引:** {', '.join(table_info['indexes']) if table_info['indexes'] else '无'}\n\n")
                
                f.write("#### 字段信息\n\n")
                f.write("| 字段名 | 数据类型 | 是否为空 | 默认值 | 主键 |\n")
                f.write("|--------|----------|----------|--------|------|\n")
                
                for col in table_info['columns']:
                    not_null = "否" if col['not_null'] else "是"
                    primary_key = "是" if col['primary_key'] else "否"
                    default_value = str(col['default_value']) if col['default_value'] is not None else "无"
                    
                    f.write(f"| {col['name']} | {col['type']} | {not_null} | {default_value} | {primary_key} |\n")
                
                f.write("\n#### 创建语句\n\n")
                f.write("```sql\n")
                f.write(table_info['create_sql'] if table_info['create_sql'] else "无")
                f.write("\n```\n\n")
                
                if table_info['sample_data']:
                    f.write("#### 样本数据\n\n")
                    f.write("```\n")
                    for row in table_info['sample_data']:
                        f.write(f"{row}\n")
                    f.write("```\n\n")
                
                f.write("---\n\n")
    
    def generate_json_report(self, database_info: Dict[str, Any], output_path: str):
        """生成JSON格式的报告"""
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(database_info, f, ensure_ascii=False, indent=2)


def main():
    """主函数"""
    # 数据库文件路径
    db_path = "dataset/bs_challenge_financial_14b_dataset/dataset/博金杯比赛数据.db"
    
    # 检查数据库文件是否存在
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        return
    
    # 创建输出目录
    output_dir = "dataset"
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建分析器实例
    analyzer = DatabaseSchemaAnalyzer(db_path)
    
    try:
        # 连接数据库
        analyzer.connect()
        
        # 分析数据库
        database_info = analyzer.analyze_database()
        
        # 生成报告
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Markdown报告
        md_output_path = os.path.join(output_dir, f"database_schema_report_{timestamp}.md")
        analyzer.generate_markdown_report(database_info, md_output_path)
        print(f"Markdown报告已生成: {md_output_path}")
        
        # JSON报告
        json_output_path = os.path.join(output_dir, f"database_schema_report_{timestamp}.json")
        analyzer.generate_json_report(database_info, json_output_path)
        print(f"JSON报告已生成: {json_output_path}")
        
        # 生成简化的表结构描述文件
        simple_output_path = os.path.join(output_dir, f"table_descriptions_{timestamp}.txt")
        with open(simple_output_path, 'w', encoding='utf-8') as f:
            f.write("数据库表结构描述\n")
            f.write("=" * 50 + "\n\n")
            
            for table_name, table_info in database_info['tables'].items():
                f.write(f"表名: {table_name}\n")
                f.write(f"描述: 包含 {table_info['row_count']} 行数据\n")
                f.write("字段列表:\n")
                
                for col in table_info['columns']:
                    f.write(f"  - {col['name']} ({col['type']})")
                    if col['primary_key']:
                        f.write(" [主键]")
                    if col['not_null']:
                        f.write(" [非空]")
                    f.write("\n")
                
                f.write("\n" + "-" * 30 + "\n\n")
        
        print(f"简化描述文件已生成: {simple_output_path}")
        
    except Exception as e:
        print(f"分析过程中出现错误: {e}")
    
    finally:
        # 断开连接
        analyzer.disconnect()


if __name__ == "__main__":
    main()