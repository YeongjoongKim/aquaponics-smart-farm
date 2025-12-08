/**
 * Aquaponics Smart Farm - Arduino Main (Final Full Version)
 * * [Changes Applied]
 * 1. Setup: Added setResolution(TEMP_DS18_RESOLUTION) for all 6 temperature sensors.
 * 2. Loop: Improved async timing logic (Request -> Wait -> Read) to prevent blocking.
 * 3. Init: Added Serial wait loop for stability.
 */

#include "config.h"
#include "sensors.h"

#include <Wire.h>
#include <SD.h>
#include <avr/wdt.h>
#include <Adafruit_ADS1X15.h>
#include <EEPROM.h>

// ==========================================
// Global ADS declarations
// ==========================================
Adafruit_ADS1115 ads_zone_a;
Adafruit_ADS1115 ads_zone_b1;
Adafruit_ADS1115 ads_zone_b2;
Adafruit_ADS1115 ads_zone_b3;

// ==========================================
// Sensor declarations
// ==========================================

// --- Zone A (Filter) ---
PHSensor zA_t1_ph(CH_A_TANK1_PH, &ads_zone_a, ADDR_A_T1_PH);
WaterLevelSensor zA_t1_lvl(PIN_A_TANK1_LEVEL);
TurbiditySensor zA_t1_turb(PIN_A_TANK1_TURB, ADDR_A_T1_TURB);
TemperatureSensor zA_t1_temp(PIN_A_TANK1_TEMP);

PHSensor zA_t2_ph(CH_A_TANK2_PH, &ads_zone_a, ADDR_A_T2_PH);
WaterLevelSensor zA_t2_lvl(PIN_A_TANK2_LEVEL);
TurbiditySensor zA_t2_turb(PIN_A_TANK2_TURB, ADDR_A_T2_TURB);
TemperatureSensor zA_t2_temp(PIN_A_TANK2_TEMP);

PHSensor zA_t3_ph(CH_A_TANK3_PH, &ads_zone_a, ADDR_A_T3_PH);
WaterLevelSensor zA_t3_lvl(PIN_A_TANK3_LEVEL);
TurbiditySensor zA_t3_turb(PIN_A_TANK3_TURB, ADDR_A_T3_TURB);
TemperatureSensor zA_t3_temp(PIN_A_TANK3_TEMP);

// --- Zone B (Nutrient) ---
PHSensor zB_t1_ph(CH_B_TANK1_PH, &ads_zone_b1, ADDR_B_T1_PH);
ECSensor zB_t1_ec(CH_B_TANK1_EC, &ads_zone_b1, ADDR_B_T1_EC);
DOSensor zB_t1_do(CH_B_TANK1_DO, &ads_zone_b1, ADDR_B_T1_DO);
TemperatureSensor zB_t1_temp(PIN_B_TANK1_TEMP);

PHSensor zB_t2_ph(CH_B_TANK2_PH, &ads_zone_b1, ADDR_B_T2_PH);
ECSensor zB_t2_ec(CH_B_TANK2_EC, &ads_zone_b2, ADDR_B_T2_EC);
DOSensor zB_t2_do(CH_B_TANK2_DO, &ads_zone_b2, ADDR_B_T2_DO);
TemperatureSensor zB_t2_temp(PIN_B_TANK2_TEMP);

PHSensor zB_t3_ph(CH_B_TANK3_PH, &ads_zone_b2, ADDR_B_T3_PH);
ECSensor zB_t3_ec(CH_B_TANK3_EC, &ads_zone_b2, ADDR_B_T3_EC);
DOSensor zB_t3_do(CH_B_TANK3_DO, &ads_zone_b3, ADDR_B_T3_DO);
TemperatureSensor zB_t3_temp(PIN_B_TANK3_TEMP);

// --- Zone C (Line) ---
ECSensor zC_start_ec(CH_C_START_EC, &ads_zone_b3, ADDR_C_START_EC);
ECSensor zC_mid_ec(CH_C_MID_EC, &ads_zone_b3, ADDR_C_MID_EC);
ECSensor zC_end_ec(CH_C_END_EC, &ads_zone_b3, ADDR_C_END_EC);

// ==========================================
// Global State & Config
// ==========================================
unsigned long last_reading_time = 0;
unsigned long last_sd_write_time = 0;
bool temp_conversion_requested = false; 

