# -------------------------------------------------------------
# dashboard.py
# Web Dashboard Logic (Flask Blueprint)
# Responsible for: 
# 1. Rendering the main monitoring and settings views.
# 2. Providing data context to HTML templates (Jinja2).
# -------------------------------------------------------------

import logging
from typing import Dict, Any, List, Optional
from flask import Blueprint, render_template, jsonify, redirect, url_for, request
from sqlalchemy import desc # Used for ordering in DB queries

# Import core modules (Assumed to be globally initialized and accessible via a setup function)
from .config import ConfigLoader
from .database import DatabaseManager, Alert, Calibration # Alert model needed for direct query

logger = logging.getLogger(__name__)

# Flask Blueprint setup
dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/')

# Global managers (Placeholders for setup_dashboard_managers)
config: Optional[ConfigLoader] = None
db_manager: Optional[DatabaseManager] = None

def setup_dashboard_managers(cfg: ConfigLoader, db_mgr: DatabaseManager):
    """
    Function to inject global managers into the dashboard module.
    Called once during application startup (in main.py/app.py).
    """
    global config, db_manager
    config = cfg
    db_manager = db_mgr
    logger.info("Dashboard Managers injected successfully.")

# --- Utility Endpoints ---

@dashboard_bp.route('/data/zone_structure', methods=['GET'])
def get_zone_structure():
    """
    Provides the static zone structure (for frontend JavaScript initialization).
    This helps the frontend build tabs and grids dynamically based on config.
    """
    if not config:
        logger.error("Zone structure request failed: Configuration not loaded.")
        return jsonify({"error": "Configuration not loaded"}), 500
        
    zones = config.get_all().get('zones', {})
    
    # Extract tank/line IDs for easy front-end listing
    
    # 1. Filtered Tanks (List)
    filtered_tanks = [tank['id'] for tank in zones.get('filtered_tanks', [])]
    
    # 2. Nutrient Tanks (List) - Updated for Multi-Zone
    nutrient_tanks = []
    n_tanks_config = zones.get('nutrient_tanks', [])
    # Fallback for legacy config if 'nutrient_tank' dict exists instead of list
    if not n_tanks_config and 'nutrient_tank' in zones:
         n_tanks_config = [zones['nutrient_tank']]
         
    for tank in n_tanks_config:
        nutrient_tanks.append(tank['id'])
        
    # 3. Cultivation Line (Points)
    line_points = list(zones.get('cultivation_line', {}).get('points', {}).keys())

    zone_data = {
        "filtered_tanks": filtered_tanks,       # e.g. ['filter_tank_1', 'filter_tank_2', ...]
        "nutrient_tanks": nutrient_tanks,       # e.g. ['nutrient_tank_1', 'nutrient_tank_2', ...]
        "cultivation_line_points": line_points  # e.g. ['start', 'middle', 'end']
    }
    
    return jsonify(zone_data)

# =============================================================
# 1. MAIN DASHBOARD VIEW
# =============================================================

@dashboard_bp.route('/')
def index():
    """
    Renders the main monitoring dashboard. 
    This page uses AJAX calls to /api/current and /api/history for real-time data.
    """
    if not config or not db_manager:
        logger.critical("System not initialized. Cannot render dashboard.")
        return "System not initialized. Check logs.", 500

    # Pass static configuration data needed for the layout
    site_info = config.get_all().get('site_info', {})
    
    # Check for active alerts to display a banner/notification
    active_alert_count = 0
    try:
        # Use the efficient DB Manager method (from database.py)
        active_alerts = db_manager.get_active_alerts()
        active_alert_count = len(active_alerts)
    except Exception as e:
        logger.warning(f"Failed to check active alerts during index render: {e}")
        pass 

    # The actual sensor readings will be fetched by client-side JS calling /api/current
    return render_template('dashboard/index.html', 
                           site_info=site_info,
                           active_alerts=active_alert_count)

# =============================================================
# 2. SETTINGS AND MAINTENANCE VIEWS
# =============================================================

@dashboard_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """
    Renders the settings page, allowing users to view and update thresholds.
    """
    if not config:
        return "System not initialized.", 500

    if request.method == 'POST':
        # This handles POST requests from the settings form
        data = request.form.to_dict()
        
        # Build the update payload structure (only monitoring/alerts can be updated via UI)
        update_payload: Dict[str, Any] = {"monitoring": {"alert_thresholds": {}}}
        
        # Simple parsing logic for form data 
        for key, value in data.items():
            if not value: continue
            
            # Check if value is numeric (allowing for negative numbers and decimals)
            # Simple check: remove one decimal point and optional leading minus, then check isdigit
            is_numeric = value.replace('.', '', 1).isdigit() or (value.startswith('-') and value[1:].replace('.', '', 1).isdigit())
            
            if is_numeric:
                try:
                    # Assuming form fields are named like 'PH_min', 'EC_critical_max'
                    # Split only on first underscore to handle keys like critical_max correctly
                    parts = key.upper().split('_', 1)
                    if len(parts) != 2: continue
                    
                    param, threshold_key = parts
                    float_value = float(value)
                    
                    # Ensure param (e.g., PH, EC) is properly capitalized for the config structure
                    if param not in update_payload["monitoring"]["alert_thresholds"]:
                        update_payload["monitoring"]["alert_thresholds"][param] = {}
                        
                    # Threshold key (min, max, critical_min, etc.) is lowercase
                    update_payload["monitoring"]["alert_thresholds"][param][threshold_key.lower()] = float_value
                except (ValueError, IndexError):
                    logger.warning(f"Ignoring malformed or non-threshold field in settings POST: {key}={value}")
                    pass # Ignore non-numeric or malformed fields

        # API endpoint /api/config will handle the actual update and Hot-Reload
        if config.update_config(update_payload):
            logger.info("Settings updated via Dashboard POST.")
            return render_template('dashboard/settings.html', 
                                   config_data=config.get_all(),
                                   success_message="Settings updated successfully (Hot-Reload applied).")
        else:
            logger.error(f"Failed to update settings via Dashboard POST for payload: {update_payload}")
            return render_template('dashboard/settings.html', 
                                   config_data=config.get_all(),
                                   error_message="Failed to update settings.")
    
    # GET request
    return render_template('dashboard/settings.html', config_data=config.get_all())


