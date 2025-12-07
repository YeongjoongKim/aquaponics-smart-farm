# -------------------------------------------------------------
# api.py
# REST API Endpoints (Flask)
# Responsible for: 
# 1. Handling all external data requests (current, history, export).
# 2. Managing configuration updates (Hot-Reload).
# 3. Serving as the command interface for calibration and alerts.
# -------------------------------------------------------------

import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from io import BytesIO

from flask import Blueprint, jsonify, request, send_file, make_response
from sqlalchemy import desc

# Import core modules
# Note: SensorReading, Alert, Calibration models are imported directly for type hinting, 
# though data operations primarily use DatabaseManager methods.
from .config import ConfigLoader
from .database import DatabaseManager, SensorReading, Alert, Calibration
from .sensors import SensorManager

logger = logging.getLogger(__name__)

# Blueprint for API endpoints
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Global managers (injected during application startup in main.py)
config: Optional[ConfigLoader] = None
db_manager: Optional[DatabaseManager] = None
sensor_manager: Optional[SensorManager] = None

def setup_api_managers(cfg: ConfigLoader, db_mgr: DatabaseManager, sensor_mgr: SensorManager):
    """
    Function to inject global managers into the API module.
    Called once during application startup (in main.py).
    """
    global config, db_manager, sensor_manager
    config = cfg
    db_manager = db_mgr
    sensor_manager = sensor_mgr
    logger.info("API Managers injected successfully.")

# --- Utility Functions ---

def json_success(data: Any) -> Dict[str, Any]:
    """Formats a successful JSON response (JSend style)."""
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "success",
        "data": data
    }

def json_error(message: str, code: int = 500) -> Dict[str, Any]:
    """Formats an error JSON response (JSend style)."""
    return {
        "timestamp": datetime.now().isoformat(),
        "status": "error",
        "message": message,
        "code": code
    }

# =============================================================
# 1. SYSTEM HEALTH AND STATUS ENDPOINTS
# =============================================================

@api_bp.route('/status', methods=['GET'])
def get_status():
    """Check system health & uptime."""
    if not db_manager or not config or not sensor_manager:
        logger.error("System health check failed: Managers not initialized.")
        return jsonify(json_error("System not fully initialized.", 500)), 500
        
    # Check if the serial connection is reported as active by the SensorManager
    serial_active = sensor_manager.serial_handler.is_connected if sensor_manager.serial_handler else False
    
    status_data = {
        "status": "healthy" if serial_active and db_manager.engine else "degraded",
        "version": config.get_all().get('site_info', {}).get('version', '1.5.0'),
        "database": "connected" if db_manager.engine else "disconnected",
        "serial_connection": "active" if serial_active else "inactive",
        "port": config.get_all().get('hardware', {}).get('connection', {}).get('port', 'N/A')
    }
    return jsonify(status_data)

# =============================================================
# 2. SENSOR DATA ENDPOINTS
# =============================================================

