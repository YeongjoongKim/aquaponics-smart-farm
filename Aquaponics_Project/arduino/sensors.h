/**
 * Aquaponics Smart Farm - Sensor Classes
 * Optimized for Multi-Zone System (3 Filter / 3 Nutrient / 1 Line)
 * * [Reflected Documentation]
 * - HARDWARE_SETUP.md: ADS1115 (0x48~0x4B) integration & Pin mappings
 * - CALIBRATION.md: Specific calibration logic (3-pt pH, 1-pt EC, etc.)
 * - README.md: Safety limits (EC Saturation > 2000, Level < 40%)
 */

#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <EEPROM.h>
#include <Adafruit_ADS1X15.h> // Required for 16-bit ADC support
#include "config.h"

// ============================================================
// BASE SENSOR CLASS
// Supports hybrid reading: Native Analog (10-bit) OR ADS1115 (16-bit)
// ============================================================

class Sensor {
protected:
  int pin;
  Adafruit_ADS1115* ads; // Pointer to ADS object (nullptr if using native pin)
  int eeprom_addr;       // Unique EEPROM Start Address
  int sensor_id;
  uint8_t quality_flags;
  float raw_value;
  float last_temp_c;     // Shared temperature storage for ATC

  // Helper: Reads raw value from either ADS1115 or Native Pin
  // Returns: 0-1023 (Native) or 0-32767 (ADS1115)
  float get_raw_reading() {
    long total = 0;
    int samples = 10;
    
    for (int i = 0; i < samples; i++) {
      if (ads != nullptr) {
        // ADS1115 Read (16-bit)
        // Note: readADC_SingleEnded returns int16_t. Ensure positive.
        int16_t val = ads->readADC_SingleEnded(pin);
        total += (val > 0) ? val : 0; 
      } else {
        // Native Arduino Read (10-bit)
        total += analogRead(pin);
      }
      delay(5); // Small debounce
    }
    return (float)(total / samples);
  }

public:
  // Constructor: Now accepts optional ADS pointer
  Sensor(int _pin, Adafruit_ADS1115* _ads = nullptr, int _addr = -1) 
    : pin(_pin), ads(_ads), eeprom_addr(_addr), sensor_id(0), quality_flags(0), raw_value(0.0), last_temp_c(25.0) {}
  
  virtual ~Sensor() {}

  virtual float read() = 0;
  virtual void calibrate() = 0; 
  virtual void load_calibration() = 0;
  virtual void save_calibration() = 0;

  virtual void set_temperature(float temp) { 
    // ATC Safety: Only accept realistic water temps
    if (temp > 5.0 && temp < 40.0) last_temp_c = temp; 
  }

  uint8_t get_flags() const { return quality_flags; }
  float get_raw() const { return raw_value; }
};

// ============================================================
// PH SENSOR CLASS (Target: Gravity SEN0169-V2)
// Ref: CALIBRATION.md -> 3-Point Calibration (4.0, 7.0, 10.0)
// ============================================================

class PHSensor : public Sensor {
private:
  float calib_low_raw;      // Raw ADC at pH 4.0
  float calib_mid_raw;      // Raw ADC at pH 7.0 (Neutral offset)
  float calib_high_raw;     // Raw ADC at pH 10.0

public:
  PHSensor(int _pin, Adafruit_ADS1115* _ads, int _addr) : Sensor(_pin, _ads, _addr) {
    sensor_id = 1;
    // Set safe defaults based on ADC type
    // ADS1115 (16-bit) values are much higher than Native (10-bit)
    if (_ads) {
      calib_mid_raw = 13500.0; // Approx 2.5V on ADS (Gain dependent)
      calib_low_raw = 17800.0; // Acidic
      calib_high_raw = 9200.0; // Alkaline
    } else {
      calib_mid_raw = 512.0;   // 2.5V on Native
      calib_low_raw = 650.0;
      calib_high_raw = 370.0;
    }
    load_calibration();
  }

  float read() override {
    raw_value = get_raw_reading();

    // Disconnect Check
    // Native: <5 or >1020. ADS: <100 or >26000 (Approx)
    float max_limit = (ads) ? 27000.0 : 1020.0;
    if (raw_value < 5.0 || raw_value > max_limit) {
      quality_flags |= SENSOR_DISCONNECTED;
      return -1.0; 
    }

    float ph_value = 7.0;
    float slope = 1.0;

    // Calculate pH based on calibration curve
    if (raw_value > calib_mid_raw) { 
      // Acidic Range (Voltage increases as pH decreases for SEN0169)
      if ((calib_low_raw - calib_mid_raw) != 0) {
        slope = (7.0 - 4.0) / (calib_low_raw - calib_mid_raw);
        ph_value = 7.0 - slope * (raw_value - calib_mid_raw);
      }
    } else {
      // Alkaline Range
      if ((calib_mid_raw - calib_high_raw) != 0) {
        slope = (10.0 - 7.0) / (calib_mid_raw - calib_high_raw);
        ph_value = 7.0 + slope * (calib_mid_raw - raw_value);
      }
    }

    quality_flags = SENSOR_OK;
    return constrain(ph_value, 0.0, 14.0);
  }

