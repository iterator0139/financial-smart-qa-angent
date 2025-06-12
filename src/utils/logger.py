import logging
import os
import sys
from logging.handlers import RotatingFileHandler, QueueHandler
from queue import Queue
from logging.handlers import QueueListener
from pathlib import Path
import time
import threading

class CustomFormatter(logging.Formatter):
    """自定义日志格式化器，添加颜色支持"""
    
    COLORS = {
        'DEBUG': '\033[94m',  # 蓝色
        'INFO': '\033[92m',   # 绿色
        'WARNING': '\033[93m', # 黄色
        'ERROR': '\033[91m',  # 红色
        'CRITICAL': '\033[91m\033[1m', # 红色加粗
        'RESET': '\033[0m'    # 重置
    }
    
    def __init__(self, fmt=None, datefmt=None, style='%', use_colors=True):
        super().__init__(fmt, datefmt, style)
        self.use_colors = use_colors
    
    def format(self, record):
        log_message = super().format(record)
        if self.use_colors and record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message

class AsyncLogger:
    """
    异步日志类，支持不同级别的日志和自动切分文件
    使用队列处理器实现异步日志
    """
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.loggers = {}
            self.queue = Queue(-1)  # 无限队列
            self.queue_handler = QueueHandler(self.queue)
            self.listener = None
            self._initialized = True
    
    def init(self, log_dir=None, log_level=logging.INFO, max_bytes=10*1024*1024, backup_count=5):
        """
        初始化日志系统
        
        Args:
            log_dir: 日志目录，如果为None则使用项目根目录下的logs目录
            log_level: 日志级别
            max_bytes: 单个日志文件最大字节数
            backup_count: 备份文件数量
        """
        # 创建日志目录
        if log_dir is None:
            project_root = Path(__file__).resolve().parent.parent.parent
            log_dir = project_root / 'logs'
        
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置根日志配置
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # 清除已有的处理器
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # 创建处理器
        handlers = []
        
        # 控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_format = '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s'
        console_formatter = CustomFormatter(console_format, datefmt='%Y-%m-%d %H:%M:%S')
        console_handler.setFormatter(console_formatter)
        handlers.append(console_handler)
        
        # 文件处理器 - 所有日志
        all_log_file = os.path.join(log_dir, 'all.log')
        file_handler = RotatingFileHandler(
            all_log_file, 
            maxBytes=max_bytes, 
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(log_level)
        file_format = '%(asctime)s [%(levelname)s] [%(name)s:%(lineno)d] - %(message)s'
        file_formatter = logging.Formatter(file_format, datefmt='%Y-%m-%d %H:%M:%S')
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
        
        # 文件处理器 - 错误日志
        error_log_file = os.path.join(log_dir, 'error.log')
        error_file_handler = RotatingFileHandler(
            error_log_file, 
            maxBytes=max_bytes, 
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(file_formatter)
        handlers.append(error_file_handler)
        
        # 设置队列监听器
        self.listener = QueueListener(
            self.queue,
            *handlers,
            respect_handler_level=True
        )
        
        # 启动监听器
        self.listener.start()
        
        # 添加队列处理器到根日志器
        root_logger.addHandler(self.queue_handler)
        
        # 记录初始化完成
        root_logger.info("异步日志系统初始化完成")
    
    def get_logger(self, name):
        """
        获取指定名称的日志器
        
        Args:
            name: 日志器名称，通常使用模块名称
            
        Returns:
            Logger: 日志器实例
        """
        if name not in self.loggers:
            logger = logging.getLogger(name)
            # 确保所有日志器都使用队列处理器
            for handler in logger.handlers[:]:
                logger.removeHandler(handler)
            logger.addHandler(self.queue_handler)
            # 阻止日志传播到root logger，避免重复
            logger.propagate = False
            self.loggers[name] = logger
        return self.loggers[name]
    
    def shutdown(self):
        """
        关闭日志系统，确保所有日志都被处理
        """
        if self.listener:
            self.listener.stop()
            self.listener = None

# 全局日志实例
logger = AsyncLogger()

def get_logger(name=None):
    """
    获取日志器的便捷方法
    
    Args:
        name: 日志器名称，如果为None则使用调用者的模块名称
        
    Returns:
        Logger: 日志器实例
    """
    if name is None:
        # 获取调用者的模块名称
        import inspect
        frame = inspect.currentframe().f_back
        name = frame.f_globals['__name__']
    
    return logger.get_logger(name) 