#!/usr/bin/env python3
"""
SQL数据库信息向量化离线任务脚本
用于将SQL库的基本信息向量化，作为agent的背景知识
"""

import sys
import argparse
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from src.config.config_manager import ConfigManager
from src.embedding.sql_context import create_sql_context_task, SQLContextRetriever
from src.utils.logger import get_logger


def main():
    parser = argparse.ArgumentParser(description='SQL数据库信息向量化离线任务')
    parser.add_argument('--db-path', '-d', 
                        default='bs_challenge_financial_14b_dataset/dataset/博金杯比赛数据.db',
                        help='数据库文件路径')
    parser.add_argument('--output-dir', '-o', 
                        default='data/sql_context',
                        help='输出目录')
    parser.add_argument('--config-dir', '-c',
                        default='src/conf',
                        help='配置文件目录')
    parser.add_argument('--list', '-l', action='store_true',
                        help='列出所有可用的上下文')
    parser.add_argument('--show-context', '-s',
                        help='显示指定数据库的上下文文本')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    logger = get_logger(__name__)
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # 如果是列出模式
    if args.list:
        retriever = SQLContextRetriever(args.output_dir)
        contexts = retriever.list_available_contexts()
        if contexts:
            print("可用的SQL上下文:")
            for ctx in contexts:
                print(f"  - {ctx}")
        else:
            print("没有找到可用的SQL上下文")
        return
    
    # 如果是显示上下文模式
    if args.show_context:
        retriever = SQLContextRetriever(args.output_dir)
        context_text = retriever.get_context_text(args.show_context)
        if context_text:
            print(f"数据库 '{args.show_context}' 的上下文:")
            print("=" * 80)
            print(context_text)
        else:
            print(f"未找到数据库 '{args.show_context}' 的上下文")
        return
    
    # 检查数据库文件是否存在
    db_path = Path(args.db_path)
    if not db_path.exists():
        logger.error(f"数据库文件不存在: {db_path}")
        sys.exit(1)
    
    # 初始化配置管理器
    config_manager = ConfigManager()
    config_dir = Path(args.config_dir)
    if config_dir.exists():
        config_manager.init(config_dir)
        logger.info(f"配置加载完成: {config_dir}")
    else:
        logger.warning(f"配置目录不存在: {config_dir}，使用默认配置")
    
    # 执行向量化任务
    logger.info(f"开始SQL上下文向量化任务")
    logger.info(f"数据库路径: {db_path}")
    logger.info(f"输出目录: {args.output_dir}")
    
    result = create_sql_context_task(
        db_path=str(db_path),
        output_dir=args.output_dir,
        config_manager=config_manager
    )
    
    # 输出结果
    if result['success']:
        print("✅ SQL上下文向量化任务完成")
        print(f"📊 处理统计:")
        print(f"  - 数据库名称: {result['db_name']}")
        print(f"  - 表数量: {result['tables_count']}")
        print(f"  - 上下文长度: {result['context_length']} 字符")
        print(f"  - 向量维度: {result['embedding_shape']}")
        print(f"📁 生成文件:")
        for key, path in result['files'].items():
            print(f"  - {key}: {path}")
        
        # 验证检索功能
        print(f"\n🔍 验证检索功能:")
        retriever = SQLContextRetriever(args.output_dir)
        contexts = retriever.list_available_contexts()
        print(f"  - 可用上下文: {contexts}")
        
        if contexts:
            context_text = retriever.get_context_text(contexts[0])
            embedding = retriever.get_embedding(contexts[0])
            print(f"  - 上下文文本长度: {len(context_text) if context_text else 0}")
            print(f"  - 向量形状: {embedding.shape if embedding is not None else 'None'}")
        
        print(f"\n💡 使用建议:")
        print(f"  - 查看上下文: python {__file__} --show-context {result['db_name']}")
        print(f"  - 列出所有上下文: python {__file__} --list")
        
    else:
        print("❌ SQL上下文向量化任务失败")
        print(f"错误信息: {result.get('error', '未知错误')}")
        sys.exit(1)


if __name__ == "__main__":
    main() 