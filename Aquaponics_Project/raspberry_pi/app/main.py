# -------------------------------------------------------------
# main.py
# Application Entry Point and Scheduler
# Responsible for: 
# 1. System Initialization (Config, DB, Sensors).
# 2. Running the main data acquisition loop (Scheduler).
# 3. Executing Alert Threshold logic.
# 4. Starting the Flask Web Server (API/Dashboard).
# -------------------------------------------------------------

import time
import threading
import logging
import sys
import os
from typing import Dict, Any, Optional

# Import core modules
# Note: These imports assume a structured package inside 'raspberry_pi/app'
from .config import ConfigLoader
from .database import DatabaseManager
from .sensors import SensorManager
from .flask_app import create_app # Import the factory function for Flask app

# =============================================================
# 1. CONFIGURATION AND LOGGING SETUP
# =============================================================

# Global references
# These references will be passed to the Flask application context
config: Optional[ConfigLoader] = None
db_manager: Optional[DatabaseManager] = None
sensor_manager: Optional[SensorManager] = None

def setup_logging(log_level: str):
    """Initializes the logging system."""
    global config
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Use RotatingFileHandler for production environment on Raspberry Pi
    try:
        from logging.handlers import RotatingFileHandler
    except ImportError:
        # Fallback for environments where RotatingFileHandler might not be available
        logging.warning("RotatingFileHandler not available. Falling back to simple file logging.")
        from logging import FileHandler as RotatingFileHandler # Placeholder, won't rotate

    log_config = config.get_all().get('logging', {})
    log_file_path = log_config.get('file_path')
    
    # Ensure log directory exists
    if log_file_path:
        log_dir = os.path.dirname(log_file_path)
        if log_dir and not os.path.exists(log_dir):
            try:
                os.makedirs(log_dir)
            except OSError as e:
                print(f"CRITICAL: Could not create log directory {log_dir}: {e}")
                log_file_path = None # Disable file logging if dir create fails

    max_bytes = log_config.get('max_file_size_mb', 10) * 1024 * 1024
    backup_count = log_config.get('backup_count', 3)
    
    handlers = [
        # Console Handler (always stream to stdout/stderr for Docker logs)
        logging.StreamHandler(sys.stdout)
    ]
    
    if log_file_path:
        try:
            file_handler = RotatingFileHandler(
                log_file_path,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            )
            handlers.append(file_handler)
        except Exception as e:
            # This is critical if we rely on file logging for persistence
            print(f"CRITICAL: Could not set up file logging at {log_file_path}: {e}")
            
    # Remove any existing handlers before basicConfig call
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        handlers=handlers
    )
    
    logging.info(f"Logging initialized at level: {log_level.upper()}")

# =============================================================
# 2. ALERT THRESHOLD CHECKER
# =============================================================

def get_param_type_from_id(sensor_id: str) -> str:
    """Extracts the base parameter type (e.g., pH, EC, Temp) from the full sensor ID."""
    # Sensor IDs are typically structured like zone_tank_type (e.g., zone_b_ph, za_t1_lvl)
    # The parameter type is always the last segment.
    
    # Use a dictionary mapping to handle known types for reliable lookup, 
    # but fall back to the last segment if needed.
    known_types = {
        'ph': 'PH', 'ec': 'EC', 'temp': 'TEMPERATURE', 
        'do': 'DO', 'lvl': 'WATER_LEVEL', 'turb': 'TURBIDITY',
        'level': 'WATER_LEVEL', 'temperature': 'TEMPERATURE',
        'turbidity': 'TURBIDITY'
    }
    
    # Split by underscore and get the last part
    last_segment = sensor_id.split('_')[-1].lower()
    
    # Map to the uppercase key used in config.json alert thresholds
    if last_segment in known_types:
        return known_types[last_segment]
    
    # Handle cases like 'temperature' that might be split from a longer ID, 
    # or match the config keys if the ID is just the type.
    return last_segment.upper()

