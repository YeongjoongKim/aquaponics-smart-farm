import json
import os
import threading

# 기본 설정 파일 경로 (app 폴더 상위에 있다고 가정)
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.json')

class ConfigManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        # 싱글톤 패턴 적용 (어디서든 같은 설정을 공유하기 위해)
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ConfigManager, cls).__new__(cls)
                    cls._instance.config = {}
                    cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """JSON 파일에서 설정을 읽어옵니다."""
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                print("Configuration loaded successfully.")
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = {}
        else:
            print(f"Config file not found at {CONFIG_PATH}")
            self.config = {}

    def save_config(self):
        """현재 설정을 JSON 파일로 저장합니다."""
        try:
            with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2)
            print("Configuration saved.")
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key, default=None):
        """특정 설정값을 가져옵니다."""
        return self.config.get(key, default)

    def update(self, new_config):
        """설정을 업데이트하고 저장합니다. (재귀적 병합)"""
        def merge_dicts(d1, d2):
            for k, v in d2.items():
                if isinstance(v, dict) and k in d1 and isinstance(d1[k], dict):
                    merge_dicts(d1[k], v)
                else:
                    d1[k] = v
        
        with self._lock:
            merge_dicts(self.config, new_config)
            return self.save_config()

    def get_thresholds(self):
        """알림 임계값 설정만 가져오는 편의 함수"""
        return self.config.get('monitoring', {}).get('alert_thresholds', {})