import json
import os
from typing import Any, Dict

class ConfigManager:
    _instance = None
    _config: Dict[str, Any] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = "config.json") -> None:
        """Загружает конфигурацию из JSON файла."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file {config_path} not found")
        with open(config_path, "r", encoding="utf-8") as f:
            self._config = json.load(f)

    def get(self, key: str, default=None):
        """Получить значение по точечному пути, например 'lm_studio.api_url'."""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        return value