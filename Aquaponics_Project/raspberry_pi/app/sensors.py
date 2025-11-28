import serial
import json
import time
import threading
from datetime import datetime
from database import DatabaseManager 


class SensorManager:
    def __init__(self, config, db_manager, alert_manager=None):
        self.serial_port = config['hardware'].get('serial_port', '/dev/ttyUSB0')
        self.baud_rate = 115200
        self.db = db_manager
        self.alert_mgr = alert_manager  # 추가
        self.latest_data = {}
        self.running = False
        self.ser = None

    def connect_serial(self):
        try:
            self.ser = serial.Serial(self.serial_port, self.baud_rate, timeout=1)
            print(f"Connected to Arduino on {self.serial_port}")
            return True
        except Exception as e:
            print(f"Serial connection failed: {e}")
            return False

    def start_monitoring(self):
        self.running = True
        thread = threading.Thread(target=self._read_loop, daemon=True)
        thread.start()

# app/sensors.py 의 _read_loop 메소드 수정

    def _read_loop(self):
        # --- [수정 시작] 테스트를 위한 가짜 데이터 생성 모드 ---
        import random
        
        # 아두이노 연결 시도
        if not self.ser:
            self.connect_serial()

        while self.running:
            # 1. 실제 아두이노가 연결된 경우
            if self.ser and self.ser.is_open:
                try:
                    if self.ser.in_waiting > 0:
                        line = self.ser.readline().decode('utf-8').strip()
                        if line.startswith('{') and line.endswith('}'):
                            data = json.loads(line)
                            self._process_data(data)
                except Exception as e:
                    print(f"Error reading sensor: {e}")
            
            # 2. 아두이노가 없는 경우 (PC 테스트 모드)
            else:
                print("⚠️ No Arduino found. Generating TEST data...")
                # 가짜 데이터 생성 (랜덤 값)
                fake_data = {
                    "pH": round(random.uniform(6.0, 8.0), 2),      # 6.0 ~ 8.0 사이
                    "EC": random.randint(1000, 1500),              # 1000 ~ 1500 사이
                    "Temp": round(random.uniform(20.0, 25.0), 1),  # 20 ~ 25도
                    "DO": round(random.uniform(5.0, 9.0), 2),
                    "Level": random.randint(80, 100),
                    "Turbidity": random.randint(0, 50)
                }
                self._process_data(fake_data)
                time.sleep(5)  # 5초마다 데이터 생성 (실제보다 천천히)
            
            # CPU 과부하 방지
            time.sleep(0.1)
        # --- [수정 끝] ---

        while self.running:
            try:
                if self.ser.in_waiting > 0:
                    line = self.ser.readline().decode('utf-8').strip()
                    # Arduino main.ino가 보내는 JSON 파싱
                    # 예: {"timestamp":12345,"pH":6.8,"EC":1350,"Temp":24.5,"DO":6.2,"Level":95,"Turbidity":50}
                    if line.startswith('{') and line.endswith('}'):
                        data = json.loads(line)
                        self._process_data(data)
            except Exception as e:
                print(f"Error reading sensor: {e}")
                time.sleep(1)

    def _process_data(self, data):
        # 키 이름 매핑 (Arduino "Temp" -> API "temperature")
        processed = {
            "pH": data.get("pH", 0),
            "EC": data.get("EC", 0),
            "temperature": data.get("Temp", 0),
            "DO": data.get("DO", 0),
            "water_level": data.get("Level", 0),
            "turbidity": data.get("Turbidity", 0),
            "timestamp": datetime.now().isoformat()
        }
        
        self.latest_data = processed
        self.db.save_reading(data) # DB에는 원본 키 사용 (위의 database.py 참고)
        # 여기에 임계값 체크(Alert) 로직 추가 가능
        if self.alert_mgr:
            self.alert_mgr.check_readings(processed)

    def get_current_readings(self):
        return self.latest_data