@api_bp.route('/current', methods=['GET'])
def get_current_readings():
    """Retrieve the latest sensor readings organized by Zone (A, B, C)."""
    if not sensor_manager:
        return jsonify(json_error("Sensor manager not available.", 503)), 503
        
    # Get latest reading data from the scheduler/serial connection
    # Expected format from SensorManager: {'timestamp': ..., 'readings': {'filter_tank_1_ph': 7.0, ...}}
    readings_data = sensor_manager.get_latest_readings()
    
    if not readings_data:
        return jsonify(json_error("No current data available (serial timeout/disconnect).", 503)), 503

    # Re-structure the flat 'readings' dictionary into Zone A/B/C for API (as per API.md spec)
    structured_data = {
        "zone_a_filtered": {},
        "zone_b_nutrient": {},
        "zone_c_cultivation": {}
    }

    # Helper to safe split sensor ID
    # IDs are typically: {tank_id}_{sensor_type}
    # Examples: filter_tank_1_ph, nutrient_tank_1_ec, zone_cultivation_1_start_ec
    
    for sensor_id, value in readings_data.get('readings', {}).items():
        try:
            parts = sensor_id.split('_')
            
            # --- Zone A: Filter Tanks ---
            if sensor_id.startswith('filter_tank'):
                # Format: filter_tank_1_ph -> parts: ['filter', 'tank', '1', 'ph']
                if len(parts) >= 4:
                    tank_num = parts[2]
                    param = parts[3]
                    tank_key = f"tank_{tank_num}"
                    
                    if tank_key not in structured_data["zone_a_filtered"]:
                        structured_data["zone_a_filtered"][tank_key] = {}
                    structured_data["zone_a_filtered"][tank_key][param] = value

            # --- Zone B: Nutrient Tanks ---
            elif sensor_id.startswith('nutrient_tank'):
                # Format: nutrient_tank_1_ph -> parts: ['nutrient', 'tank', '1', 'ph']
                # Note: Updated from single 'zone_nutrient' to multi 'nutrient_tank_X'
                if len(parts) >= 4:
                    tank_num = parts[2]
                    param = parts[3]
                    tank_key = f"tank_{tank_num}"
                    
                    if tank_key not in structured_data["zone_b_nutrient"]:
                        structured_data["zone_b_nutrient"][tank_key] = {}
                    structured_data["zone_b_nutrient"][tank_key][param] = value

            # --- Zone C: Cultivation Line ---
            elif sensor_id.startswith('zone_cultivation'):
                # Format: zone_cultivation_1_start_ec -> parts: ['zone', 'cultivation', '1', 'start', 'ec']
                if len(parts) >= 5:
                    position = parts[3] # start, middle, end
                    param = parts[4]    # ec
                    
                    if position not in structured_data["zone_c_cultivation"]:
                        structured_data["zone_c_cultivation"][position] = {}
                    structured_data["zone_c_cultivation"][position][param] = value
                    
        except Exception as e:
            logger.warning(f"Failed to parse sensor ID {sensor_id} for API structure: {e}")
            continue

    return jsonify(json_success(structured_data))

@api_bp.route('/history', methods=['GET'])
def get_historical_data():
    """Retrieve historical sensor data for charting or analysis."""
    try:
        hours = int(request.args.get('hours', 24))
        zone = request.args.get('zone')
        limit = int(request.args.get('limit', 1000))
        
        # Use the specialized DB manager method
        history_list = db_manager.get_readings_history(hours=hours, zone_id=zone, limit=limit)
        
        response_data = {
            "range_hours": hours,
            "count": len(history_list),
            "data": history_list
        }
        return jsonify(json_success(response_data))

    except Exception as e:
        logger.error(f"Error retrieving history: {e}")
        return jsonify(json_error(f"Error retrieving history: {e}", 400)), 400


@api_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """Get Min/Max/Avg statistical analysis of sensor data."""
    try:
        hours = int(request.args.get('hours', 24))
        
        # Use the specialized DB manager method
        stats = db_manager.get_sensor_statistics(hours=hours)

        response_data = {
            "hours": hours,
            "statistics": stats
        }
        return jsonify(json_success(response_data))

    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        return jsonify(json_error(f"Error calculating statistics: {e}", 500)), 500

# =============================================================
# 3. ALERTS MANAGEMENT ENDPOINTS
# =============================================================

@api_bp.route('/alerts/active', methods=['GET'])
def get_active_alerts():
    """Retrieve all active (unresolved) alerts."""
    try:
        # Use the specialized DB manager method
        alerts_list = db_manager.get_active_alerts()
        
        return jsonify(json_success({"count": len(alerts_list), "alerts": alerts_list}))
    except Exception as e:
        logger.error(f"Error retrieving active alerts: {e}")
        return jsonify(json_error(f"Error retrieving active alerts: {e}", 500)), 500

