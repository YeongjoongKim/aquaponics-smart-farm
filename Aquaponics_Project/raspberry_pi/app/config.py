# -------------------------------------------------------------
# config.py
# Configuration Loader and Manager
# Responsible for: Loading and managing system settings from
#                  config.json, including hardware, zones, and
#                  alert thresholds.
# -------------------------------------------------------------

import json
from typing import Dict, Any, List, Optional
import os
import logging
import copy # For deep copying configuration segments

# Initialize logger for this module before main logging is fully set up
module_logger = logging.getLogger(__name__)
module_logger.setLevel(logging.INFO) # Default to INFO until main overrides

# Configuration file name (mounted via Docker volume)
CONFIG_FILE = 'config.json'

class ConfigLoader:
    """
    Loads, validates, and provides access to system configuration.
    Supports dynamic updates of certain parameters (Hot-Reload).
    """
    
    def __init__(self, config_path: str = CONFIG_FILE):
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> bool:
        """
        Loads the configuration from the JSON file path.
        Returns True if successful, False otherwise.
        """
        
        # --- Path Resolution for Debug/Test ---
        # In Docker, self.config_path ('config.json') is mapped to /app/config.json
        # For local testing, we need relative path adjustment.
        resolved_path = self.config_path
        if not os.path.exists(resolved_path):
            # Attempt a common fallback path if running from inside the 'app' directory
            fallback_path = os.path.join(os.path.dirname(__file__), '..', resolved_path)
            if os.path.exists(fallback_path):
                resolved_path = fallback_path
            else:
                module_logger.critical(f"Configuration file not found at expected paths: {self.config_path} or {fallback_path}")
                return False

        try:
            with open(resolved_path, 'r', encoding='utf-8') as f:
                # Use standard json load (comments in json are not supported by standard lib, 
                # ensure config.json is valid standard JSON)
                self._config = json.load(f)
            
            self.config_path = resolved_path # Store the successfully resolved path
            module_logger.info(f"Configuration loaded successfully from {self.config_path}")
            
            # Optional: Basic structure validation
            if 'hardware' not in self._config or 'zones' not in self._config:
                module_logger.warning("Configuration is missing 'hardware' or 'zones' section.")
            
            return True
            
        except json.JSONDecodeError as e:
            module_logger.critical(f"Failed to decode JSON file ({resolved_path}): {e}")
            return False
        except Exception as e:
            module_logger.critical(f"Failed to read configuration file ({resolved_path}): {e}")
            return False

    def get_all(self) -> Dict[str, Any]:
        """
        Returns a deep copy of the entire configuration dictionary to prevent external mutation.
        """
        return copy.deepcopy(self._config)

    def update_config(self, new_settings: Dict[str, Any]) -> bool:
        """
        Updates parts of the configuration with new settings (Hot-Reload).
        Only non-critical sections like 'monitoring' or 'logging' should be updated without restart.
        The changes are saved back to the file on disk.
        """
        if not new_settings:
            return False

        # Recursively update the configuration dictionary
        def recursive_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict) and k in d:
                    # Recursively update if both are dictionaries
                    d[k] = recursive_update(d.get(k, {}), v)
                else:
                    # Otherwise, set the value directly
                    d[k] = v
            return d

        recursive_update(self._config, new_settings)
        
        # Save the updated config back to the file
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2)
            module_logger.info("Configuration file updated on disk.")
            return True
        except Exception as e:
            module_logger.error(f"Could not save updated config to disk: {e}")
            return False
            
    # =========================================================
    # HARDWARE & CONNECTION ACCESSORS
    # =========================================================

    def get_hardware_port(self) -> str:
        """
        Returns the serial port path (e.g., /dev/ttyUSB0).
        """
        return self._config.get('hardware', {}).get('connection', {}).get('port', '/dev/ttyUSB0')

    def get_hardware_baud_rate(self) -> int:
        """
        Returns the serial baud rate (e.g., 115200).
        """
        return self._config.get('hardware', {}).get('connection', {}).get('baud_rate', 115200)

    def get_hardware_timeout(self) -> int:
        """
        Returns the serial connection timeout in seconds.
        """
        return self._config.get('hardware', {}).get('connection', {}).get('timeout', 2)
    
    def is_simulation_enabled(self) -> bool:
        """
        Checks if hardware simulation mode is enabled.
        """
        return self._config.get('hardware', {}).get('enable_simulation', False)

    def get_sensor_mapping(self) -> Dict[str, Any]:
        """
        Aggregates and returns a flat dictionary of all sensors across all zones.
        This is crucial for SensorManager initialization and ID lookups.
        
        Format Key: {tank_id}_{sensor_type}
        Example: 'filter_tank_1_ph', 'nutrient_tank_1_ec', 'zone_cultivation_1_start_ec'
        """
        mapping: Dict[str, Any] = {}
        zones = self._config.get('zones', {})

        # 1. Filtered Tanks (Zone A)
        # Structure: List of tank objects
        for tank in zones.get('filtered_tanks', []):
            tank_id = tank['id'] # e.g., 'filter_tank_1'
            for sensor in tank.get('sensors', []):
                sensor_type = sensor['type']
                # ID format: 'filter_tank_1_ph'
                sensor_id = f"{tank_id}_{sensor_type}"
                mapping[sensor_id] = sensor
        
        # 2. Nutrient Tanks (Zone B)
        # Structure: List of tank objects (Updated from single object)
        # Note: Handling both 'nutrient_tanks' (list) and legacy 'nutrient_tank' (dict) for safety
        n_tanks = zones.get('nutrient_tanks', [])
        if not n_tanks and 'nutrient_tank' in zones:
             n_tanks = [zones['nutrient_tank']]

        for tank in n_tanks:
            tank_id = tank['id'] # e.g., 'nutrient_tank_1'
            for sensor in tank.get('sensors', []):
                sensor_type = sensor['type']
                # ID format: 'nutrient_tank_1_ph'
                sensor_id = f"{tank_id}_{sensor_type}"
                mapping[sensor_id] = sensor
            
        # 3. Cultivation Line (Zone C) - Gradient
        cultivation_line = zones.get('cultivation_line', {})
        line_id = cultivation_line.get('id', 'zone_cultivation_1')
        
        for point, sensors in cultivation_line.get('points', {}).items():
            for sensor in sensors:
                sensor_type = sensor['type']
                # ID format: 'zone_cultivation_1_start_ec'
                sensor_id = f"{line_id}_{point}_{sensor_type}"
                mapping[sensor_id] = sensor

        return mapping

    # =========================================================
    # MONITORING & ALERT ACCESSORS
    # =========================================================

    def get_reading_interval(self) -> int:
        """
        Returns the data reading interval in seconds.
        """
        return self._config.get('monitoring', {}).get('reading_interval_seconds', 60)

    def get_averaging_window(self) -> int:
        """
        Returns the averaging window size for noise reduction.
        """
        return self._config.get('monitoring', {}).get('averaging_window', 10)

    def get_alert_thresholds(self) -> Dict[str, Any]:
        """
        Returns the entire alert_thresholds dictionary. Keys are capitalized (e.g., 'PH', 'EC').
        """
        # Ensure keys are consistently capitalized to match the logic in main.py
        thresholds = self._config.get('monitoring', {}).get('alert_thresholds', {})
        return {k.upper(): v for k, v in thresholds.items()}

    def get_threshold(self, parameter: str) -> Optional[Dict[str, float]]:
        """
        Returns thresholds for a specific parameter (e.g., 'pH', 'EC').
        """
        return self.get_alert_thresholds().get(parameter.upper())

    # =========================================================
    # DATABASE ACCESSORS
    # =========================================================
    
    def get_db_path(self) -> str:
        """
        Returns the path to the SQLite database file.
        """
        return self._config.get('database', {}).get('path', '/app/data/aquaponics.db')
        
    def get_db_retention_policy(self) -> Dict[str, int]:
        """
        Returns the retention policy for raw data and logs (in days).
        """
        return self._config.get('database', {}).get('retention_policy', {
            "raw_data_days": 90,
            "logs_days": 30
        })

    # =========================================================
    # SYSTEM & LOGGING ACCESSORS
    # =========================================================
    
    def get_site_info(self) -> Dict[str, str]:
        """
        Returns site information (name, location, version).
        """
        return self._config.get('site_info', {})
        
    def get_logging_level(self) -> str:
        """
        Returns the logging verbosity level (e.g., 'INFO', 'DEBUG').
        """
        return self._config.get('logging', {}).get('level', 'INFO').upper()
    
    def is_debug_mode(self) -> bool:
        """
        Checks if the logging level is set to DEBUG.
        """
        return self.get_logging_level() == 'DEBUG'
        
