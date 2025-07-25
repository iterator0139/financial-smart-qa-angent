from src.dao.db import MySQLClient
from typing import Dict, Any, Optional
from src.utils.logger import get_logger

log = get_logger()

def query_db(sql: str, params: Optional[Dict[str, Any]] = None):
    """
    执行数据库查询
    
    Args:
        sql: SQL查询语句
        params: 查询参数
        
    Returns:
        查询结果列表
    """
    log.info(f"[DEBUG] query_db: {sql}")
    log.info(f"[DEBUG] query_db: {params}")
    try:
        result = MySQLClient().execute_sql(sql, params)
        log.info(f"[DEBUG] query_db: {result}")
        return result
    except Exception as e:
        log.error(f"[DEBUG] query_db: {e}")
        return f"query_db: {str(e)}"


def check_db_info():
    log.info(f"[DEBUG] check_db_info")
    # 获取所有表名
    tables = MySQLClient().get_tables()
    table_info = {}
    # 获取每个表结构
    for table in tables:
        table_info[table] = MySQLClient().get_table_info(table)
    return table_info