@dashboard_bp.route('/calibration')
def calibration_view():
    """
    Renders the calibration wizard/view.
    Dynamically builds the list of sensors based on config.json.
    """
    if not config:
        return "System not initialized.", 500
        
    # Retrieve all sensors that require software calibration (PH, EC, DO, Turbidity)
    all_zones = config.get_all().get('zones', {})
    all_calib_config = config.get_all().get('calibration', {})
    
    calibratable_sensors: List[Dict[str, Any]] = []
    
    # Helper to clean up sensor data and generate ID
    def append_calibratable_sensor(id_prefix, sensor_data, name_prefix):
        sensor_type = sensor_data['type']
        
        # Skip temperature (digital) and water level (hardware pot)
        if sensor_type in ['temperature', 'water_level']:
            return
            
        # Determine unique ID for API/Arduino lookup
        # ID Format MUST match api.py expectations: {tank_id}_{sensor_type}
        # Example: filter_tank_1_ph, nutrient_tank_1_ec
        sensor_id = f"{id_prefix}_{sensor_type}"
        
        # Special handling for Zone C (Line) which has points
        if 'point' in sensor_data:
             # ID Format: {line_id}_{point}_{sensor_type}
             # Example: zone_cultivation_1_start_ec
             sensor_id = f"{id_prefix}_{sensor_data['point']}_{sensor_type}"

        # Human readable name
        name = f"{name_prefix} - {sensor_type.upper()}"
        
        # Find default calibration config for tooltips
        calib_type_default = all_calib_config.get(sensor_type, {})
        
        calibratable_sensors.append({
            "id": sensor_id,
            "name": name,
            "type": sensor_type,
            "calib_info": calib_type_default
        })

    # 1. Zone A: Filter Tanks
    for tank in all_zones.get('filtered_tanks', []):
        tank_id = tank['id'] # e.g. filter_tank_1
        tank_desc = tank.get('description', tank_id).split('#')[-1] # "1" from "#1"
        for sensor in tank.get('sensors', []):
            append_calibratable_sensor(tank_id, sensor, f"Filter Tank {tank_desc}")

    # 2. Zone B: Nutrient Tanks (Multi-Tank List)
    n_tanks = all_zones.get('nutrient_tanks', [])
    # Legacy fallback
    if not n_tanks and 'nutrient_tank' in all_zones:
         n_tanks = [all_zones['nutrient_tank']]

    for tank in n_tanks:
        tank_id = tank['id'] # e.g. nutrient_tank_1
        # Extract number for cleaner UI name
        tank_num = tank_id.split('_')[-1] if '_' in tank_id else tank_id
        for sensor in tank.get('sensors', []):
            append_calibratable_sensor(tank_id, sensor, f"Nutrient Tank {tank_num}")
            
    # 3. Zone C: Cultivation Line (EC only)
    cultivation_line = all_zones.get('cultivation_line', {})
    line_id = cultivation_line.get('id', 'zone_cultivation_1')
    
    for point, sensors in cultivation_line.get('points', {}).items():
        for sensor in sensors:
            # Inject the point (start, middle, end) into sensor data helper
            sensor_data_with_point = sensor.copy()
            sensor_data_with_point['point'] = point 
            
            name_prefix = f"Line ({point.capitalize()})"
            append_calibratable_sensor(line_id, sensor_data_with_point, name_prefix)
            
    return render_template('dashboard/calibration.html', 
                           sensors=calibratable_sensors,
                           calib_defaults=all_calib_config)


# =============================================================
# 3. ALERTS & LOGS VIEW
# =============================================================

@dashboard_bp.route('/alerts')
def alerts_view():
    """
    Renders the alert history log and displays active alerts.
    """
    if not db_manager:
        return "Database not initialized.", 500
        
    try:
        # Get active alerts (unresolved) using the efficient DB Manager method
        active_alerts_data = db_manager.get_active_alerts()
        
        # Get recent history (resolved and unresolved) - fetch from DB for raw objects
        session = db_manager.get_session()
        # Fetch the most recent 50 alerts
        recent_alerts = session.query(Alert).order_by(desc(Alert.timestamp)).limit(50).all()
        session.close() # Close session immediately after query
        
        # Simple serialization
        def serialize_alert(a):
            return {
                "id": a.id,
                "timestamp": a.timestamp.isoformat(),
                "sensor_id": a.sensor_id,
                "alert_type": a.alert_type,
                "value": a.value,
                "message": a.message,
                "resolved": a.resolved
            }
            
        # active_alerts_data is already a list of dictionaries from db_manager
        return render_template('dashboard/alerts.html',
                               active_alerts=active_alerts_data,
                               recent_alerts=[serialize_alert(a) for a in recent_alerts])
                               
    except Exception as e:
        logger.error(f"Error retrieving alerts for dashboard view: {e}")
        return f"Error retrieving alerts: {e}", 500