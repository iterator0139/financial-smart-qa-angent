from watchdog.events import FileSystemEventHandler
from pathlib import Path
import yaml
import logging

class ConfigFileHandler(FileSystemEventHandler):
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self._logger = logging.getLogger(__name__)

    def on_modified(self, event):
        if event.src_path.endswith('.yaml'):
            try:
                with open(event.src_path, 'r') as f:
                    config_data = yaml.safe_load(f)
                    self.config_manager._merge_config(config_data)
                self._logger.info(f"Configuration reloaded from {event.src_path}")
            except Exception as e:
                self._logger.error(f"Error reloading config: {e}") 