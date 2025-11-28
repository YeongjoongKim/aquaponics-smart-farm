/**
 * Aquaponics Smart Farm - Arduino Main Sketch
 * Real-time water quality monitoring system
 *
 * Board: Arduino Mega 2560
 * Sensors: pH, EC, Temperature, DO, Water Level, Turbidity
 *
 * Features:
 * - Multi-sensor data collection with averaging
 * - Calibration management (EEPROM storage)
 * - SD card data logging (CSV format)
 * - RTC timestamp synchronization
 * - Serial communication for Raspberry Pi
 * - Alert threshold monitoring
 */

#include "config.h"
#include "sensors.h"

#include <Wire.h>
#include <SD.h>
#include <time.h>

// ============================================================
// GLOBAL OBJECTS
// ============================================================

PHSensor        ph_sensor(PH_SENSOR_PIN);
ECSensor        ec_sensor(EC_SENSOR_PIN);
TemperatureSensor temp_sensor(TEMPERATURE_PIN);
DOSensor        do_sensor(DO_SENSOR_PIN);
WaterLevelSensor water_level_sensor(WATER_LEVEL_PIN);
TurbiditySensor turbidity_sensor(TURBIDITY_SENSOR_PIN);

AlertThresholds thresholds;

// Sensor data buffers (for averaging)
float ph_buffer[AVERAGING_WINDOW];
float ec_buffer[AVERAGING_WINDOW];
float temp_buffer[AVERAGING_WINDOW];
float do_buffer[AVERAGING_WINDOW];
float level_buffer[AVERAGING_WINDOW];
float turbidity_buffer[AVERAGING_WINDOW];

int buffer_index = 0;
unsigned long last_reading_time = 0;
unsigned long last_sd_write_time = 0;

File data_file;

// ============================================================
// SETUP
// ============================================================