  void calibrate() override {} // Calibration handled by specific setters via Serial Command

  void load_calibration() override {
    if (eeprom_addr < 0) return;
    float stored_mid;
    EEPROM.get(eeprom_addr + 4, stored_mid);
    
    // Sanity check: If EEPROM is empty (NaN or 0), keep defaults
    if (!isnan(stored_mid) && stored_mid > 100.0) {
      EEPROM.get(eeprom_addr, calib_low_raw);      // Base + 0
      calib_mid_raw = stored_mid;                  // Base + 4
      EEPROM.get(eeprom_addr + 8, calib_high_raw); // Base + 8
    }
  }

  void save_calibration() override {
    if (eeprom_addr < 0) return;
    EEPROM.put(eeprom_addr, calib_low_raw);
    EEPROM.put(eeprom_addr + 4, calib_mid_raw);
    EEPROM.put(eeprom_addr + 8, calib_high_raw);
  }

  void set_calib_low(float raw) { calib_low_raw = raw; }
  void set_calib_mid(float raw) { calib_mid_raw = raw; }
  void set_calib_high(float raw) { calib_high_raw = raw; }
};

// ============================================================
// EC SENSOR CLASS (Target: Gravity SEN0451)
// Ref: README.md -> Hardware Saturation Limit at 2000 uS/cm
// Ref: CALIBRATION.md -> 1-Point Calibration @ 1413 uS/cm
// ============================================================

class ECSensor : public Sensor {
private:
  float calib_standard_raw;   
  const float standard_ec = 1413.0; 

public:
  ECSensor(int _pin, Adafruit_ADS1115* _ads, int _addr) : Sensor(_pin, _ads, _addr) {
    sensor_id = 2;
    // Default approx raw values
    calib_standard_raw = (ads) ? 8000.0 : 220.0; 
    load_calibration();
  }

  float read() override {
    raw_value = get_raw_reading();

    if (raw_value < 5.0) return 0.0;
    
    // [CRITICAL] Saturation Check (Hardware Limit)
    // ADS1115 value around 26000 corresponds to 2.0-3.0V depending on gain
    float max_limit = (ads) ? 26000.0 : 1020.0;
    if (raw_value > max_limit) {
      quality_flags |= SENSOR_SATURATED;
      return 2000.0; // Return max limit to indicate saturation
    }

    float k_factor = 1.0;
    if (calib_standard_raw > 0) {
      k_factor = standard_ec / calib_standard_raw;
    }
    
    // Linear approximation for Analog EC
    float ec_uncompensated = raw_value * k_factor;

    // Temperature Compensation (25.0 C standard)
    float temp_coefficient = 0.02; 
    float temp_factor = 1.0 + temp_coefficient * (last_temp_c - 25.0);
    
    float ec_final = 0.0;
    if (temp_factor > 0) {
        ec_final = ec_uncompensated / temp_factor;
    }

    quality_flags = SENSOR_OK;
    return constrain(ec_final, 0.0, 2500.0); 
  }

  void calibrate() override {} 

  void load_calibration() override {
    if (eeprom_addr < 0) return;
    float stored_std;
    EEPROM.get(eeprom_addr, stored_std);
    if (!isnan(stored_std) && stored_std > 10.0) {
        calib_standard_raw = stored_std;
    }
  }

  void save_calibration() override {
    if (eeprom_addr < 0) return;
    EEPROM.put(eeprom_addr, calib_standard_raw);
  }

  void set_calib_standard(float raw) { calib_standard_raw = raw; }
};

// ============================================================
// TEMPERATURE SENSOR CLASS (Target: DS18B20)
// Ref: HARDWARE_SETUP.md -> Digital Pin (D2-D7), Pull-up required
// ============================================================

class TemperatureSensor : public Sensor {
private:
  OneWire* one_wire;
  DallasTemperature* sensors;

public:
  // Digital sensor does not use ADS or EEPROM
  TemperatureSensor(int _pin) : Sensor(_pin, nullptr, -1) {
    sensor_id = 3;
    one_wire = new OneWire(_pin);
    sensors = new DallasTemperature(one_wire);
    sensors->begin();
    sensors->setWaitForConversion(false); // Async reading
  }

  ~TemperatureSensor() {
    delete sensors;
    delete one_wire;
  }

