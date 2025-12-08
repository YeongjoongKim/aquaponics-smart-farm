#pragma once

/**
 * Aquaponics Smart Farm - Sensor Classes (Finalized)
 * - Implemented per-sensor Low-pass filter alpha from config.h
 * - Centralized EC_HARDWARE_LIMIT usage
 * - Added setResolution() to TemperatureSensor for arduino.ino compatibility
 */

#ifndef SENSORS_H
#define SENSORS_H

#include <Arduino.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <EEPROM.h>
#include <Adafruit_ADS1X15.h>
#include "config.h"

// ============================================================
// SENSOR FLAGS (mapped from config.h)
// ============================================================
#define SENSOR_OK           FLAG_OK
#define SENSOR_DISCONNECTED FLAG_DISCONNECTED
#define SENSOR_SATURATED    FLAG_SATURATED


// ============================================================
// BASE SENSOR CLASS
// ============================================================
class Sensor {
protected:
  int pin;
  Adafruit_ADS1115* ads;
  int eeprom_addr;
  int sensor_id;
  uint8_t quality_flags;
  float raw_value;
  float last_temp_c;

  float filtered_value;

  // EMA (Exponential Moving Average) Filter
  float apply_filter(float avg, float alpha) {
    // If first reading (0.0), initialize immediately to avoid slow ramp-up
    if (filtered_value == 0.0) filtered_value = avg;
    
    filtered_value = (filtered_value * (1.0f - alpha)) + (avg * alpha);
    return filtered_value;
  }

  // Sampling Strategy: Read N times -> Average -> Apply EMA Filter
  float sample_and_filter(float alpha) {
    long total = 0;

    for (int i = 0; i < SENSOR_SAMPLES; i++) {
      int16_t val = 0;
      if (ads) {
        val = ads->readADC_SingleEnded(pin);
        if (val < 0) val = 0;
      } else {
        val = analogRead(pin);
      }
      total += val;
      delay(SENSOR_SAMPLE_DELAY_MS);
    }
    float avg = (float)total / (float)SENSOR_SAMPLES;
    return apply_filter(avg, alpha);
  }

public:
  Sensor(int _pin, Adafruit_ADS1115* _ads=nullptr, int _addr=-1)
    : pin(_pin), ads(_ads), eeprom_addr(_addr),
      sensor_id(0), quality_flags(FLAG_OK),
      raw_value(0.0), last_temp_c(25.0), filtered_value(0.0) {}

  virtual ~Sensor() {}

  virtual float read() = 0;
  virtual void calibrate() = 0;
  virtual void load_calibration() = 0;
  virtual void save_calibration() = 0;

  virtual void set_temperature(float t) {
    // Safety range for temperature compensation inputs
    if (t > HARD_TEMP_MIN && t < HARD_TEMP_MAX)
      last_temp_c = t;
  }

  uint8_t get_flags() const { return quality_flags; }
  float   get_raw()   const { return raw_value; }
};


// ============================================================
// PH SENSOR
// ============================================================
class PHSensor : public Sensor {
private:
  float calib_low_raw;
  float calib_mid_raw;
  float calib_high_raw;

public:
  PHSensor(int _pin, Adafruit_ADS1115* _ads, int _addr)
    : Sensor(_pin, _ads, _addr) {
    sensor_id = 1;
    // Default values based on typical ADC readings
    if (_ads) {
      calib_mid_raw  = 13500.0;
      calib_low_raw  = 17800.0; // Acidic voltage is usually higher on some probes, depends on op-amp
      calib_high_raw = 9200.0;
    } else {
      calib_mid_raw  = 512.0;
      calib_low_raw  = 650.0;
      calib_high_raw = 370.0;
    }
    load_calibration();
  }

