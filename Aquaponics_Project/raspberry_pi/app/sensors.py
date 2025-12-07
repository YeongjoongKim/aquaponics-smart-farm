# -------------------------------------------------------------
# sensors.py
# Sensor Manager and Data Parser
# Responsible for: 
# 1. Coordinating sensor data retrieval via SerialHandler.
# 2. Parsing raw JSON data from Arduino into a structured format.
# 3. Validating sensor values (e.g., EC saturation, error codes).
# 4. Translating calibration requests into Arduino commands.
# -------------------------------------------------------------

import json
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime

# Import modules from the current package
from .config import ConfigLoader 
# [MODIFIED] Import the dedicated SerialHandler module
from .serial_handler import SerialHandler 

# --- Constants based on configuration files ---
# EC Sensor maximum physical limit (for error checking)
EC_SATURATION_LIMIT = 2000.0 
EC_SATURATION_ALERT_VALUE = 2000.0 # Value to return when saturation is detected

# Initialize logger for this module
logger = logging.getLogger(__name__)

class AquaponicsParser:
    """
    Parses the raw JSON data from Arduino and structures it into a
    standardized format for the API and Database.
    """
    def __init__(self, config: ConfigLoader):
        self.config = config
        # Mapping Arduino short keys (arduino.ino) to Database/API full keys (API.md/config.json)
        # Note: Zone B is now Multi-Tank (t1, t2, t3) similar to Zone A
        self.key_map = {
            'zA': {'t1': 'filter_tank_1', 't2': 'filter_tank_2', 't3': 'filter_tank_3'},
            'zB': {'t1': 'nutrient_tank_1', 't2': 'nutrient_tank_2', 't3': 'nutrient_tank_3'},
            # Zone C maps short keys to the full sensor ID segment
            'zC_keys': {'s': 'start', 'm': 'middle', 'e': 'end'}, 
            's_keys': {'ph': 'ph', 'tb': 'turbidity', 'lv': 'water_level', 'tp': 'temperature', 
                       'ec': 'ec', 'do': 'do'} # Unified short keys for parameters
        }
    
    def parse(self, raw_json_str: str) -> Optional[Dict[str, Any]]:
        """
        Parses the Arduino JSON string into a structured dictionary.
        """
        try:
            raw_data = json.loads(raw_json_str)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode JSON: {e}. Raw data: {raw_json_str[:50]}...")
            return None
        
        # Initialize the standardized output structure
        system_state: Dict[str, Any] = {
            "timestamp": datetime.now().isoformat(),
            "status": raw_data.get('st', 'OK'),
            "readings": {} # Flattened dictionary of {sensor_id: value}
        }
        
        # --- Data Mapping Logic ---
        
        # 1. Zone A: Filtered Water Tanks (t1, t2, t3)
        if 'zA' in raw_data:
            for tank_short_key, tank_full_key in self.key_map['zA'].items():
                tank_data = raw_data['zA'].get(tank_short_key, {})
                for arduino_key, db_key in self.key_map['s_keys'].items():
                    if arduino_key in tank_data:
                        # Full ID: 'filter_tank_1_ph'
                        sensor_id = f"{tank_full_key}_{db_key}"
                        system_state['readings'][sensor_id] = self._validate_and_normalize(db_key, tank_data[arduino_key])
                        
        # 2. Zone B: Nutrient Tanks (t1, t2, t3) - [UPDATED for Multi-Tank]
        if 'zB' in raw_data:
            for tank_short_key, tank_full_key in self.key_map['zB'].items():
                tank_data = raw_data['zB'].get(tank_short_key, {})
                for arduino_key, db_key in self.key_map['s_keys'].items():
                    if arduino_key in tank_data:
                        # Full ID: 'nutrient_tank_1_ph'
                        sensor_id = f"{tank_full_key}_{db_key}"
                        system_state['readings'][sensor_id] = self._validate_and_normalize(db_key, tank_data[arduino_key])
                    
        # 3. Zone C: Cultivation Line (EC Gradient)
        if 'zC' in raw_data:
            zone_data = raw_data['zC']
            zone_full_key = 'zone_cultivation_1' # As per config/API structure
            
            # Note: Zone C only sends EC readings ('s', 'm', 'e')
            for short_key, point_key in self.key_map['zC_keys'].items():
                if short_key in zone_data:
                    # Full ID: 'zone_cultivation_1_start_ec'
                    # Format must match config.py: {line_id}_{point}_{sensor_type}
                    sensor_id = f"{zone_full_key}_{point_key}_ec"
                    # All readings here are EC
                    system_state['readings'][sensor_id] = self._validate_and_normalize('ec', zone_data[short_key])

        return system_state

    def _validate_and_normalize(self, sensor_type: str, value: Any) -> Any:
        """
        Performs basic validation on numerical values.
        Converts Arduino error codes (-1, -127) to None for database/alert logic.
        """
        if not isinstance(value, (int, float)):
            logger.debug(f"Non-numeric value detected for {sensor_type}: {value}")
            return None

        # Check for Arduino error codes (based on sensor.h/arduino.ino logic)
        if value < 0:
            # -1.0 for pH/Analog Disconnected, -127.0 for Temp Disconnected
            if value == -1.0 or value == -127.0: 
                # Upstream (main.py) will handle None as SYSTEM_FAULT alert
                return None 

        # Specific sensor hardware checks (EC saturation)
        if sensor_type.lower() == 'ec' and value >= EC_SATURATION_LIMIT:
            logger.warning(f"EC reading {value} >= {EC_SATURATION_LIMIT} uS/cm (Sensor Saturation).")
            # Retain the saturation value, allowing the alert system to flag it as CRITICAL
            return EC_SATURATION_ALERT_VALUE
            
        # Normalize float precision for consistency
        if isinstance(value, float):
            return round(value, 2)
            
        return value