  float read() override {
    sensors->requestTemperatures(); 
    // Small delay usually required, but main loop delay handles it
    
    float tempC = sensors->getTempCByIndex(0);

    // DS18B20 Error Codes
    if (tempC == DEVICE_DISCONNECTED_C || tempC < -50.0) {
      quality_flags |= SENSOR_DISCONNECTED;
      return -127.0;
    }

    raw_value = tempC;
    last_temp_c = tempC; 
    quality_flags = SENSOR_OK;
    return tempC;
  }

  void calibrate() override {}
  void load_calibration() override {}
  void save_calibration() override {}
};

// ============================================================
// DO SENSOR CLASS (Target: Gravity SEN0237)
// Ref: CALIBRATION.md -> 2-Point (0%, 100%)
// ============================================================

class DOSensor : public Sensor {
private:
  float calib_do_raw; // Represents 100% Saturation Raw Value

public:
  DOSensor(int _pin, Adafruit_ADS1115* _ads, int _addr) : Sensor(_pin, _ads, _addr) {
    sensor_id = 4;
    calib_do_raw = (ads) ? 12000.0 : 327.0; // Defaults
    load_calibration();
  }

  float read() override {
    raw_value = get_raw_reading();

    // Saturation calculation formula (Simplified)
    float saturation_mg_L = 14.652 - 0.41022 * last_temp_c + 0.007991 * last_temp_c * last_temp_c - 0.000077774 * last_temp_c * last_temp_c * last_temp_c;
    
    float ratio = 0.0;
    if (calib_do_raw > 0) {
        ratio = raw_value / calib_do_raw;
    }
    
    float do_value = ratio * saturation_mg_L;

    quality_flags = SENSOR_OK;
    return constrain(do_value, 0.0, 20.0);
  }

  void calibrate() override {} 

  void load_calibration() override {
    if (eeprom_addr < 0) return;
    float stored_do;
    EEPROM.get(eeprom_addr, stored_do);
    if(!isnan(stored_do) && stored_do > 10.0) calib_do_raw = stored_do; 
  }

  void save_calibration() override {
    if (eeprom_addr < 0) return;
    EEPROM.put(eeprom_addr, calib_do_raw);
  }

  void set_calib_span(float raw) { calib_do_raw = raw; }
};

// ============================================================
// WATER LEVEL SENSOR CLASS (Target: KIT0139)
// Ref: HARDWARE_SETUP.md -> Uses 24V I/V Converter
// Ref: CALIBRATION.md -> Hardware Calibration (Potentiometer) only
// ============================================================

class WaterLevelSensor : public Sensor {
public:
  // Water Level uses Native Pins only (Zone A) as per config.json
  WaterLevelSensor(int _pin) : Sensor(_pin, nullptr, -1) {
    sensor_id = 5;
  }

  float read() override {
    // Hardware calibration ensures 0V = Empty, 5V = Full
    raw_value = get_raw_reading(); // 0-1023
    
    // Map 0-1023 to 0-100%
    float percentage = (raw_value / 1023.0) * 100.0;
    
    // Noise filter near zero
    if (percentage < 2.0) percentage = 0.0;

    quality_flags = SENSOR_OK;
    return constrain(percentage, 0.0, 100.0);
  }

  void calibrate() override {} // No software calibration needed
  void load_calibration() override {}
  void save_calibration() override {}
};

// ============================================================
// TURBIDITY SENSOR CLASS (Target: Gravity SEN0189)
// Ref: CALIBRATION.md -> Baseline Calibration (Clear Water)
// ============================================================

class TurbiditySensor : public Sensor {
private:
  float calib_clear_raw; 

public:
  // Turbidity uses Native Pins (Zone A)
  TurbiditySensor(int _pin, int _addr) : Sensor(_pin, nullptr, _addr) { 
    sensor_id = 6;
    calib_clear_raw = 800.0; // Default clear water reading (~4V)
    load_calibration(); 
  }

  float read() override {
    raw_value = get_raw_reading();
    
    float turbidity = 0.0;
    // Voltage drops as turbidity increases
    // Simple inverted mapping relative to clear water baseline
    if (raw_value < calib_clear_raw) {
        turbidity = ((calib_clear_raw - raw_value) / calib_clear_raw) * 3000.0; // 3000 NTU max scale
    }

    quality_flags = SENSOR_OK;
    return constrain(turbidity, 0.0, 3000.0);
  }

  void calibrate() override {} // Handled via set_calib_clear

  void load_calibration() override {
      if (eeprom_addr < 0) return;
      float stored_clear;
      EEPROM.get(eeprom_addr, stored_clear);
      if (!isnan(stored_clear) && stored_clear > 100.0) calib_clear_raw = stored_clear;
  }

  void save_calibration() override {
      if (eeprom_addr < 0) return;
      EEPROM.put(eeprom_addr, calib_clear_raw);
  }
  
  void set_calib_clear(float raw) { calib_clear_raw = raw; }
};

#endif // SENSORS_H