@api_bp.route('/alerts', methods=['GET'])
def get_alerts_history():
    """Retrieve alert history logs by date range."""
    session = db_manager.get_session()
    try:
        # Default: last 7 days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7) 
        limit = int(request.args.get('limit', 100))

        # Handle date parsing from query parameters (requires ISO format)
        if 'start_date' in request.args:
            try:
                start_date = datetime.fromisoformat(request.args.get('start_date'))
            except ValueError:
                pass # Use default if parsing fails
        if 'end_date' in request.args:
            try:
                end_date = datetime.fromisoformat(request.args.get('end_date'))
            except ValueError:
                pass

        # Fetch alerts from DB
        alerts = session.query(Alert).filter(
            Alert.timestamp >= start_date,
            Alert.timestamp <= end_date
        ).order_by(desc(Alert.timestamp)).limit(limit).all()

        alerts_list = [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "sensor_id": a.sensor_id,
                "alert_type": a.alert_type,
                "value": a.value,
                "message": a.message,
                "resolved": a.resolved
            } for a in alerts
        ]
        
        return jsonify(json_success({"count": len(alerts_list), "alerts": alerts_list}))

    except Exception as e:
        logger.error(f"Error retrieving alert history: {e}")
        return jsonify(json_error(f"Error retrieving alert history: {e}", 400)), 400
    finally:
        session.close()

@api_bp.route('/alert', methods=['POST'])
def create_manual_alert():
    """Manually trigger an alert."""
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify(json_error("Missing required fields for manual alert (message).", 400)), 400
        
    # Use default/dummy values for manual alert
    alert_data = {
        "sensor_id": data.get('sensor_id', 'SYSTEM_MANUAL'),
        "alert_type": data.get('alert_type', 'WARNING'),
        "value": data.get('value', -999.0), # Use -999.0 for manual non-sensor value
        "message": data['message']
    }
    
    alert_id = db_manager.save_alert(alert_data)
    
    if alert_id > 0:
        return jsonify(json_success({"alert_id": alert_id, "message": "Alert created successfully"})), 201
    else:
        return jsonify(json_error("Failed to save manual alert to database.")), 500

@api_bp.route('/alert/<int:alert_id>/resolve', methods=['POST'])
def resolve_alert(alert_id):
    """Mark alert as resolved."""
    if db_manager.resolve_alert(alert_id):
        return jsonify(json_success({"message": f"Alert ID {alert_id} resolved successfully."}))
    else:
        return jsonify(json_error(f"Alert ID {alert_id} not found or resolution failed.", 404)), 404


# =============================================================
# 4. CONFIGURATION ENDPOINTS
# =============================================================

@api_bp.route('/config', methods=['GET'])
def get_current_config():
    """Retrieve current system configuration."""
    if not config:
        return jsonify(json_error("Configuration not loaded.", 500)), 500
        
    return jsonify(json_success({"config": config.get_all()}))

@api_bp.route('/config', methods=['POST'])
def update_configuration():
    """Update system settings dynamically (Hot-Reload)."""
    data = request.get_json()
    if not data:
        return jsonify(json_error("No configuration data provided.", 400)), 400
    
    if config.update_config(data):
        return jsonify(json_success({"message": "Configuration updated. New settings applied immediately."}))
    else:
        logger.error(f"Config update failed for data: {data}")
        return jsonify(json_error("Configuration update failed (check JSON structure/file permissions).", 500)), 500

# =============================================================
# 5. CALIBRATION ENDPOINTS
# =============================================================

@api_bp.route('/calibration/<string:sensor_id>', methods=['POST'])
def calibrate_sensor(sensor_id):
    """Trigger calibration logic for a specific sensor."""
    data = request.get_json()
    if not data or 'points' not in data or 'calibration_type' not in data:
        return jsonify(json_error("Missing required calibration fields (points, calibration_type).", 400)), 400

    points = data['points']
    calib_type = data['calibration_type']
    notes = data.get('notes', 'N/A')

    # 1. Send command to Arduino via SensorManager (saves calibration to EEPROM)
    # sensor_manager.perform_calibration will map the ID (e.g. zone_b_tank1_ph) to 
    # Arduino Command (e.g. CALIB_ZB_T1_PH)
    arduino_response = sensor_manager.perform_calibration(sensor_id, calib_type, points)
    
    if arduino_response and 'ERROR' in arduino_response:
        logger.error(f"Arduino calibration failed for {sensor_id}: {arduino_response}")
        return jsonify(json_error(f"Calibration command failed on Arduino: {arduino_response}", 500)), 500

    # 2. Save audit trail to Database
    calib_data = {
        "sensor_id": sensor_id,
        "calibration_type": calib_type,
        "points": points,
        "notes": notes
    }
    db_manager.save_calibration(calib_data)

    return jsonify(json_success({
        "sensor_id": sensor_id,
        "message": f"Calibration constants updated successfully. Arduino Response: {arduino_response}"
    }))