# Example usage (for testing)
if __name__ == '__main__':
    # Adjust path if running in the root directory for demonstration
    # Assumes config.json is one level up from the current directory ('app')
    config = ConfigLoader(os.path.join('..', CONFIG_FILE)) 

    print("\n--- Configuration Check ---")
    print(f"Site Name: {config.get_site_info().get('name')}")
    print(f"Serial Port: {config.get_hardware_port()}")
    print(f"Reading Interval: {config.get_reading_interval()} seconds")
    
    # Check EC threshold
    ec_thresholds = config.get_threshold('EC')
    if ec_thresholds:
        print(f"EC Critical Max: {ec_thresholds.get('critical_max')} {ec_thresholds.get('unit')} (HW Limit)")
    
    # Check Sensor Mapping (New Feature)
    print("\n--- Sensor Mapping Check ---")
    mapping = config.get_sensor_mapping()
    print(f"Total Sensors Mapped: {len(mapping)}")
    # Verify new ID formats
    print(f"Zone C Start EC Pin: {mapping.get('zone_cultivation_1_start_ec', {}).get('pin')}")
    print(f"Zone B Nutrient 1 pH Pin: {mapping.get('nutrient_tank_1_ph', {}).get('pin')}")
    
    # Test Hot-Reload
    print("\n--- Testing Hot-Reload ---")
    new_settings = {
        "monitoring": {
            "reading_interval_seconds": 30,
            "alert_thresholds": {
                "DO": {
                    "min": 4.5
                }
            }
        }
    }
    
    initial_do_min = config.get_threshold('DO').get('min') if config.get_threshold('DO') else 'N/A'
    print(f"Initial DO Min: {initial_do_min}")
    
    config.update_config(new_settings)
    
    print(f"New Reading Interval: {config.get_reading_interval()}")
    print(f"New DO Min: {config.get_threshold('DO').get('min')}")