import datetime
from database import DatabaseManager
from config import ConfigManager

class AlertManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.config_mgr = ConfigManager()
        # 중복 알림 방지를 위한 캐시 (sensor_name -> alert_type)
        self.active_alerts = {}

    def check_readings(self, readings):
        """센서 데이터가 임계값을 벗어나는지 검사"""
        thresholds = self.config_mgr.get_thresholds()
        timestamp = datetime.datetime.now()

        # readings 예시: {'pH': 7.0, 'EC': 1200, ...}
        for sensor, value in readings.items():
            # 타임스탬프 등 숫자가 아닌 데이터는 건너뜀
            if not isinstance(value, (int, float)):
                continue
                
            # 해당 센서의 임계값 설정이 있는지 확인
            sensor_cfg = thresholds.get(sensor)
            if not sensor_cfg:
                continue

            alert_type = None
            message = ""

            # 1. Critical 체크 (위험)
            if 'critical_min' in sensor_cfg and value < sensor_cfg['critical_min']:
                alert_type = "CRITICAL"
                message = f"{sensor} is CRITICALLY LOW ({value} < {sensor_cfg['critical_min']})"
            elif 'critical_max' in sensor_cfg and value > sensor_cfg['critical_max']:
                alert_type = "CRITICAL"
                message = f"{sensor} is CRITICALLY HIGH ({value} > {sensor_cfg['critical_max']})"
            
            # 2. Warning 체크 (주의) - Critical이 아닐 때만
            elif 'min' in sensor_cfg and value < sensor_cfg['min']:
                alert_type = "WARNING"
                message = f"{sensor} is LOW ({value} < {sensor_cfg['min']})"
            elif 'max' in sensor_cfg and value > sensor_cfg['max']:
                alert_type = "WARNING"
                message = f"{sensor} is HIGH ({value} > {sensor_cfg['max']})"

            # 알림 처리 로직
            if alert_type:
                self._trigger_alert(sensor, alert_type, value, message, timestamp)
            else:
                self._resolve_alert_if_exists(sensor, timestamp)

    def _trigger_alert(self, sensor, alert_type, value, message, timestamp):
        """알림 발생 및 DB 저장 (중복 방지)"""
        # 이미 같은 타입의 알림이 활성화 상태라면 DB에 또 저장하지 않음 (로그 스팸 방지)
        if self.active_alerts.get(sensor) == alert_type:
            return

        print(f"!!! ALERT [{alert_type}] {message}")
        
        # DB에 저장
        with self.db.get_connection() as conn:
            conn.execute('''
                INSERT INTO alerts (timestamp, sensor_name, alert_type, value, message, resolved)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (timestamp, sensor, alert_type, value, message))
            conn.commit()
        
        # 활성 알림 상태 업데이트
        self.active_alerts[sensor] = alert_type

    def _resolve_alert_if_exists(self, sensor, timestamp):
        """수치가 정상으로 돌아오면 알림 해제"""
        if sensor in self.active_alerts:
            print(f"--- Alert Resolved: {sensor} returned to normal.")
            
            # DB에서 해당 센서의 미해결 알림들을 모두 해결(resolved=1)로 업데이트
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE alerts 
                    SET resolved = 1, resolved_at = ? 
                    WHERE sensor_name = ? AND resolved = 0
                ''', (timestamp, sensor))
                conn.commit()
            
            # 활성 목록에서 제거
            del self.active_alerts[sensor]