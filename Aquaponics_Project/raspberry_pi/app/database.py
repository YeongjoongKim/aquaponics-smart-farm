# -------------------------------------------------------------
# database.py
# SQLite Database Manager (SQLAlchemy ORM)
# Responsible for: 
# 1. Defining the database schema (SensorReading, Alert, Calibration).
# 2. Providing a thread-safe interface for data persistence.
# 3. Handling data cleanup and statistical queries.
# -------------------------------------------------------------

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json

from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, Boolean, func, desc, text
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from sqlalchemy.pool import QueuePool

# Import ConfigLoader type for type hinting
from .config import ConfigLoader

logger = logging.getLogger(__name__)

Base = declarative_base()

# =============================================================
# DATABASE MODELS (SCHEMA)
# =============================================================

class SensorReading(Base):
    """
    Stores individual sensor readings.
     Optimized for Multi-Zone lookups (zone_id, tank_id).
    """
    __tablename__ = 'sensor_readings'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    # Hierarchical Identification
    zone_id = Column(String(20), index=True)  # e.g., 'zone_a', 'zone_b', 'zone_c'
    tank_id = Column(String(30), index=True)  # e.g., 'tank_1', 'start', 'nutrient_tank_1'
    sensor_type = Column(String(20))          # e.g., 'ph', 'ec', 'do', 'temp'
    
    # Data
    value = Column(Float)
    raw_value = Column(Float)  # Original ADC value (optional, for debugging)
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp.isoformat(),
            "zone_id": self.zone_id,
            "tank_id": self.tank_id,
            "sensor_type": self.sensor_type,
            "value": self.value
        }

class Alert(Base):
    """
    Stores system alerts and threshold violations.
    """
    __tablename__ = 'alerts'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    
    sensor_id = Column(String(50), index=True) # Full ID: zone_b_tank1_ph
    alert_type = Column(String(20))            # WARNING, CRITICAL, SYSTEM_FAULT
    value = Column(Float)
    message = Column(String(255))
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)

class Calibration(Base):
    """
    Audit trail for sensor calibration events.
    """
    __tablename__ = 'calibrations'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, default=datetime.now)
    
    sensor_id = Column(String(50), index=True)
    calibration_type = Column(String(20))      # 3-point, 1-point, baseline
    
    # Store points as JSON string because structure varies (low/mid/high vs zero/span)
    raw_points_json = Column(String(500)) 
    
    slope = Column(Float, nullable=True)       # Calculated slope (if applicable)
    intercept = Column(Float, nullable=True)   # Calculated intercept
    valid = Column(Boolean, default=True)
    notes = Column(String(255))

# =============================================================
# DATABASE MANAGER CLASS
# =============================================================

