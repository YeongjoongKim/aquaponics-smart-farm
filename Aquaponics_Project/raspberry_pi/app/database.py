import sqlite3
from datetime import datetime
import json
from contextlib import contextmanager

DB_PATH = "data/aquaponics.db"

class DatabaseManager:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """데이터베이스 테이블 초기화"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 센서 데이터 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_readings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    ph REAL,
                    ec REAL,
                    temperature REAL,
                    do REAL,
                    water_level REAL,
                    turbidity REAL,
                    status TEXT
                )
            ''')
            
            # 알림 테이블 (여기에 resolved_at 추가됨!)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    sensor_name TEXT,
                    alert_type TEXT,
                    value REAL,
                    message TEXT,
                    resolved BOOLEAN DEFAULT 0,
                    resolved_at DATETIME  
                )
            ''')
            conn.commit()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def save_reading(self, data):
        """센서 데이터 저장"""
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO sensor_readings (ph, ec, temperature, do, water_level, turbidity, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (data.get('pH'), data.get('EC'), data.get('Temp'), 
                  data.get('DO'), data.get('Level'), data.get('Turbidity'), 'OK'))
            conn.commit()

    def get_recent_readings(self, limit=100):
        """최근 데이터 조회"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sensor_readings ORDER BY timestamp DESC LIMIT ?', (limit,))
            cols = [desc[0] for desc in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]