// Fallback configs if not in config.h
#ifndef SD_LOG_INTERVAL
#define SD_LOG_INTERVAL 600 
#endif
#define SD_DATA_FILENAME "datalog.csv"
#define ENABLE_SD_LOGGING true
#define DEBUG_SERIAL true
#define SD_CHIP_SELECT_PIN 4   

struct SystemState {
  float za_t1[4]; // [ph, turb, lvl, temp]
  float za_t2[4];
  float za_t3[4];
  float zb_t1[4]; // [ph, ec, do, temp]
  float zb_t2[4];
  float zb_t3[4];
  float zc[3];    // [start_ec, mid_ec, end_ec]
  String status;
} sysState;

// ==========================================
// Function Prototypes
// ==========================================
void handle_serial_command();
void log_to_sd();
void send_json_data();
void print_tank(const char* name, PHSensor& ph, TurbiditySensor& tb, WaterLevelSensor& lv, float temp_val, TemperatureSensor& temp_sensor);
void print_tankB(const char* name, PHSensor& ph, ECSensor& ec, DOSensor& d, float temp_val, TemperatureSensor& temp_sensor);
void print_value_flag(const char* key, float v, uint8_t f, bool comma);
void request_all_temp_conversions();
void read_all_sensors();

// ==========================================
// Setup
// ==========================================
void setup() {
  // 1. EEPROM Check
  if(EEPROM.read(ADDR_MAGIC) != EEPROM_MAGIC){
    EEPROM.write(ADDR_MAGIC, EEPROM_MAGIC);
    // Factory reset logic can go here if needed
  }
  
  // 2. Serial Init
  wdt_disable();
  Serial.begin(SERIAL_BAUD_RATE);
  // Wait for serial to be ready (useful for some boards like Leonardo, harmless for Mega)
  unsigned long serial_wait = millis();
  while (!Serial && (millis() - serial_wait < 3000)); 
  delay(1500);

  // 3. ADS Init
  Wire.begin();
  ads_zone_a.begin(ADS_ADDR_ZONE_A);
  ads_zone_b1.begin(ADS_ADDR_ZONE_B1);
  ads_zone_b2.begin(ADS_ADDR_ZONE_B2);
  ads_zone_b3.begin(ADS_ADDR_ZONE_B3);

  ads_zone_a.setGain(ADS_GAIN_SETTING);
  ads_zone_b1.setGain(ADS_GAIN_SETTING);
  ads_zone_b2.setGain(ADS_GAIN_SETTING);
  ads_zone_b3.setGain(ADS_GAIN_SETTING);
  
  // 4. SD Card Init
  pinMode(SD_CHIP_SELECT_PIN, OUTPUT);
  if (ENABLE_SD_LOGGING) {
      if (!SD.begin(SD_CHIP_SELECT_PIN)) {
          if (DEBUG_SERIAL) Serial.println(F("[ERR] SD Init Failed!"));
      }
  }
  if (DEBUG_SERIAL) Serial.println(F("[INIT] System Ready"));
  
  // 5. Temperature Resolution Setting (CRITICAL FIX)
  // Ensures DS18B20 uses the resolution defined in config.h (e.g., 12-bit)
  zA_t1_temp.setResolution(TEMP_DS18_RESOLUTION);
  zA_t2_temp.setResolution(TEMP_DS18_RESOLUTION);
  zA_t3_temp.setResolution(TEMP_DS18_RESOLUTION);
  zB_t1_temp.setResolution(TEMP_DS18_RESOLUTION);
  zB_t2_temp.setResolution(TEMP_DS18_RESOLUTION);
  zB_t3_temp.setResolution(TEMP_DS18_RESOLUTION);

  // 6. Initial Temp Request
  request_all_temp_conversions();

  wdt_enable(WDTO_8S);
}

// ==========================================
// Loop
// ==========================================
void loop() {
  wdt_reset();
  unsigned long now = millis();

  // Handle incoming Serial Commands
  if (Serial.available()) handle_serial_command();

  // ASYNC READING LOGIC
  
  // Step 1: Check if it's time to REQUEST a new reading
  if (now - last_reading_time >= READ_INTERVAL_MS) {
    if (!temp_conversion_requested) {
      request_all_temp_conversions();
      // Update baseline time to 'now' so we wait for conversion relative to this moment
      last_reading_time = now; 
    }
  }

  // Step 2: Check if conversion time has passed since the request
  if (temp_conversion_requested && (now - last_reading_time >= TEMP_CONVERT_MS)) {
    // Read all sensors (Temps are now ready)
    read_all_sensors();
    
    // Send Data to RPi
    send_json_data();

    // Log to SD if interval met
    if (ENABLE_SD_LOGGING && (now - last_sd_write_time >= SD_LOG_INTERVAL*1000UL)) {
      log_to_sd();
      last_sd_write_time = now;
    }
    
    // Reset Flag
    temp_conversion_requested = false; 
    
    // Reset Timer: Cycle is complete. 
    // Next request will happen READ_INTERVAL_MS after this point.
    last_reading_time = now; 
  }
}

