
/**
 * Aquaponics Smart Farm - Arduino Configuration
 * Hardware pin assignments and calibration constants
 *
 * Board: Arduino Mega 2560 (or modify for Arduino Uno)
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
// SENSOR PIN ASSIGNMENTS
// ============================================================

// Analog Input Pins (ADC)
#define PH_SENSOR_PIN           A0      // pH analog input
#define EC_SENSOR_PIN           A1      // EC/TDS analog input
#define DO_SENSOR_PIN           A2      // Dissolved Oxygen analog input
#define TURBIDITY_SENSOR_PIN    A3      // Turbidity analog input

// Digital Pins
#define TEMPERATURE_PIN         4       // DS18B20 OneWire data pin
#define WATER_LEVEL_PIN         17      // Water level float switch
#define SD_CHIP_SELECT_PIN      53      // SD card SPI chip select (Mega)
#define RTC_SDA_PIN             20      // I2C SDA for DS3231 RTC
#define RTC_SCL_PIN             21      // I2C SCL for DS3231 RTC

// ============================================================
// SENSOR CONFIGURATION
// ============================================================

// Reading intervals (milliseconds)
#define SENSOR_READ_INTERVAL    300000  // 5 minutes (300 seconds)
#define AVERAGING_WINDOW        10      // Number of readings to average
#define SENSOR_TIMEOUT          30000   // 30 second timeout per sensor

// ============================================================
// PH SENSOR CALIBRATION
// ============================================================

// pH calibration points (modify based on your calibration solutions)
#define PH_CALIB_LOW            4.0
#define PH_CALIB_MID            7.0
#define PH_CALIB_HIGH           10.0

// Raw ADC values at calibration points (to be determined during setup)
// These will be stored in EEPROM after calibration
#define EEPROM_PH_CALIB_LOW_ADDR    0
#define EEPROM_PH_CALIB_MID_ADDR    4
#define EEPROM_PH_CALIB_HIGH_ADDR   8

// ============================================================
// EC SENSOR CALIBRATION
// ============================================================

// EC calibration points (μS/cm)
#define EC_CALIB_LOW            1000    // Low EC solution (1000 μS/cm)
#define EC_CALIB_HIGH           10000   // High EC solution (10000 μS/cm)

// Raw ADC values at calibration points (stored in EEPROM)
#define EEPROM_EC_CALIB_LOW_ADDR     12
#define EEPROM_EC_CALIB_HIGH_ADDR    16

// Temperature compensation factor (ppm/°C)
#define EC_TEMP_COEFF           2.0

// ============================================================
// DISSOLVED OXYGEN CALIBRATION
// ============================================================

#define DO_CALIB_ZERO           0       // Zero point (N2 saturation)
#define DO_CALIB_SPAN           100     // Span point (air saturation at sea level)

#define EEPROM_DO_CALIB_ZERO_ADDR    20
#define EEPROM_DO_CALIB_SPAN_ADDR    24

// Altitude above sea level (m) - for DO saturation calculation
#define SYSTEM_ALTITUDE         0

// ============================================================
// ALERT THRESHOLDS
// ============================================================

struct AlertThresholds {
  // pH thresholds
  float ph_min = 5.5;
  float ph_max = 7.5;
  float ph_critical_min = 5.0;
  float ph_critical_max = 8.0;

  // EC thresholds (μS/cm)
  float ec_min = 1200;
  float ec_max = 1600;
  float ec_critical_min = 1000;
  float ec_critical_max = 1800;

  // Temperature thresholds (°C)
  float temp_min = 18;
  float temp_max = 28;
  float temp_critical_min = 15;
  float temp_critical_max = 32;

  // Dissolved Oxygen thresholds (mg/L)
  float do_min = 5.0;
  float do_critical_min = 3.0;

  // Water level thresholds (%)
  float water_level_min = 60;
  float water_level_critical_min = 40;

  // Turbidity thresholds (NTU)
  float turbidity_max = 500;
  float turbidity_critical_max = 1000;
};

// ============================================================
// EEPROM MEMORY MAP
// ============================================================

#define EEPROM_SIZE             1024    // Arduino Mega has 4KB EEPROM

// Calibration data storage (12 bytes for pH, 8 bytes for EC, 8 bytes for DO)
#define EEPROM_CALIB_START      0
#define EEPROM_CALIB_SIZE       28

// Threshold values storage
#define EEPROM_THRESH_START     28
#define EEPROM_THRESH_SIZE      72      // sizeof(AlertThresholds) * 4 bytes per float

// Timestamp of last calibration (4 bytes = 32-bit unsigned long)
#define EEPROM_LAST_CALIB_ADDR  100

// SD card data file
#define SD_DATA_FILENAME        "aqua_data.csv"
#define SD_HEADER_WRITTEN_FLAG  104     // 1 byte

// ============================================================
// DATA LOGGING
// ============================================================

#define ENABLE_SD_LOGGING       true    // Enable SD card data logging
#define SD_LOG_INTERVAL         300     // Log to SD every 5 minutes (300s)

// CSV Header: Timestamp,pH,EC,Temperature,DO,WaterLevel,Turbidity,Flags
#define CSV_HEADER "Time,pH,EC(uS),Temp(C),DO(mg/L),Level(%),Turbidity(NTU),Status\n"

// ============================================================
// REAL-TIME CLOCK (DS3231)
// ============================================================

#define ENABLE_RTC              true    // Enable DS3231 RTC module
#define RTC_I2C_ADDRESS         0x68    // DS3231 I2C address

// ============================================================
// DEBUG AND TESTING
// ============================================================

#define DEBUG_SERIAL            true    // Enable serial debug output
#define BAUD_RATE               115200  // Serial monitor baud rate

// Enable mock sensor data for testing (for development only)
#define ENABLE_MOCK_SENSORS     false

// ============================================================
// SENSOR QUALITY FLAGS
// ============================================================

#define SENSOR_OK               0
#define SENSOR_TIMEOUT          1
#define SENSOR_OUT_OF_RANGE     2
#define SENSOR_UNCALIBRATED     4
#define SENSOR_ERROR            8

// ============================================================
// SYSTEM CONSTANTS
// ============================================================

#define SYSTEM_VOLTAGE          5.0     // System voltage (5.0V or 3.3V)
#define ADC_RESOLUTION          10      // 10-bit ADC (0-1023)
#define ADC_MAX_VALUE           1023

#endif // CONFIG_H
