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
from .alerts import AlertManager

# =============================================================
# 1. CONFIGURATION AND LOGGING SETUP
# =============================================================

# Global references
# These references will be passed to the Flask application context
config: Optional[ConfigLoader] = None
db_manager: Optional[DatabaseManager] = None
sensor_manager: Optional[SensorManager] = None
alert_manager: Optional[AlertManager] = None

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
# 3. MAIN SCHEDULER LOOP
# =============================================================

def scheduler_loop():
    """
    The main thread loop responsible for reading data, saving, and checking alerts.
    This thread is managed by the main function and runs independently.
    """
    global config, db_manager, sensor_manager, alert_manager
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
                if alert_manager:
                    alert_manager.check_readings(readings_data)

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
    시스템 컴포넌트를 순서대로 초기화하고 메인 스레드를 시작합니다.
    """
    global config, db_manager, sensor_manager, alert_manager
    
    # [Step 1] 설정 로드
    try:
        config = ConfigLoader('config.json') 
        setup_logging(config.get_logging_level())
        logging.info("Application Initialization starting...")
    except Exception as e:
        print(f"FATAL: Config setup failed. {e}")
        sys.exit(1)

    # [Step 2] 데이터베이스 초기화
    try:
        db_manager = DatabaseManager(config)
        logging.info("Database initialized successfully.")
    except Exception as e:
        logging.critical(f"FATAL: Database setup failed. {e}")
        sys.exit(1)
        
    # [Step 3] 센서 매니저 초기화 (시리얼 연결)
    try:
        sensor_manager = SensorManager(config)
        if sensor_manager.serial_handler.is_connected:
            logging.info("Serial connection established.")
        else:
            logging.error("Serial connection failed. Scheduler will retry.")
    except Exception as e:
        logging.critical(f"FATAL: Sensor manager setup failed. {e}")
        sys.exit(1)

    # [Step 4] 알림 매니저 초기화
    # 반드시 DB와 Config가 준비된 후에 초기화해야 합니다.
    try:
        alert_manager = AlertManager(config, db_manager)
        logging.info("Alert Manager initialized successfully.")
    except Exception as e:
        logging.critical(f"FATAL: Alert manager setup failed. {e}")
        sys.exit(1)

    # [Step 5] 스레드 및 서버 시작
    
    # 1. 데이터 수집 스케줄러 시작 (백그라운드 데몬)
    scheduler_thread = threading.Thread(target=scheduler_loop, name="SchedulerThread")
    scheduler_thread.daemon = True
    scheduler_thread.start()
    logging.info("Data acquisition scheduler thread started.")
    
    # 2. 웹 서버 시작 (메인 스레드 블로킹)
    try:
        start_flask_server()
    except KeyboardInterrupt:
        logging.info("Flask server stopped by user.")
    except Exception as e:
        logging.critical(f"Flask server crashed: {e}")
    finally:
        logging.info("System shutdown complete.")

if __name__ == '__main__':
    main()