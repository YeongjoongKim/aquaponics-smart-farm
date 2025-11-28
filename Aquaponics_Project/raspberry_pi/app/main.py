import json
import os
from flask import Flask
from flask_cors import CORS
from database import DatabaseManager
from sensors import SensorManager
from api import api_bp, init_api
from config import ConfigManager
from alerts import AlertManager

app = Flask(__name__)
CORS(app)

def main():
    print("=== Aquaponics Smart Farm System Starting ===")
    
    # 1. 설정 로드 (ConfigManager 사용)
    config_mgr = ConfigManager()
    config = config_mgr.config
    
    # 2. 데이터베이스 초기화
    if not os.path.exists('data'):
        os.makedirs('data')
    db = DatabaseManager()
    
    # 3. 알림 매니저 초기화
    alert_mgr = AlertManager(db)
    
    # 4. 센서 매니저 시작 (alert_mgr 전달)
    # 주의: sensors.py의 SensorManager 클래스 __init__도 수정 필요 (아래 참조)
    sensor_mgr = SensorManager(config, db, alert_mgr) 
    sensor_mgr.start_monitoring()
    
    # 5. API 초기화
    init_api(sensor_mgr)
    app.register_blueprint(api_bp)
    
    host = config.get('web_server', {}).get('host', '0.0.0.0')
    port = config.get('web_server', {}).get('port', 5000)
    
    print(f"Server running on http://{host}:{port}")
    app.run(host=host, port=port, use_reloader=False)

if __name__ == '__main__':
    main()