from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
import yaml
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from enum import Enum
import logging
import os
from src.utils.logger import get_logger


class Environment(Enum):
    DEVELOPMENT = "dev"
    TESTING = "test"
    PRODUCTION = "prod"

class ConfigChangeEvent:
    def __init__(self, key: str, old_value: Any, new_value: Any):
        self.key = key
        self.old_value = old_value
        self.new_value = new_value

class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.log = get_logger()

    def on_modified(self, event):
        if event.src_path.endswith('.yaml'):
            try:
                with open(event.src_path, 'r') as f:
                    old_config = self.config_manager._config.copy()
                    config_data = yaml.safe_load(f)
                    self.config_manager._merge_config(config_data)
                    
                    # Notify about changed values
                    for key in self.config_manager._config:
                        if key in old_config:
                            if self.config_manager._config[key] != old_config[key]:
                                self.config_manager._notify_listeners(
                                    ConfigChangeEvent(
                                        key=key,
                                        old_value=old_config[key],
                                        new_value=self.config_manager._config[key]
                                    )
                                )
            except Exception as e:
                self.log.error(f"配置文件重新加载错误: {e}")

class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._config: Dict[str, Any] = {}
            self._listeners: List[Callable[[ConfigChangeEvent], None]] = []
            self._cache = {}
            self._initialized = True
            self._logger = get_logger()

    def init(self, config_dir: Path):
        """Initialize the configuration manager"""
        self._logger.info(f"初始化配置管理器")
        
        # 首先加载原来的配置文件（向后兼容）
        self._load_configs(config_dir)
        
        
        # 监视配置文件变化
        self._setup_file_watcher(config_dir)

    def _load_configs(self, config_dir: Path) -> None:
        """Load all YAML configuration files from the specified directory"""
        self._logger.info(f"从 {config_dir} 加载配置")
        for config_file in config_dir.glob("*.yaml"):
            try:
                self._logger.info(f"发现配置文件: {config_file}")
                with open(config_file, 'r') as f:
                    config_data = yaml.safe_load(f)
                    self._logger.info(f"加载配置数据: {config_data}")
                    self._merge_config(config_data)
            except Exception as e:
                self._logger.error(f"加载配置文件 {config_file} 错误: {e}")



    def _merge_env_specific_config(self, config_data: Dict[str, Any]) -> None:
        """Merge configuration data from environment-specific sections"""
        if not config_data:
            return
            
        self._logger.info(f"合并环境 {self._environment.value} 的配置数据")
        env_config = config_data.get(self._environment.value, {})
        self._logger.debug(f"环境配置段落: {env_config}")
        self._config.update(env_config)
        self._logger.debug(f"更新后的配置: {self._config}")
        self._cache.clear()

    def _merge_direct_config(self, config_data: Dict[str, Any]) -> None:
        """Merge configuration data directly without looking for environment sections"""
        if not config_data:
            return
            
        self._logger.info(f"直接合并配置数据")
        self._logger.debug(f"配置数据: {config_data}")
        self._config.update(config_data)
        self._logger.debug(f"更新后的配置: {self._config}")
        self._cache.clear()

    def _merge_config(self, config_data: Dict[str, Any]) -> None:
        """Merge new configuration data with existing config"""
        # 处理环境变量替换
        config_data = self._replace_env_vars(config_data)
        # 保持向后兼容性，尝试两种方式合并配置
        self._merge_direct_config(config_data)
    
    def _replace_env_vars(self, data: Any) -> Any:
        """递归替换配置中的环境变量"""
        if isinstance(data, dict):
            return {key: self._replace_env_vars(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._replace_env_vars(item) for item in data]
        elif isinstance(data, str) and data.startswith("${") and data.endswith("}"):
            # 提取环境变量名
            env_var = data[2:-1]
            return os.getenv(env_var, data)  # 如果环境变量不存在，返回原值
        else:
            return data

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key path"""
        if key in self._cache:
            return self._cache[key]

        keys = key.split('.')
        value = self._config
        try:
            for k in keys:
                value = value[k]
            self._cache[key] = value
            return value
        except (KeyError, TypeError):
            return default

    def get_string(self, key: str, default: str = "") -> str:
        """Get string configuration value"""
        value = self.get(key, default)
        return str(value)

    def get_int(self, key: str, default: int = 0) -> int:
        """Get integer configuration value"""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    def get_boolean(self, key: str, default: bool = False) -> bool:
        """Get boolean configuration value"""
        value = self.get(key, default)
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return bool(value)

    def add_listener(self, listener: Callable[[ConfigChangeEvent], None]) -> None:
        """Add configuration change listener"""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable[[ConfigChangeEvent], None]) -> None:
        """Remove configuration change listener"""
        self._listeners.remove(listener)

    def _notify_listeners(self, event: ConfigChangeEvent) -> None:
        """Notify all listeners of configuration changes"""
        for listener in self._listeners:
            try:
                listener(event)
            except Exception as e:
                self._logger.error(f"配置变更监听器错误: {e}")

    def _setup_file_watcher(self, config_dir: Path) -> None:
        """Setup file watcher for configuration files"""
        if not config_dir.exists():
            self._logger.warning(f"配置目录不存在，无法设置文件监视器: {config_dir}")
            return
            
        self._logger.info(f"为目录设置文件监视器: {config_dir}")
        event_handler = ConfigFileHandler(self)  # Use our custom handler
        observer = Observer()
        observer.schedule(event_handler, str(config_dir), recursive=False)
        observer.start()

    def get_config(self):
        """获取配置数据"""
        return self._config
    
    def update_config(self, key_path, value):
        """
        更新配置中的特定值
        
        Args:
            key_path: 配置路径，使用点号分隔，例如 'openai.api_key'
            value: 要设置的新值
        """
        if not self._config:
            raise ValueError("配置尚未初始化，请先调用init方法")
            
        keys = key_path.split('.')
        config = self._config
        
        # 遍历路径直到最后一个键
        for key in keys[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        
        # 设置最终键的值
        config[keys[-1]] = value
        
        self._logger.info(f"已更新配置: {key_path}")