class DatabaseManager:
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.db_path = config.get_db_path()
        self.engine = None
        self.SessionLocal = None
        self.init_db()

    def init_db(self):
        """Initializes the database engine and creates tables."""
        db_url = f"sqlite:///{self.db_path}"
        
        # Connect args for SQLite optimization (WAL mode handled via pragma later if needed)
        self.engine = create_engine(
            db_url, 
            connect_args={"check_same_thread": False},
            poolclass=QueuePool,
            pool_size=5,
            max_overflow=10
        )
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Enable WAL mode for better concurrency in SQLite
        try:
            with self.engine.connect() as connection:
                connection.execute(text("PRAGMA journal_mode=WAL;"))
                logger.info(f"Database initialized at {self.db_path} (WAL Mode enabled)")
        except Exception as e:
            logger.warning(f"Could not enable WAL mode: {e}")

    def get_session(self) -> Session:
        """Returns a new database session. Caller must close it."""
        if not self.SessionLocal:
            raise Exception("Database not initialized")
        return self.SessionLocal()

    # ---------------------------------------------------------
    # DATA SAVING METHODS
    # ---------------------------------------------------------

    def save_readings(self, readings_dict: Dict[str, float]):
        """
        Saves a batch of sensor readings.
        Parses flat ID (e.g., filter_tank_1_ph) into Zone/Tank/Type.
        """
        session = self.get_session()
        try:
            timestamp = datetime.now()
            entries = []
            
            for sensor_id, value in readings_dict.items():
                if value is None: continue
                
                # ID Parsing Logic (Must match api.py / config.py logic)
                # Format: {prefix}_{tank}_{type}
                parts = sensor_id.split('_')
                
                zone_id = "unknown"
                tank_id = "unknown"
                sensor_type = "unknown"
                
                # --- Zone A: filter_tank_1_ph ---
                if sensor_id.startswith('filter_tank'):
                    zone_id = "zone_a"
                    # tank_1
                    tank_id = f"{parts[0]}_{parts[1]}_{parts[2]}" 
                    sensor_type = parts[3]
                    
                # --- Zone B: nutrient_tank_1_ph ---
                elif sensor_id.startswith('nutrient_tank'):
                    zone_id = "zone_b"
                    tank_id = f"{parts[0]}_{parts[1]}_{parts[2]}"
                    sensor_type = parts[3]
                    
                # --- Zone C: zone_cultivation_1_start_ec ---
                elif sensor_id.startswith('zone_cultivation'):
                    zone_id = "zone_c"
                    # start / middle / end
                    tank_id = parts[3] # Position is treated as tank_id for Line
                    sensor_type = parts[4] # ec
                
                # --- Legacy / Fallback ---
                else:
                    zone_id = "other"
                    tank_id = "system"
                    sensor_type = sensor_id

                entry = SensorReading(
                    timestamp=timestamp,
                    zone_id=zone_id,
                    tank_id=tank_id,
                    sensor_type=sensor_type,
                    value=value
                )
                entries.append(entry)
            
            if entries:
                session.add_all(entries)
                session.commit()
                # logger.debug(f"Saved {len(entries)} readings.")
                
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving readings: {e}")
        finally:
            session.close()

    def save_alert(self, alert_data: Dict[str, Any]) -> int:
        """Saves an alert and returns its ID."""
        session = self.get_session()
        try:
            # Check for existing unresolved alert for same sensor/type to prevent duplicates
            existing = session.query(Alert).filter(
                Alert.sensor_id == alert_data['sensor_id'],
                Alert.alert_type == alert_data['alert_type'],
                Alert.resolved == False
            ).first()
            
            if existing:
                # Update existing alert timestamp (keep it active)
                existing.timestamp = datetime.now()
                existing.value = alert_data['value']
                existing.message = alert_data['message']
                session.commit()
                return existing.id
            
            # Create new
            new_alert = Alert(
                sensor_id=alert_data['sensor_id'],
                alert_type=alert_data['alert_type'],
                value=alert_data['value'],
                message=alert_data['message']
            )
            session.add(new_alert)
            session.commit()
            return new_alert.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving alert: {e}")
            return -1
        finally:
            session.close()

    def resolve_alert(self, alert_id: int) -> bool:
        """Mark an alert as resolved."""
        session = self.get_session()
        try:
            alert = session.query(Alert).get(alert_id)
            if alert:
                alert.resolved = True
                alert.resolved_at = datetime.now()
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Error resolving alert: {e}")
            return False
        finally:
            session.close()

    def save_calibration(self, calib_data: Dict[str, Any]):
        """Saves a calibration record."""
        session = self.get_session()
        try:
            entry = Calibration(
                sensor_id=calib_data['sensor_id'],
                calibration_type=calib_data['calibration_type'],
                raw_points_json=json.dumps(calib_data['points']),
                notes=calib_data.get('notes', '')
            )
            session.add(entry)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving calibration: {e}")
        finally:
            session.close()

    # ---------------------------------------------------------
    # DATA RETRIEVAL METHODS (API Support)
    # ---------------------------------------------------------

    def get_readings_history(self, hours: int = 24, zone_id: Optional[str] = None, limit: Optional[int] = 1000) -> List[Dict[str, Any]]:
        """
        Retrieves historical data, flattened for charting/export.
        Optimized to pivot data: One row per timestamp, columns for sensors.
        """
        # Note: Pivoting in SQL is complex. Here we fetch and pivot in Python for flexibility.
        session = self.get_session()
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            query = session.query(SensorReading).filter(SensorReading.timestamp >= start_time)
            
            if zone_id:
                query = query.filter(SensorReading.zone_id == zone_id)
                
            readings = query.order_by(SensorReading.timestamp.asc()).all()
            
            # Pivot Logic: Group by Timestamp
            # Result: [{'timestamp': '...', 'filter_tank_1_ph': 7.0, 'zone_b_ec': 1200}, ...]
            grouped_data = {}
            
            for r in readings:
                # Round timestamp to minute to group nearby readings (from same poll cycle)
                ts_key = r.timestamp.replace(second=0, microsecond=0).isoformat()
                
                if ts_key not in grouped_data:
                    grouped_data[ts_key] = {"timestamp": ts_key}
                
                # Reconstruct ID for flat structure: {tank}_{type}
                # e.g. tank_1_ph, start_ec
                flat_key = f"{r.tank_id}_{r.sensor_type}"
                
                # Add Zone prefix if requesting all zones to avoid collision
                if not zone_id:
                    flat_key = f"{r.zone_id}_{flat_key}"
                    
                grouped_data[ts_key][flat_key] = r.value
            
            # Convert to list and limit
            result_list = list(grouped_data.values())
            
            # If limit is set, take the *last* N records (most recent)
            if limit and len(result_list) > limit:
                result_list = result_list[-limit:]
                
            return result_list
            
        except Exception as e:
            logger.error(f"Error retrieving history: {e}")
            return []
        finally:
            session.close()

    def get_sensor_statistics(self, hours: int = 24) -> Dict[str, Dict[str, float]]:
        """
        Calculates Min/Max/Avg for each sensor over the last N hours.
        """
        session = self.get_session()
        try:
            start_time = datetime.now() - timedelta(hours=hours)
            
            # SQLAlchemy aggregation
            stats_query = session.query(
                SensorReading.zone_id,
                SensorReading.tank_id,
                SensorReading.sensor_type,
                func.min(SensorReading.value).label('min_val'),
                func.max(SensorReading.value).label('max_val'),
                func.avg(SensorReading.value).label('avg_val'),
                func.count(SensorReading.value).label('count')
            ).filter(
                SensorReading.timestamp >= start_time
            ).group_by(
                SensorReading.zone_id, SensorReading.tank_id, SensorReading.sensor_type
            ).all()
            
            result = {}
            for row in stats_query:
                # Reconstruct Key: zone_tank_type
                key = f"{row.zone_id}_{row.tank_id}_{row.sensor_type}"
                result[key] = {
                    "min": round(row.min_val, 2),
                    "max": round(row.max_val, 2),
                    "avg": round(row.avg_val, 2),
                    "count": row.count
                }
            return result
            
        except Exception as e:
            logger.error(f"Error calculating stats: {e}")
            return {}
        finally:
            session.close()

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Returns a list of unresolved alerts."""
        session = self.get_session()
        try:
            alerts = session.query(Alert).filter(Alert.resolved == False).order_by(desc(Alert.timestamp)).all()
            return [
                {
                    "id": a.id,
                    "timestamp": a.timestamp.isoformat(),
                    "sensor_id": a.sensor_id,
                    "alert_type": a.alert_type,
                    "value": a.value,
                    "message": a.message
                } for a in alerts
            ]
        finally:
            session.close()

    # ---------------------------------------------------------
    # MAINTENANCE METHODS
    # ---------------------------------------------------------

    def cleanup_old_data(self):
        """
        Deletes data older than the retention policy.
        Called periodically by the scheduler.
        """
        policy = self.config.get_db_retention_policy()
        days_keep = policy.get('raw_data_days', 90)
        
        cutoff_date = datetime.now() - timedelta(days=days_keep)
        
        session = self.get_session()
        try:
            deleted_count = session.query(SensorReading).filter(SensorReading.timestamp < cutoff_date).delete()
            session.commit()
            if deleted_count > 0:
                logger.info(f"Database Cleanup: Removed {deleted_count} sensor readings older than {days_keep} days.")
                
            # Also clean old resolved alerts
            alert_cutoff = datetime.now() - timedelta(days=policy.get('logs_days', 30))
            session.query(Alert).filter(Alert.timestamp < alert_cutoff, Alert.resolved == True).delete()
            session.commit()
            
        except Exception as e:
            session.rollback()
            logger.error(f"Database cleanup failed: {e}")
        finally:
            session.close()