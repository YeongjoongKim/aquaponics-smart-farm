import logging
import datetime
from typing import Dict, Any

# 프로젝트 구조에 맞춘 import 수정
from .database import DatabaseManager
from .config import ConfigLoader  # ConfigManager -> ConfigLoader로 수정

logger = logging.getLogger(__name__)

class AlertManager:
    def __init__(self, config: ConfigLoader, db_manager: DatabaseManager):
   
        self.config = config
        self.db_manager = db_manager
        
        self.active_alerts: Dict[str, str] = {}
        self._load_active_alerts()

    def _load_active_alerts(self):
        try:
            active_list = self.db_manager.get_active_alerts()
            for alert in active_list:
                self.active_alerts[alert['sensor_id']] = alert['alert_type']
            logger.info(f"Loaded {len(self.active_alerts)} active alerts from database.")
        except Exception as e:
            logger.error(f"Failed to load active alerts: {e}")

    def get_param_type_from_id(self, sensor_id: str) -> str:
        try:
            parts = sensor_id.split('_')
            param_type = parts[-1].upper()
            
            if param_type == 'LEVEL': return 'WATER_LEVEL'
            if param_type == 'TEMP': return 'TEMPERATURE'
            
            return param_type
        except IndexError:
            return ""

    def check_readings(self, readings_data: Dict[str, Any]):

        thresholds = self.config.get_alert_thresholds()
        
        current_readings = readings_data.get('readings', readings_data)

        for sensor_id, value in current_readings.items():
            if not isinstance(value, (int, float)):
                continue
                
            param_type = self.get_param_type_from_id(sensor_id)
            sensor_cfg = thresholds.get(param_type)
            
            if not sensor_cfg:
                continue

            alert_type = None
            message = ""

            min_val = sensor_cfg.get('min')
            max_val = sensor_cfg.get('max')
            crit_min = sensor_cfg.get('critical_min')
            crit_max = sensor_cfg.get('critical_max')
            unit = sensor_cfg.get('unit', '')

            if crit_min is not None and value < crit_min:
                alert_type = "CRITICAL"
                message = f"CRITICAL: {sensor_id} value {value}{unit} is below limit {crit_min}{unit}"
            elif crit_max is not None and value > crit_max:
                alert_type = "CRITICAL"
                message = f"CRITICAL: {sensor_id} value {value}{unit} is above limit {crit_max}{unit}"
            
            elif alert_type is None:
                if min_val is not None and value < min_val:
                    alert_type = "WARNING"
                    message = f"WARNING: {sensor_id} value {value}{unit} is low (Optimal > {min_val}{unit})"
                elif max_val is not None and value > max_val:
                    alert_type = "WARNING"
                    message = f"WARNING: {sensor_id} value {value}{unit} is high (Optimal < {max_val}{unit})"

            if alert_type:
                current_status = self.active_alerts.get(sensor_id)
                if current_status != alert_type:
                    self._trigger_alert(sensor_id, alert_type, value, message)
            else:
                self._resolve_alert_if_exists(sensor_id)

    def _trigger_alert(self, sensor_id: str, alert_type: str, value: float, message: str):
        
        logger.warning(f"!!! ALERT [{alert_type}] {sensor_id}: {message}")
        
        alert_data = {
            "sensor_id": sensor_id,
            "alert_type": alert_type,
            "value": value,
            "message": message
        }
        
        saved_id = self.db_manager.save_alert(alert_data)
        
        if saved_id:
            self.active_alerts[sensor_id] = alert_type

    def _resolve_alert_if_exists(self, sensor_id: str):
        """수치가 정상으로 돌아오면 알림 해제"""
        if sensor_id in self.active_alerts:
            logger.info(f"--- Alert Resolved: {sensor_id} returned to normal.")                 
            session = self.db_manager.get_session()
            try:
                from .database import Alert
                alerts = session.query(Alert).filter(
                    Alert.sensor_id == sensor_id, 
                    Alert.resolved == False
                ).all()
                
                for alert in alerts:
                    alert.resolved = True
                    alert.resolved_at = datetime.datetime.now()
                
                session.commit()
            except Exception as e:
                session.rollback()
                logger.error(f"Error resolving alert for {sensor_id}: {e}")
            finally:
                session.close()
            
            del self.active_alerts[sensor_id]