def check_and_raise_alerts(readings_data: Dict[str, Any]):
    """
    Compares current readings against configured thresholds and saves alerts.
    Handles None values as SENSOR_DISCONNECTED SYSTEM_FAULT.
    Handles out-of-bounds saturation values (e.g., 2000 for EC).
    """
    if not db_manager or not config:
        logging.error("Alert check failed: Database or Config manager not initialized.")
        return

    thresholds = config.get_alert_thresholds()
    alerts_triggered = 0

    # readings_data['readings'] contains cleaned values (float or None for disconnect)
    for sensor_id, value in readings_data.get('readings', {}).items():
        param_type = get_param_type_from_id(sensor_id)
        param_thresholds = thresholds.get(param_type)

        if not param_thresholds:
            # This is common for sensors like Turbidity that might not be in the config key name
            # logging.debug(f"No threshold configuration found for parameter type: {param_type} (Sensor: {sensor_id})")
            continue
        
        alert_type = None
        message = ""
        
        min_warn = param_thresholds.get('min')
        max_warn = param_thresholds.get('max')
        min_crit = param_thresholds.get('critical_min')
        max_crit = param_thresholds.get('critical_max')
        unit = param_thresholds.get('unit', '')

        if value is None or value == -127.0: # -127.0 is the DS18B20 error code
            # SYSTEM_FAULT: Sensor disconnection or error
            alert_type = "SYSTEM_FAULT"
            value_display = value if value is not None else "NULL"
            message = f"SYSTEM_FAULT: Sensor '{sensor_id}' reported error value {value_display}."
            
        elif value is not None:
            # Check for CRITICAL thresholds
            if min_crit is not None and value < min_crit:
                alert_type = "CRITICAL"
                message = f"CRITICAL: {sensor_id} value {value:.2f}{unit} is below CRITICAL minimum {min_crit}{unit}."
            elif max_crit is not None and value > max_crit:
                alert_type = "CRITICAL"
                message = f"CRITICAL: {sensor_id} value {value:.2f}{unit} is above CRITICAL maximum {max_crit}{unit}."
            
            # Check for WARNING thresholds if not already CRITICAL
            elif alert_type is None:
                if min_warn is not None and value < min_warn:
                    alert_type = "WARNING"
                    message = f"WARNING: {sensor_id} value {value:.2f}{unit} is below optimal minimum {min_warn}{unit}."
                elif max_warn is not None and value > max_warn:
                    alert_type = "WARNING"
                    message = f"WARNING: {sensor_id} value {value:.2f}{unit} is above optimal maximum {max_warn}{unit}."

        if alert_type:
            alert_data = {
                "sensor_id": sensor_id,
                "alert_type": alert_type,
                "value": value if value is not None else -999.0, # Use placeholder for null/error values
                "threshold_min": min_warn,
                "threshold_max": max_warn,
                "message": message
            }
            db_manager.save_alert(alert_data)
            alerts_triggered += 1

    if alerts_triggered > 0:
        logging.warning(f"Total {alerts_triggered} new alerts recorded.")

# =============================================================
# 3. MAIN SCHEDULER LOOP
# =============================================================

def scheduler_loop():
    """
    The main thread loop responsible for reading data, saving, and checking alerts.
    This thread is managed by the main function and runs independently.
    """
    global config, db_manager, sensor_manager
    logging.info("Scheduler started.")
    
    # Initial read interval might be slow until config loads, use a default safety value
    read_interval = config.get_reading_interval() if config else 60
    
    # Run data retention policy check hourly (3600 seconds)
    last_maintenance_time = time.time()
    maintenance_interval = 3600 # 1 hour

    while True:
        try:
            start_time = time.time()
            
            # Update interval in case config was hot-reloaded
            if config:
                read_interval = config.get_reading_interval()
            
            # 1. Acquire Data from Arduino via SensorManager
            readings_data = sensor_manager.get_latest_readings()
            
            if readings_data:
                # 2. Save Data to Database
                db_manager.save_readings(readings_data['readings'])
                
                # 3. Check for Alerts
                check_and_raise_alerts(readings_data)

            else:
                logging.error("Failed to acquire valid readings from Arduino.")
                
            # 4. Run Maintenance (Data Retention)
            if (time.time() - last_maintenance_time) >= maintenance_interval:
                db_manager.cleanup_old_data()
                last_maintenance_time = time.time()
                
            # 5. Sleep for the remainder of the interval
            elapsed_time = time.time() - start_time
            sleep_time = read_interval - elapsed_time
            
            if sleep_time > 0:
                time.sleep(sleep_time)
            elif elapsed_time > read_interval:
                logging.warning(f"Scheduler loop took {elapsed_time:.2f}s, exceeding interval of {read_interval}s. Consider adjusting interval or optimizing sensor read process.")
        
        except Exception as e:
            logging.error(f"Error in scheduler loop: {e}. Attempting to continue in {read_interval}s.")
            time.sleep(read_interval) # Wait before trying again