@api_bp.route('/calibration/<string:sensor_id>', methods=['GET'])
def get_calibration_history(sensor_id):
    """Retrieve the last 10 calibration records for a specific sensor."""
    session = db_manager.get_session()
    try:
        history = session.query(Calibration).filter(
            Calibration.sensor_id == sensor_id
        ).order_by(desc(Calibration.timestamp)).limit(10).all()

        history_list = [
            {
                "timestamp": h.timestamp.isoformat(),
                "calibration_type": h.calibration_type,
                "points": json.loads(h.raw_points_json), # Deserialize JSON string back to dict
                "notes": h.notes,
                "valid": h.valid
            } for h in history
        ]

        return jsonify(json_success({"sensor_id": sensor_id, "history": history_list}))

    except Exception as e:
        logger.error(f"Error retrieving calibration history: {e}")
        return jsonify(json_error(f"Error retrieving calibration history: {e}", 500)), 500
    finally:
        session.close()

# =============================================================
# 6. DATA MANAGEMENT ENDPOINTS
# =============================================================

@api_bp.route('/export', methods=['GET'])
def export_data():
    """Export sensor data in CSV, JSON, or Excel format."""
    format_type = request.args.get('format', 'csv').lower()
    hours = int(request.args.get('hours', 24))
    zone = request.args.get('zone')
    
    if format_type not in ['csv', 'json', 'xlsx']:
        return jsonify(json_error("Invalid format specified. Use csv, json, or xlsx.", 400)), 400

    # 1. Fetch Data
    # Using the existing historical method for data fetching
    raw_data_list = db_manager.get_readings_history(hours=hours, zone_id=zone, limit=None)
    
    # 2. Handle Export Format
    if format_type == 'json':
        # JSON export directly uses the history list format
        return jsonify(json_success({"hours": hours, "count": len(raw_data_list), "data": raw_data_list}))
        
    elif format_type == 'csv' or format_type == 'xlsx':
        try:
            import pandas as pd # Requires pandas library (in requirements.txt)
        except ImportError:
            return jsonify(json_error("Pandas library required for CSV/XLSX export.", 500)), 500
            
        if not raw_data_list:
            return jsonify(json_error("No data found for the specified period.", 404)), 404
        
        # Convert list of dictionaries (where keys vary per timestamp) to DataFrame
        df = pd.DataFrame(raw_data_list)
        
        # Set timestamp as index and sort (clean up for export)
        df = df.set_index('timestamp').sort_index()
        
        # --- Generate Response ---
        if format_type == 'csv':
            csv_data = df.to_csv()
            response = make_response(csv_data)
            filename = f"aquaponics_export_{datetime.now().strftime('%Y%m%d')}.csv"
            response.headers["Content-Disposition"] = f"attachment; filename={filename}"
            response.headers["Content-type"] = "text/csv"
            return response
        
        elif format_type == 'xlsx':
            try:
                # pandas.ExcelWriter uses openpyxl (in requirements.txt)
                output = BytesIO()
                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='Sensor Data')
                
                output.seek(0)
                
                filename = f"aquaponics_export_{datetime.now().strftime('%Y%m%d')}.xlsx"
                return send_file(
                    output, 
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    as_attachment=True,
                    download_name=filename
                )
            except Exception as e:
                logger.error(f"XLSX export failed: {e}")
                return jsonify(json_error(f"XLSX export failed: {e}", 500)), 500
    
    # Should be unreachable
    return jsonify(json_error("Unknown export process failure.", 500)), 500