  float read() override {
    quality_flags = FLAG_OK;
    // Use specific alpha for pH
    raw_value = sample_and_filter(SENSOR_FILTER_ALPHA_PH);

    float max_limit = (ads)?27000.0:1020.0;
    
    // Disconnection check
    if (raw_value < 5.0 || raw_value > max_limit) {
      quality_flags = FLAG_DISCONNECTED;
      return -1.0;
    }

    float ph_value = 7.0;
    if (raw_value > calib_mid_raw) {
      // Slope for 4.0 ~ 7.0
      float slope = (7.0-4.0)/(calib_low_raw-calib_mid_raw);
      ph_value = 7.0 - slope*(raw_value-calib_mid_raw);
    } else {
      // Slope for 7.0 ~ 10.0
      float slope = (10.0-7.0)/(calib_mid_raw-calib_high_raw);
      ph_value = 7.0 + slope*(calib_mid_raw-raw_value);
    }
    return constrain(ph_value, 0.0, 14.0);
  }

  void calibrate() override {} // Implement specific command logic in sensors.cpp if needed
  
  void load_calibration() override {
    if (eeprom_addr<0) return;
    float stored_mid;
    EEPROM.get(eeprom_addr+4, stored_mid);
    if (!isnan(stored_mid) && stored_mid>100.0){
      EEPROM.get(eeprom_addr,     calib_low_raw);
      calib_mid_raw = stored_mid;
      EEPROM.get(eeprom_addr+8, calib_high_raw);
    }
  }
  void save_calibration() override {
    if (eeprom_addr<0) return;
    EEPROM.put(eeprom_addr,     calib_low_raw);
    EEPROM.put(eeprom_addr+4,   calib_mid_raw);
    EEPROM.put(eeprom_addr+8,   calib_high_raw);
  }
};


// ============================================================
// EC SENSOR
// ============================================================
class ECSensor : public Sensor {
private:
  float calib_standard_raw;

public:
  ECSensor(int _pin, Adafruit_ADS1115* _ads, int _addr)
    : Sensor(_pin, _ads, _addr) {
    sensor_id = 2;
    calib_standard_raw = (_ads?8000.0:220.0);
    load_calibration();
  }

  float read() override {
    quality_flags = FLAG_OK;
    // Use specific alpha for EC
    raw_value = sample_and_filter(SENSOR_FILTER_ALPHA_EC);

    if (raw_value < 5.0) return 0.0;

    float max_limit = (ads)?26000.0:1020.0;
    if (raw_value > max_limit){
      quality_flags = FLAG_SATURATED;
      // [FIX] Use Centralized Limit from config.h
      return EC_HARDWARE_LIMIT;
    }

    // Linear Calibration
    float k_factor   = (calib_standard_raw>0)?(EC_REF_STANDARD/calib_standard_raw):1.0;
    float ec_uncomp  = raw_value*k_factor;

    // Temperature Compensation (2.0% per degree C)
    float temp_factor = 1.0 + 0.02*(last_temp_c-25.0);
    float ec_final    = (temp_factor>0)?(ec_uncomp/temp_factor):ec_uncomp;

    // [FIX] Use Centralized Limit
    return constrain(ec_final, 0.0, EC_HARDWARE_LIMIT);
  }

  void calibrate() override {}
  void load_calibration() override {
    if (eeprom_addr<0) return;
    float stored;
    EEPROM.get(eeprom_addr, stored);
    if (!isnan(stored) && stored>10.0)
      calib_standard_raw = stored;
  }
  void save_calibration() override {
    if (eeprom_addr<0) return;
    EEPROM.put(eeprom_addr, calib_standard_raw);
  }
};


// ============================================================
// TEMPERATURE DS18B20 (Async + Resolution Support)
// ============================================================
class TemperatureSensor : public Sensor {
private:
  OneWire* one_wire;
  DallasTemperature* sensors;

public:
  TemperatureSensor(int _pin)
    : Sensor(_pin,nullptr,-1) {
    sensor_id = 3;
    one_wire  = new OneWire(_pin);
    sensors   = new DallasTemperature(one_wire);
    sensors->begin();
    // Default init, but should be overridden by setResolution call in setup
    sensors->setResolution(TEMP_DS18_RESOLUTION); 
    sensors->setWaitForConversion(false); // Enable Async mode
  }

  ~TemperatureSensor(){
    delete sensors;
    delete one_wire;
  }

  // [NEW] Public method to allow resolution setting from main setup()
  void setResolution(uint8_t res) {
      if(sensors) sensors->setResolution(res);
  }

