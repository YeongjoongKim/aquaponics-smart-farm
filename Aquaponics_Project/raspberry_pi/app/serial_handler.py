# -------------------------------------------------------------
# serial_handler.py
# Serial Communication Handler (Arduino Interface)
# Responsible for: 
# 1. Establishing and maintaining the serial connection.
# 2. Reading raw lines of data (JSON) from the Arduino.
# 3. Sending commands for calibration.
# -------------------------------------------------------------

import serial
import time
import json
import logging
from typing import Optional, Dict

# Import configuration loader
from .config import ConfigLoader

logger = logging.getLogger(__name__)

class SerialHandler:
    """
    Manages the physical serial connection to the Arduino Mega.
    """
    def __init__(self, config: ConfigLoader):
        """
        Initializes the serial connection parameters from ConfigLoader.
        """
        self.config = config
        self.port = self.config.get_hardware_port() # e.g., /dev/ttyUSB0
        self.baud_rate = self.config.get_hardware_baud_rate() # e.g., 115200
        self.timeout = self.config.get_hardware_timeout() # e.g., 2 seconds
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        
        # Initial attempt to connect
        self.connect()

    def connect(self) -> bool:
        """
        Attempts to establish the serial connection.
        If already connected, returns True.
        """
        if self.ser and self.ser.is_open:
            return True
            
        try:
            # Close any existing connection first
            if self.ser:
                self.ser.close()
            
            self.ser = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=self.timeout
            )
            # Wait for Arduino to reset/stabilize (critical step)
            time.sleep(2) 
            self.is_connected = self.ser.is_open
            
            if self.is_connected:
                logger.info(f"Serial connection established on {self.port} at {self.baud_rate}.")
            else:
                logger.error(f"Serial connection attempt failed (is_open=False) on {self.port}.")
            return self.is_connected
            
        except serial.SerialException as e:
            self.is_connected = False
            logger.critical(f"Serial connection failed for {self.port}: {e}. Check /dev/ttyUSB0 permissions (dialout group) or mapping.")
            return False

    def disconnect(self):
        """
        Closes the serial connection.
        """
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
            logger.info("Serial connection closed.")

    def read_line(self) -> Optional[str]:
        """
        Reads one line of JSON data from the serial port.
        Automatically attempts to reconnect if not connected.
        """
        if not self.is_connected and not self.connect():
            return None
        
        try:
            # Read all available bytes until a newline character
            # Check if data is waiting to avoid blocking read if possible (though timeout handles it)
            if self.ser.in_waiting > 0:
                # [Optimization] Use errors='ignore' to prevent crashes from noisy serial data
                line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                
                # Validation: Must start with '{' and end with '}'
                if line.startswith('{') and line.endswith('}'):
                    if self.config.is_debug_mode():
                        logger.debug(f"RAW_SERIAL: {line[:100]}...")
                    return line
                
                if line and self.config.is_debug_mode():
                    logger.debug(f"Discarded non-JSON data: {line[:50]}...")
            
            return None
                
        except serial.SerialTimeoutException:
            # SENSOR_TIMEOUT scenario
            if self.config.is_debug_mode():
                logger.debug("Serial read timeout detected (Arduino unresponsive/data gap).")
            return None
        except Exception as e:
            # Handle unexpected connection loss
            logger.error(f"Reading failed, attempting reconnect: {e}")
            self.is_connected = False
            return None

    def send_command(self, command: str) -> Optional[Dict[str, str]]:
        """
        Sends a command string to the Arduino (e.g., CALIB_PH_B:MID:350) 
        and awaits a confirmation response.
        
        :returns: Dictionary with 'msg' or 'error' key.
        """
        if not self.is_connected and not self.connect():
            return {"error": "Serial port not connected, cannot send command."}
            
        try:
            # Clear input buffer before sending a command to ensure we read the response, not old data
            self.ser.reset_input_buffer()
                
            # Arduino expects a newline
            self.ser.write((command + '\n').encode('utf-8'))
            logger.info(f"Sent command: {command}")
            
            # Wait briefly for the Arduino to process and send a JSON response (e.g., {"msg":"PH Saved"})
            # Adjust sleep based on Arduino processing time
            time.sleep(0.5) 
            
            # Read response line
            # We use a loop to retry reading a few times in case of latency
            response_line = None
            for _ in range(3):
                if self.ser.in_waiting > 0:
                    # [Optimization] Use errors='ignore' here as well
                    response_line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if response_line.startswith('{'):
                        break
                time.sleep(0.1)
            
            if response_line:
                try:
                    # Arduino response format is {"msg":"PH Saved"}
                    return json.loads(response_line)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON response from Arduino: {response_line}")
                    return {"error": f"Invalid JSON response from Arduino: {response_line}"}
            else:
                return {"error": "No valid response received from Arduino after command."}
                
        except Exception as e:
            logger.error(f"Failed to send command: {e}")
            self.is_connected = False
            return {"error": f"Failed to send command due to serial error: {e}"}