# =============================================================
# 4. FLASK SERVER STARTER
# =============================================================

def start_flask_server():
    """
    Initializes and starts the Flask server.
    The Flask app object is created and configured with the global managers.
    """
    global config, db_manager, sensor_manager
    
    if not config:
        logging.critical("Cannot start Flask server: Configuration not loaded.")
        return

    try:
        # Create Flask app instance using the factory
        app = create_app(config, db_manager, sensor_manager)
        
        host = config.get_all().get('web_server', {}).get('host', '0.0.0.0')
        port = config.get_all().get('web_server', {}).get('port', 5000)
        # Note: Debug mode is usually set to False in Docker/Production (FLASK_DEBUG=0 in docker-compose)
        # We rely on Flask's run params or app.config settings
        debug_mode = app.config.get('DEBUG', False)
        
        logging.info(f"Starting Flask server (API/Dashboard) at http://{host}:{port}/")
        
        # When running via `python app/main.py`, app.run() is typically blocking.
        # This keeps the main thread busy, so no need for the while True loop in main().
        app.run(host=host, port=port, debug=debug_mode, use_reloader=False) 
        
    except Exception as e:
        logging.critical(f"FATAL: Flask server startup failed. Error: {e}")
        # The main thread will exit if this fails.

# =============================================================
# 5. APPLICATION ENTRY POINT
# =============================================================

def main():
    """
    Initializes system components and starts the main threads.
    """
    global config, db_manager, sensor_manager
    
    # --- Initialization Step 1: Configuration ---
    try:
        # Load config from the path where Docker volume mounts it
        # We assume the config file is in the root of the Docker WORKDIR (/app)
        config = ConfigLoader('config.json') 
        setup_logging(config.get_logging_level())
        logging.info("Application Initialization starting...")
    except Exception as e:
        print(f"FATAL: Configuration setup failed. Exiting. Error: {e}")
        sys.exit(1) # Use sys.exit(1) for cleaner shutdown

    # --- Initialization Step 2: Database ---
    try:
        db_manager = DatabaseManager(config)
        # db_manager.init_db() is called in constructor
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.critical(f"FATAL: Database initialization failed. Exiting. Error: {e}")
        sys.exit(1)
        
    # --- Initialization Step 3: Sensor Manager (Serial) ---
    try:
        sensor_manager = SensorManager(config)
        if not sensor_manager.serial_handler.is_connected:
             # Log an error, but don't exit. The scheduler will try to reconnect.
             logging.error("Serial connection failed during startup. Scheduler will attempt reconnect.")
        else:
            logging.info("Serial connection established successfully.")
    except Exception as e:
        logging.critical(f"FATAL: Sensor manager initialization failed. Exiting. Error: {e}")
        sys.exit(1)

    # --- Initialization Step 4: Start Threads ---
    
    # 1. Start the data acquisition scheduler thread (Daemon)
    scheduler_thread = threading.Thread(target=scheduler_loop, name="SchedulerThread")
    scheduler_thread.daemon = True
    scheduler_thread.start()
    logging.info("Data acquisition scheduler thread started.")
    
    # 2. Start the web server thread (Blocking call on the main thread)
    try:
        start_flask_server()
    except KeyboardInterrupt:
        logging.info("Flask server received interrupt signal.")
    except Exception as e:
        logging.critical(f"Flask server exited unexpectedly: {e}")
    finally:
        logging.info("Aquaponics Smart Farm stopped.")

if __name__ == '__main__':
    main()