class SensorManager:
    """
    High-level manager to coordinate serial communication and data parsing.
    This class is the main interface for the main.py scheduler.
    """
    # Mapping of sensor IDs (from config.json/API.md) to Arduino command targets (arduino.ino)
    # The IDs here must match the full, parsed IDs generated by AquaponicsParser
    # Updated to match arduino.ino command handlers (CALIB_ZA_T1_PH, etc.)
    ARDUINO_CMD_MAP = {
        # Zone A - Filter Tanks (filter_tank_X_ph/turbidity)
        'filter_tank_1_ph': 'CALIB_ZA_T1_PH', 'filter_tank_2_ph': 'CALIB_ZA_T2_PH', 'filter_tank_3_ph': 'CALIB_ZA_T3_PH',
        'filter_tank_1_turbidity': 'CALIB_ZA_T1_TURB', 'filter_tank_2_turbidity': 'CALIB_ZA_T2_TURB', 'filter_tank_3_turbidity': 'CALIB_ZA_T3_TURB',
        
        # Zone B - Nutrient Tanks (nutrient_tank_X_ph/ec/do)
        'nutrient_tank_1_ph': 'CALIB_ZB_T1_PH', 'nutrient_tank_2_ph': 'CALIB_ZB_T2_PH', 'nutrient_tank_3_ph': 'CALIB_ZB_T3_PH',
        'nutrient_tank_1_ec': 'CALIB_ZB_T1_EC', 'nutrient_tank_2_ec': 'CALIB_ZB_T2_EC', 'nutrient_tank_3_ec': 'CALIB_ZB_T3_EC',
        'nutrient_tank_1_do': 'CALIB_ZB_T1_DO', 'nutrient_tank_2_do': 'CALIB_ZB_T2_DO', 'nutrient_tank_3_do': 'CALIB_ZB_T3_DO',
        
        # Zone C - Cultivation Line (zone_cultivation_1_start/middle/end_ec)
        'zone_cultivation_1_start_ec': 'CALIB_ZC_START', 
        'zone_cultivation_1_middle_ec': 'CALIB_ZC_MID', 
        'zone_cultivation_1_end_ec': 'CALIB_ZC_END'
    }
    
    def __init__(self, config: ConfigLoader):
        self.config = config
        self.serial_handler = SerialHandler(config) # Use imported SerialHandler
        self.parser = AquaponicsParser(config)

    def get_latest_readings(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves and parses the latest structured sensor data.
        """
        # Try to reconnect if not connected
        if not self.serial_handler.is_connected:
            self.serial_handler.connect()
            if not self.serial_handler.is_connected:
                return None
                
        # Use the handler's read_line method
        raw_line = self.serial_handler.read_line()
        
        if not raw_line:
            return None

        readings = self.parser.parse(raw_line)

        if readings and self.config.is_debug_mode():
            logger.debug(f"Parsed Readings: {json.dumps(readings, indent=2)}")

        return readings

    def perform_calibration(self, sensor_id: str, calibration_type: str, points: Dict[str, Any]) -> Optional[str]:
        """
        Translates an API calibration request into a serial command and executes it.
        
        :param sensor_id: Full sensor ID (e.g., 'nutrient_tank_1_ph').
        :param calibration_type: '3-point', '1-point', 'baseline', or 'saturation'.
        :param points: Dictionary containing the raw ADC values for calibration.
        :return: Arduino's JSON response string (or error message if starts with ERROR:).
        """
        target = self.ARDUINO_CMD_MAP.get(sensor_id)
        if not target:
            logger.error(f"Unknown sensor ID for calibration: {sensor_id}")
            return f"ERROR: Unknown sensor ID for calibration: {sensor_id}"

        command = ""
        
        # --- PH CALIBRATION (3-Point: LOW, MID, HIGH) ---
        if calibration_type == '3-point' and 'CALIB_PH' in target: # Matches CALIB_ZA_T1_PH, CALIB_ZB_T1_PH, etc.
            point_map = {'low': 'LOW', 'mid': 'MID', 'high': 'HIGH'}
            for point_key, arduino_point in point_map.items():
                if point_key in points:
                    raw_val = points[point_key]
                    command = f"{target}:{arduino_point}:{raw_val:.1f}"
                    break
                    
        # --- EC CALIBRATION (1-Point: STD) ---
        elif calibration_type == '1-point' and 'CALIB_EC' in target: # Matches CALIB_ZB_T1_EC, CALIB_ZC_START, etc.
            if 'raw_adc' in points:
                raw_val = points['raw_adc']
                # Standard point for EC is often passed as STD param
                command = f"{target}:STD:{raw_val:.1f}"
            elif 'standard' in points: # Fallback key
                raw_val = points['standard']
                command = f"{target}:STD:{raw_val:.1f}"
            else:
                return "ERROR: EC Calibration requires 'raw_adc' (ADC value at 1413 uS/cm)."
                
        # --- TURBIDITY CALIBRATION (1-Point Baseline) ---
        elif calibration_type == 'baseline' and 'CALIB_TURB' in target:
            if 'raw_adc' in points:
                raw_val = points['raw_adc']
                # Turbidity just needs the raw value
                command = f"{target}:{raw_val:.1f}"
            elif 'clear' in points: # Fallback key
                raw_val = points['clear']
                command = f"{target}:{raw_val:.1f}"
            else:
                return "ERROR: Turbidity Calibration requires 'raw_adc' (ADC value in clear water)."
                
        # --- DO CALIBRATION (Simplified Span/Zero) ---
        elif calibration_type == 'saturation' and 'CALIB_DO' in target:
            if 'span_raw_adc' in points:
                raw_val = points['span_raw_adc']
                command = f"{target}:SPAN:{raw_val:.1f}" 
            elif 'zero_raw_adc' in points:
                raw_val = points['zero_raw_adc']
                command = f"{target}:ZERO:{raw_val:.1f}"
            elif 'span' in points: # Fallback key
                raw_val = points['span']
                command = f"{target}:SPAN:{raw_val:.1f}"
            else:
                return "ERROR: DO Calibration requires 'span_raw_adc' or 'zero_raw_adc' value."
        
        # --- RESET COMMAND ---
        elif calibration_type == 'reset':
            command = "RESET"

        if not command:
            return f"ERROR: Could not format a valid command for type {calibration_type} and sensor {sensor_id} from provided points."

        # Send command and parse the JSON response from SerialHandler
        response_dict = self.serial_handler.send_command(command)

        if response_dict and 'error' in response_dict:
            # SerialHandler failed to connect or failed to receive valid JSON
            return f"ERROR: {response_dict['error']}"
        elif response_dict and 'msg' in response_dict:
            # Arduino returned a success message
            return f"SUCCESS: {response_dict['msg']}"
        
        return "ERROR: Unknown response during command execution."