// ==========================================
// Helper Functions
// ==========================================

void request_all_temp_conversions() {
    zA_t1_temp.request_conversion();
    zA_t2_temp.request_conversion();
    zA_t3_temp.request_conversion();
    zB_t1_temp.request_conversion();
    zB_t2_temp.request_conversion();
    zB_t3_temp.request_conversion();
    
    temp_conversion_requested = true;
    if (DEBUG_SERIAL) Serial.println(F("[TEMP] Conversion requested."));
}

void read_all_sensors() {
  // 1. Read Temperatures (Result of async request)
  float tA1 = zA_t1_temp.read();
  float tA2 = zA_t2_temp.read();
  float tA3 = zA_t3_temp.read();
  float tB1 = zB_t1_temp.read();
  float tB2 = zB_t2_temp.read();
  float tB3 = zB_t3_temp.read();
  
  sysState.status = "OK";
  if (zA_t1_temp.get_flags() == FLAG_DISCONNECTED || zB_t1_temp.get_flags() == FLAG_DISCONNECTED) {
      sysState.status = "ERR_TEMP";
  }

  // 2. Zone A (Filter) Readings - Apply Temp Comp
  zA_t1_ph.set_temperature(tA1);
  zA_t2_ph.set_temperature(tA2);
  zA_t3_ph.set_temperature(tA3);

  sysState.za_t1[0] = zA_t1_ph.read();
  sysState.za_t1[1] = zA_t1_turb.read();
  sysState.za_t1[2] = zA_t1_lvl.read();
  sysState.za_t1[3] = tA1; 

  sysState.za_t2[0] = zA_t2_ph.read();
  sysState.za_t2[1] = zA_t2_turb.read();
  sysState.za_t2[2] = zA_t2_lvl.read();
  sysState.za_t2[3] = tA2; 
  
  sysState.za_t3[0] = zA_t3_ph.read();
  sysState.za_t3[1] = zA_t3_turb.read();
  sysState.za_t3[2] = zA_t3_lvl.read();
  sysState.za_t3[3] = tA3; 

  // 3. Zone B (Nutrient) Readings - Apply Temp Comp
  zB_t1_ph.set_temperature(tB1);
  zB_t1_ec.set_temperature(tB1);
  zB_t1_do.set_temperature(tB1);
  
  zB_t2_ph.set_temperature(tB2);
  zB_t2_ec.set_temperature(tB2);
  zB_t2_do.set_temperature(tB2);
  
  zB_t3_ph.set_temperature(tB3);
  zB_t3_ec.set_temperature(tB3);
  zB_t3_do.set_temperature(tB3);

  sysState.zb_t1[0] = zB_t1_ph.read();
  sysState.zb_t1[1] = zB_t1_ec.read();
  sysState.zb_t1[2] = zB_t1_do.read();
  sysState.zb_t1[3] = tB1; 

  sysState.zb_t2[0] = zB_t2_ph.read();
  sysState.zb_t2[1] = zB_t2_ec.read();
  sysState.zb_t2[2] = zB_t2_do.read();
  sysState.zb_t2[3] = tB2; 
  
  sysState.zb_t3[0] = zB_t3_ph.read();
  sysState.zb_t3[1] = zB_t3_ec.read();
  sysState.zb_t3[2] = zB_t3_do.read();
  sysState.zb_t3[3] = tB3; 

  // 4. Zone C (Line) Readings - Shares T3 Temp
  zC_start_ec.set_temperature(tB3);
  zC_mid_ec.set_temperature(tB3);
  zC_end_ec.set_temperature(tB3);
  
  sysState.zc[0] = zC_start_ec.read();
  sysState.zc[1] = zC_mid_ec.read();
  sysState.zc[2] = zC_end_ec.read();
  
  // 5. Logic Checks (EC Saturation)
  if (zB_t1_ec.get_flags() == FLAG_SATURATED || zB_t2_ec.get_flags() == FLAG_SATURATED || zB_t3_ec.get_flags() == FLAG_SATURATED) {
      sysState.status = "SAT_EC";
  }
}