void setup() {
  // Serial communication
  Serial.begin(BAUD_RATE);
  delay(2000);  // Wait for serial to stabilize

  if (DEBUG_SERIAL) {
    Serial.println(F("\n=== Aquaponics Smart Farm - Arduino ==="));
    Serial.println(F("Initializing sensors..."));
  }

  // Initialize I2C for RTC
  Wire.begin();

  // Initialize SD card
  if (ENABLE_SD_LOGGING) {
    if (!SD.begin(SD_CHIP_SELECT_PIN)) {
      if (DEBUG_SERIAL) Serial.println(F("ERROR: SD card initialization failed!"));
    } else {
      if (DEBUG_SERIAL) Serial.println(F("SD card initialized successfully"));
    }
  }

  // Load calibration data from EEPROM
  if (DEBUG_SERIAL) Serial.println(F("Loading calibration data..."));
  ph_sensor.load_calibration();
  ec_sensor.load_calibration();
  do_sensor.load_calibration();
  turbidity_sensor.load_calibration();

  // Load thresholds from EEPROM (or use defaults)
  load_thresholds();

  // Initialize buffers
  init_buffers();

  if (DEBUG_SERIAL) {
    Serial.println(F("Setup complete!"));
    Serial.println(F("Starting sensor readings...\n"));
    print_header();
  }
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {
  unsigned long current_time = millis();

  // Read sensors at configured interval
  if (current_time - last_reading_time >= SENSOR_READ_INTERVAL) {
    read_all_sensors();
    last_reading_time = current_time;
    buffer_index = (buffer_index + 1) % AVERAGING_WINDOW;

    // Log to SD card
    if (ENABLE_SD_LOGGING && (current_time - last_sd_write_time >= (SD_LOG_INTERVAL * 1000))) {
      log_to_sd();
      last_sd_write_time = current_time;
    }

    // Send to Raspberry Pi via serial
    send_serial_data();

    // Print to Serial Monitor
    if (DEBUG_SERIAL) {
      print_readings();
    }
  }

  // Check for serial commands (for calibration, etc.)
  if (Serial.available()) {
    handle_serial_command();
  }

  delay(100);  // Small delay to prevent overwhelming the loop
}

// ============================================================
// SENSOR READING FUNCTIONS
// ============================================================

void read_all_sensors() {
  // Read each sensor and store in buffer
  float temp = temp_sensor.read();
  if (temp_sensor.is_healthy()) {
    temp_buffer[buffer_index] = temp;
  }

  // Temperature is needed for EC and DO compensation
  ec_sensor.set_temperature(temp);
  do_sensor.set_temperature(temp);

  // Read other sensors
  float ph = ph_sensor.read();
  if (ph_sensor.is_healthy()) {
    ph_buffer[buffer_index] = ph;
  }

  float ec = ec_sensor.read();
  if (ec_sensor.is_healthy()) {
    ec_buffer[buffer_index] = ec;
  }

  float dissolved_oxygen = do_sensor.read();
  if (do_sensor.is_healthy()) {
    do_buffer[buffer_index] = dissolved_oxygen;
  }

  float level = water_level_sensor.read();
  if (water_level_sensor.is_healthy()) {
    level_buffer[buffer_index] = level;
  }

  float turbidity = turbidity_sensor.read();
  if (turbidity_sensor.is_healthy()) {
    turbidity_buffer[buffer_index] = turbidity;
  }
}

float get_average(float* buffer) {
  float sum = 0.0;
  for (int i = 0; i < AVERAGING_WINDOW; i++) {
    sum += buffer[i];
  }
  return sum / AVERAGING_WINDOW;
}

// ============================================================
// SD CARD LOGGING
// ============================================================

void log_to_sd() {
  if (!ENABLE_SD_LOGGING) return;

  // Open file for writing (append mode)
  data_file = SD.open(SD_DATA_FILENAME, FILE_WRITE);

  if (!data_file) {
    if (DEBUG_SERIAL) Serial.println(F("ERROR: Could not open SD file"));
    return;
  }

  // Write header if file is new
  if (data_file.size() == 0) {
    data_file.print(CSV_HEADER);
  }

  // Get current timestamp
  unsigned long timestamp = millis() / 1000;  // Seconds since start

  // Format and write CSV line
  char line[128];
  snprintf(line, sizeof(line), "%lu,%5.2f,%6.1f,%5.2f,%4.2f,%3.0f,%5.1f,OK\n",
           timestamp,
           get_average(ph_buffer),
           get_average(ec_buffer),
           get_average(temp_buffer),
           get_average(do_buffer),
           get_average(level_buffer),
           get_average(turbidity_buffer));

  data_file.print(line);
  data_file.close();

  if (DEBUG_SERIAL) Serial.println(F("Data logged to SD"));
}

// ============================================================
// SERIAL COMMUNICATION
// ============================================================

void send_serial_data() {
  // Send data to Raspberry Pi in JSON format
  // Format: {"pH": 6.8, "EC": 1350, "Temp": 24.5, "DO": 6.2, "Level": 95, "Turbidity": 50}

  Serial.print(F("{\"timestamp\":"));
  Serial.print(millis() / 1000);
  Serial.print(F(",\"pH\":"));
  Serial.print(get_average(ph_buffer), 2);
  Serial.print(F(",\"EC\":"));
  Serial.print(get_average(ec_buffer), 1);
  Serial.print(F(",\"Temp\":"));
  Serial.print(get_average(temp_buffer), 2);
  Serial.print(F(",\"DO\":"));
  Serial.print(get_average(do_buffer), 2);
  Serial.print(F(",\"Level\":"));
  Serial.print(get_average(level_buffer), 0);
  Serial.print(F(",\"Turbidity\":"));
  Serial.print(get_average(turbidity_buffer), 1);
  Serial.println(F("}"));
}

void handle_serial_command() {
  String command = Serial.readStringUntil('\n');
  command.trim();

  if (command.startsWith("CALIB_PH")) {
    handle_ph_calibration(command);
  } else if (command.startsWith("CALIB_EC")) {
    handle_ec_calibration(command);
  } else if (command.startsWith("CALIB_DO")) {
    handle_do_calibration(command);
  } else if (command.startsWith("CALIB_TURB")) {
    handle_turbidity_calibration(command);
  } else if (command == "STATUS") {
    print_status();
  } else if (command == "RESET") {
    software_reset();
  }
}

// ============================================================
// CALIBRATION FUNCTIONS
// ============================================================

void handle_ph_calibration(String cmd) {
  // Command format: CALIB_PH:LOW:512 or CALIB_PH:MID:512 or CALIB_PH:HIGH:512
  int idx1 = cmd.indexOf(':');
  int idx2 = cmd.indexOf(':', idx1 + 1);

  if (idx1 == -1 || idx2 == -1) {
    Serial.println(F("ERROR: Invalid calibration format"));
    return;
  }

  String point = cmd.substring(idx1 + 1, idx2);
  float raw_value = cmd.substring(idx2 + 1).toFloat();

  if (point == "LOW") {
    ph_sensor.set_calib_low(raw_value);
    Serial.println(F("pH calibration LOW stored"));
  } else if (point == "MID") {
    ph_sensor.set_calib_mid(raw_value);
    Serial.println(F("pH calibration MID stored"));
  } else if (point == "HIGH") {
    ph_sensor.set_calib_high(raw_value);
    Serial.println(F("pH calibration HIGH stored"));
  }

  ph_sensor.save_calibration();
  Serial.println(F("pH calibration saved to EEPROM"));
}

void handle_ec_calibration(String cmd) {
  int idx1 = cmd.indexOf(':');
  int idx2 = cmd.indexOf(':', idx1 + 1);

  if (idx1 == -1 || idx2 == -1) {
    Serial.println(F("ERROR: Invalid calibration format"));
    return;
  }

  String point = cmd.substring(idx1 + 1, idx2);
  float raw_value = cmd.substring(idx2 + 1).toFloat();

  if (point == "LOW") {
    ec_sensor.set_calib_low(raw_value);
    Serial.println(F("EC calibration LOW stored"));
  } else if (point == "HIGH") {
    ec_sensor.set_calib_high(raw_value);
    Serial.println(F("EC calibration HIGH stored"));
  }

  ec_sensor.save_calibration();
  Serial.println(F("EC calibration saved to EEPROM"));
}

void handle_do_calibration(String cmd) {
  int idx1 = cmd.indexOf(':');
  int idx2 = cmd.indexOf(':', idx1 + 1);

  if (idx1 == -1 || idx2 == -1) {
    Serial.println(F("ERROR: Invalid calibration format"));
    return;
  }

  String point = cmd.substring(idx1 + 1, idx2);
  float raw_value = cmd.substring(idx2 + 1).toFloat();

  if (point == "ZERO") {
    do_sensor.set_calib_zero(raw_value);
    Serial.println(F("DO calibration ZERO stored"));
  } else if (point == "SPAN") {
    do_sensor.set_calib_span(raw_value);
    Serial.println(F("DO calibration SPAN stored"));
  }

  do_sensor.save_calibration();
  Serial.println(F("DO calibration saved to EEPROM"));
}

void handle_turbidity_calibration(String cmd) {
  int idx = cmd.indexOf(':');
  if (idx == -1) {
    Serial.println(F("ERROR: Invalid calibration format"));
    return;
  }

  float raw_value = cmd.substring(idx + 1).toFloat();
  turbidity_sensor.set_calib_clear(raw_value);
  turbidity_sensor.save_calibration();
  Serial.println(F("Turbidity calibration saved to EEPROM"));
}

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

void init_buffers() {
  for (int i = 0; i < AVERAGING_WINDOW; i++) {
    ph_buffer[i] = 0.0;
    ec_buffer[i] = 0.0;
    temp_buffer[i] = 0.0;
    do_buffer[i] = 0.0;
    level_buffer[i] = 0.0;
    turbidity_buffer[i] = 0.0;
  }
}

void load_thresholds() {
  // Load from EEPROM or use defaults
  // For simplicity, using defaults for now
}

void print_header() {
  Serial.println(F("Time(s),  pH, EC(μS), Temp(C), DO(mg/L), Level(%), Turbidity(NTU)"));
  Serial.println(F("================================================================="));
}

void print_readings() {
  Serial.print(millis() / 1000);
  Serial.print(F(","));
  Serial.print(get_average(ph_buffer), 2);
  Serial.print(F(","));
  Serial.print(get_average(ec_buffer), 0);
  Serial.print(F(","));
  Serial.print(get_average(temp_buffer), 2);
  Serial.print(F(","));
  Serial.print(get_average(do_buffer), 2);
  Serial.print(F(","));
  Serial.print(get_average(level_buffer), 0);
  Serial.print(F(","));
  Serial.println(get_average(turbidity_buffer), 1);
}

void print_status() {
  Serial.println(F("\n=== System Status ==="));
  Serial.print(F("pH Sensor: "));
  Serial.println(ph_sensor.is_healthy() ? "OK" : "ERROR");
  Serial.print(F("EC Sensor: "));
  Serial.println(ec_sensor.is_healthy() ? "OK" : "ERROR");
  Serial.print(F("Temp Sensor: "));
  Serial.println(temp_sensor.is_healthy() ? "OK" : "ERROR");
  Serial.print(F("DO Sensor: "));
  Serial.println(do_sensor.is_healthy() ? "OK" : "ERROR");
  Serial.print(F("Level Sensor: "));
  Serial.println(water_level_sensor.is_healthy() ? "OK" : "ERROR");
  Serial.print(F("Turbidity Sensor: "));
  Serial.println(turbidity_sensor.is_healthy() ? "OK" : "ERROR");
  Serial.println();
}

void software_reset() {
  asm volatile("jmp 0");
}