  // Request only (call in loop BEFORE reading)
  void request_conversion(){
    if(sensors) sensors->requestTemperatures();
  }

  float read() override {
    quality_flags = FLAG_OK;
    // Get the temperature prepared by previous request_conversion()
    float tempC = sensors->getTempCByIndex(0);

    // Error checks
    if (tempC == DEVICE_DISCONNECTED_C || tempC < HARD_TEMP_MIN || tempC > HARD_TEMP_MAX){
      quality_flags = FLAG_DISCONNECTED;
      return -127.0;
    }

    raw_value = tempC;
    last_temp_c = tempC;
    // Use specific alpha for Temperature
    return apply_filter(tempC, SENSOR_FILTER_ALPHA_TEMP);
  }

  void calibrate() override {}
  void load_calibration() override {}
  void save_calibration() override {}
};


// ============================================================
// DO SENSOR
// ============================================================
class DOSensor : public Sensor {
private:
  float calib_do_raw;

public:
  DOSensor(int _pin, Adafruit_ADS1115* _ads, int _addr)
    : Sensor(_pin,_ads,_addr){
    sensor_id = 4;
    calib_do_raw = (_ads?12000.0:327.0);
    load_calibration();
  }

  float read() override {
    quality_flags = FLAG_OK;
    // Use specific alpha for DO
    raw_value = sample_and_filter(SENSOR_FILTER_ALPHA_DO);

    // Simplified DO saturation calculation based on temp
    float sat = (14.652 - 0.41022*last_temp_c +
                 0.007991*last_temp_c*last_temp_c -
                 0.000077774*last_temp_c*last_temp_c*last_temp_c);

    float ratio = (calib_do_raw>0)?(raw_value/calib_do_raw):0.0;
    float do_v = ratio*sat;

    return constrain(do_v, 0.0, 20.0);
  }

  void calibrate() override {}
  void load_calibration() override {
    if (eeprom_addr<0) return;
    float s;
    EEPROM.get(eeprom_addr,s);
    if (!isnan(s) && s>10.0) calib_do_raw = s;
  }
  void save_calibration() override {
    if (eeprom_addr<0) return;
    EEPROM.put(eeprom_addr, calib_do_raw);
  }
};


// ============================================================
// WATER LEVEL
// ============================================================
class WaterLevelSensor : public Sensor {
public:
  WaterLevelSensor(int _pin):Sensor(_pin,nullptr,-1){
    sensor_id = 5;
  }

  float read() override {
    quality_flags = FLAG_OK;
    // Use specific alpha for Water Level
    raw_value = sample_and_filter(SENSOR_FILTER_ALPHA_LEVEL);

    float pct = (raw_value/1023.0)*100.0;
    if (pct<1.0) pct=0;
    return constrain(pct,0,100);
  }

  void calibrate() override {}
  void load_calibration() override {}
  void save_calibration() override {}
};


// ============================================================
// TURBIDITY
// ============================================================
class TurbiditySensor: public Sensor{
private:
  float calib_clear_raw;

public:
  TurbiditySensor(int _pin,int _addr)
    :Sensor(_pin,nullptr,_addr){
    sensor_id=6;
    calib_clear_raw=800.0;
    load_calibration();
  }

  float read() override {
    quality_flags=FLAG_OK;
    // Use specific alpha for Turbidity
    raw_value = sample_and_filter(SENSOR_FILTER_ALPHA_TURB);

    float turbidity=0.0;
    if(raw_value<calib_clear_raw){
      turbidity=((calib_clear_raw-raw_value)/calib_clear_raw)*3000.0;
    }
    return constrain(turbidity,0,3000);
  }

  void calibrate() override {}
  void load_calibration() override{
    if (eeprom_addr<0)return;
    float s;
    EEPROM.get(eeprom_addr,s);
    if(!isnan(s)&&s>100.0) calib_clear_raw=s;
  }
  void save_calibration() override{
    if(eeprom_addr<0)return;
    EEPROM.put(eeprom_addr,calib_clear_raw);
  }
};

#endif