void send_json_data(){
  Serial.print(F("{\"t\":")); Serial.print(millis()/1000);

  // --- ZONE A (Filter) ---
  Serial.print(F(",\"zA\":{"));
    // 센서 객체(zA_t1_ph 등)를 넘기지 않고, sysState.za_t1 배열의 값을 넘김
    print_tank("t1", sysState.za_t1, zA_t1_ph.get_flags(), zA_t1_turb.get_flags(), zA_t1_lvl.get_flags(), zA_t1_temp.get_flags());
    Serial.print(F(","));
    print_tank("t2", sysState.za_t2, zA_t2_ph.get_flags(), zA_t2_turb.get_flags(), zA_t2_lvl.get_flags(), zA_t2_temp.get_flags());
    Serial.print(F(","));
    print_tank("t3", sysState.za_t3, zA_t3_ph.get_flags(), zA_t3_turb.get_flags(), zA_t3_lvl.get_flags(), zA_t3_temp.get_flags());
  Serial.print(F("}"));

  // --- ZONE B (Nutrient) ---
  Serial.print(F(",\"zB\":{"));
    print_tankB("t1", sysState.zb_t1, zB_t1_ph.get_flags(), zB_t1_ec.get_flags(), zB_t1_do.get_flags(), zB_t1_temp.get_flags());
    Serial.print(F(","));
    print_tankB("t2", sysState.zb_t2, zB_t2_ph.get_flags(), zB_t2_ec.get_flags(), zB_t2_do.get_flags(), zB_t2_temp.get_flags());
    Serial.print(F(","));
    print_tankB("t3", sysState.zb_t3, zB_t3_ph.get_flags(), zB_t3_ec.get_flags(), zB_t3_do.get_flags(), zB_t3_temp.get_flags());
  Serial.print(F("}"));

  // --- ZONE C (Line) ---
  Serial.print(F(",\"zC\":{"));
    print_value_flag("s", sysState.zc[0], zC_start_ec.get_flags(), true);
    print_value_flag("m", sysState.zc[1], zC_mid_ec.get_flags(), true);
    print_value_flag("e", sysState.zc[2], zC_end_ec.get_flags(), false);
  Serial.print(F("}"));

  Serial.print(F(",\"st\":\"")); Serial.print(sysState.status); Serial.print(F("\""));
  Serial.println(F("}"));
}

// [수정됨] Tank A 출력 함수: 값 배열과 플래그를 인자로 받음
void print_tank(const char* name, float* values, uint8_t f_ph, uint8_t f_turb, uint8_t f_lvl, uint8_t f_temp){
  Serial.print(F("\"")); Serial.print(name); Serial.print(F("\":{"));
  // values[0]:PH, [1]:Turb, [2]:Lvl, [3]:Temp (read_all_sensors 저장 순서 따름)
  print_value_flag("ph", values[0], f_ph, true);
  print_value_flag("tr", values[1], f_turb, true);
  print_value_flag("lv", values[2], f_lvl, true);
  print_value_flag("t",  values[3], f_temp, false); 
  Serial.print(F("}"));
}

// [수정됨] Tank B 출력 함수
void print_tankB(const char* name, float* values, uint8_t f_ph, uint8_t f_ec, uint8_t f_do, uint8_t f_temp){
  Serial.print(F("\"")); Serial.print(name); Serial.print(F("\":{"));
  // values[0]:PH, [1]:EC, [2]:DO, [3]:Temp
  print_value_flag("ph", values[0], f_ph, true);
  print_value_flag("ec", values[1], f_ec, true);
  print_value_flag("do", values[2], f_do, true);
  print_value_flag("t",  values[3], f_temp, false);
  Serial.print(F("}"));
}

void print_value_flag(const char* key, float v, uint8_t f, bool comma){
  Serial.print(F("\"")); Serial.print(key); Serial.print(F("\":{"));
  Serial.print(F("\"v\":")); Serial.print(v, 2); 
  Serial.print(F(",\"f\":")); Serial.print(f);
  Serial.print(F("}"));
  if (comma) Serial.print(F(","));
}

void log_to_sd() {
    // Placeholder logic from original file
    if (DEBUG_SERIAL) Serial.println(F("[SD] Logging to SD card... (Placeholder)"));
}

void handle_serial_command() {
    // Placeholder logic from original file
    // Actual implementation depends on sensors.cpp mapping
    if (DEBUG_SERIAL) Serial.println(F("[SERIAL] Command received. (Placeholder)"));
    // To be implemented: Read Serial string, parse command, call sensor.calibrate()
}