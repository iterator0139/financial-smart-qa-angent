import pymysql
from typing import List, Dict, Any, Optional, Type, TypeVar
from contextlib import contextmanager
import threading
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, Boolean, Float, MetaData, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
from src.config import ConfigManager
from src.utils.logger import get_logger

log = get_logger()

# 创建基础模型类
Base = declarative_base()

# 泛型类型变量
T = TypeVar('T', bound=Base)


class MySQLClient:
    """MySQL数据库客户端，使用ORM进行查询"""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化MySQL客户端（单例模式）"""
        if not hasattr(self, '_initialized'):
            self.config_manager = ConfigManager()
            self.engine = None
            self.Session = None
            self._init_connection()
            self._initialized = True
    
    def _init_connection(self):
        """初始化数据库连接"""
        try:
            # 从配置管理器获取数据库配置
            db_config = {
                'host': self.config_manager.get('database.mysql.host', 'localhost'),
                'port': self.config_manager.get_int('database.mysql.port', 3306),
                'user': self.config_manager.get('database.mysql.user', 'root'),
                'password': self.config_manager.get('database.mysql.password', 'password'),
                'database': self.config_manager.get('database.mysql.database', 'financial_db'),
                'charset': self.config_manager.get('database.mysql.charset', 'utf8mb4'),
                'pool_size': self.config_manager.get_int('database.mysql.pool_size', 10),
                'max_overflow': self.config_manager.get_int('database.mysql.max_overflow', 20),
                'pool_timeout': self.config_manager.get_int('database.mysql.pool_timeout', 30),
                'pool_recycle': self.config_manager.get_int('database.mysql.pool_recycle', 3600),
                'echo': self.config_manager.get_boolean('database.mysql.echo', False)
            }
            
            # 构建数据库URL
            db_url = (
                f"mysql+pymysql://{db_config['user']}:{db_config['password']}"
                f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
                f"?charset={db_config['charset']}"
            )
            
            # 创建SQLAlchemy引擎
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=db_config['pool_size'],
                max_overflow=db_config['max_overflow'],
                pool_timeout=db_config['pool_timeout'],
                pool_recycle=db_config['pool_recycle'],
                echo=db_config['echo']
            )
            
            # 创建会话工厂
            self.Session = sessionmaker(bind=self.engine)
            
            log.info("MySQL客户端初始化成功")
            
        except Exception as e:
            log.error(f"初始化数据库连接失败: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Session:
        """获取数据库会话的上下文管理器"""
        session = None
        try:
            session = self.Session()
            yield session
            session.commit()
        except Exception as e:
            log.error(f"数据库会话错误: {e}")
            if session:
                session.rollback()
            raise
        finally:
            if session:
                session.close()
    
    def create_tables(self):
        """创建所有表"""
        try:
            Base.metadata.create_all(self.engine)
            log.info("数据库表创建成功")
        except Exception as e:
            log.error(f"创建表失败: {e}")
            raise
    
    def drop_tables(self):
        """删除所有表"""
        try:
            Base.metadata.drop_all(self.engine)
            log.info("数据库表删除成功")
        except Exception as e:
            log.error(f"删除表失败: {e}")
            raise
    
    def add(self, obj: Base) -> Base:
        """
        添加对象到数据库
        
        Args:
            obj: 要添加的对象
            
        Returns:
            添加的对象
        """
        try:
            with self.get_session() as session:
                session.add(obj)
                session.flush()
                session.refresh(obj)
                return obj
        except Exception as e:
            log.error(f"添加对象失败: {e}")
            raise
    
    def add_all(self, objects: List[Base]) -> List[Base]:
        """
        批量添加对象到数据库
        
        Args:
            objects: 要添加的对象列表
            
        Returns:
            添加的对象列表
        """
        try:
            with self.get_session() as session:
                session.add_all(objects)
                session.flush()
                for obj in objects:
                    session.refresh(obj)
                return objects
        except Exception as e:
            log.error(f"批量添加对象失败: {e}")
            raise
    
    def get_by_id(self, model_class: Type[T], id_value: Any) -> Optional[T]:
        """
        根据ID获取对象
        
        Args:
            model_class: 模型类
            id_value: ID值
            
        Returns:
            找到的对象或None
        """
        try:
            with self.get_session() as session:
                return session.query(model_class).filter_by(id=id_value).first()
        except Exception as e:
            log.error(f"根据ID获取对象失败: {e}")
            raise
    
    def get_all(self, model_class: Type[T], limit: Optional[int] = None) -> List[T]:
        """
        获取所有对象
        
        Args:
            model_class: 模型类
            limit: 限制数量
            
        Returns:
            对象列表
        """
        try:
            with self.get_session() as session:
                query = session.query(model_class)
                if limit:
                    query = query.limit(limit)
                return query.all()
        except Exception as e:
            log.error(f"获取所有对象失败: {e}")
            raise
    
    def update(self, obj: Base) -> Base:
        """
        更新对象
        
        Args:
            obj: 要更新的对象
            
        Returns:
            更新后的对象
        """
        try:
            with self.get_session() as session:
                session.merge(obj)
                session.flush()
                session.refresh(obj)
                return obj
        except Exception as e:
            log.error(f"更新对象失败: {e}")
            raise
    
    def delete(self, obj: Base) -> bool:
        """
        删除对象
        
        Args:
            obj: 要删除的对象
            
        Returns:
            是否删除成功
        """
        try:
            with self.get_session() as session:
                session.delete(obj)
                return True
        except Exception as e:
            log.error(f"删除对象失败: {e}")
            raise
    
    def delete_by_id(self, model_class: Type[T], id_value: Any) -> bool:
        """
        根据ID删除对象
        
        Args:
            model_class: 模型类
            id_value: ID值
            
        Returns:
            是否删除成功
        """
        try:
            with self.get_session() as session:
                obj = session.query(model_class).filter_by(id=id_value).first()
                if obj:
                    session.delete(obj)
                    return True
                return False
        except Exception as e:
            log.error(f"根据ID删除对象失败: {e}")
            raise
    
    def count(self, model_class: Type[T]) -> int:
        """
        统计对象数量
        
        Args:
            model_class: 模型类
            
        Returns:
            对象数量
        """
        try:
            with self.get_session() as session:
                return session.query(model_class).count()
        except Exception as e:
            log.error(f"统计对象数量失败: {e}")
            raise
    
    def execute_sql(self, sql: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        直接执行SQL查询
        
        Args:
            sql: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果列表
        """
        try:
            with self.get_session() as session:
                result = session.execute(text(sql), params or {})
                if result.returns_rows:
                    return [dict(row._mapping) for row in result]
                return []
        except Exception as e:
            log.error(f"SQL查询执行失败: {e}")
            raise
    
    def execute_update(self, sql: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行更新SQL（INSERT, UPDATE, DELETE）
        
        Args:
            sql: SQL语句
            params: 参数
            
        Returns:
            影响的行数
        """
        try:
            with self.get_session() as session:
                result = session.execute(text(sql), params or {})
                session.commit()
                return result.rowcount
        except Exception as e:
            log.error(f"SQL更新执行失败: {e}")
            raise
    
    def execute_many(self, sql: str, params_list: List[Dict[str, Any]]) -> int:
        """
        批量执行SQL
        
        Args:
            sql: SQL语句
            params_list: 参数列表
            
        Returns:
            影响的行数
        """
        try:
            with self.get_session() as session:
                result = session.execute(text(sql), params_list)
                session.commit()
                return result.rowcount
        except Exception as e:
            log.error(f"批量SQL执行失败: {e}")
            raise
    
    def check_connection(self) -> bool:
        """
        检查数据库连接是否正常
        
        Returns:
            连接状态
        """
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            log.error(f"数据库连接检查失败: {e}")
            return False
    
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            log.info("数据库连接已关闭")


    def get_tables(self) -> List[str]:
        """获取所有表名"""
        return self.execute_sql("SHOW TABLES")
    
    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        return self.execute_sql(f"SHOW CREATE TABLE {table_name}")
    