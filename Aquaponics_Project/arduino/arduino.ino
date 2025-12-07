/**
 * Aquaponics Smart Farm - Arduino Main Sketch
 * Real-time water quality monitoring system (Zone A/B/C)
 * Target: Arduino Mega 2560
 * * [Reflected Documentation]
 * - HARDWARE_SETUP.md: 4x ADS1115 Integration (I2C)
 * - config.h: New Pin/Channel definitions
 * - sensors.h: Updated constructors with ADS pointers
 */

#include "config.h"
#include "sensors.h"

#include <Wire.h>
#include <SD.h>
#include <avr/wdt.h>  // Watchdog Timer
#include <Adafruit_ADS1X15.h>

// ============================================================
// I2C EXPANSION OBJECTS (4x ADS1115)
// ============================================================
Adafruit_ADS1115 ads_zone_a;   // Filter Tanks
Adafruit_ADS1115 ads_zone_b1;  // Nutrient Tank 1 & 2
Adafruit_ADS1115 ads_zone_b2;  // Nutrient Tank 2 & 3
Adafruit_ADS1115 ads_zone_b3;  // Nutrient Tank 3 & Line

// ============================================================
// GLOBAL SENSOR OBJECTS
// Constructors: Sensor(Pin/Ch, &ADS_Obj, EEPROM_Addr)
// ============================================================

// --- ZONE A: Filtered Water Tanks (3 Tanks) ---
// pH uses ADS_ZONE_A. Turbidity/Level use Native Pins.
// Tank 1
PHSensor          zA_t1_ph(CH_A_TANK1_PH, &ads_zone_a, ADDR_A_T1_PH);
TurbiditySensor   zA_t1_turb(PIN_A_TANK1_TURB, ADDR_A_T1_TURB);
WaterLevelSensor  zA_t1_lvl(PIN_A_TANK1_LEVEL);
TemperatureSensor zA_t1_temp(PIN_A_TANK1_TEMP);

// Tank 2
PHSensor          zA_t2_ph(CH_A_TANK2_PH, &ads_zone_a, ADDR_A_T2_PH);
TurbiditySensor   zA_t2_turb(PIN_A_TANK2_TURB, ADDR_A_T2_TURB);
WaterLevelSensor  zA_t2_lvl(PIN_A_TANK2_LEVEL);
TemperatureSensor zA_t2_temp(PIN_A_TANK2_TEMP);

// Tank 3
PHSensor          zA_t3_ph(CH_A_TANK3_PH, &ads_zone_a, ADDR_A_T3_PH);
TurbiditySensor   zA_t3_turb(PIN_A_TANK3_TURB, ADDR_A_T3_TURB);
WaterLevelSensor  zA_t3_lvl(PIN_A_TANK3_LEVEL);
TemperatureSensor zA_t3_temp(PIN_A_TANK3_TEMP);

// --- ZONE B: Nutrient Tanks (3 Tanks) ---
// Complex mapping across 3 ADS modules. Ref: config.h
// Tank 1
PHSensor          zB_t1_ph(CH_B_TANK1_PH, &ads_zone_b1, ADDR_B_T1_PH);
ECSensor          zB_t1_ec(CH_B_TANK1_EC, &ads_zone_b1, ADDR_B_T1_EC);
DOSensor          zB_t1_do(CH_B_TANK1_DO, &ads_zone_b1, ADDR_B_T1_DO);
TemperatureSensor zB_t1_temp(PIN_B_TANK1_TEMP);

// Tank 2
PHSensor          zB_t2_ph(CH_B_TANK2_PH, &ads_zone_b1, ADDR_B_T2_PH);
ECSensor          zB_t2_ec(CH_B_TANK2_EC, &ads_zone_b2, ADDR_B_T2_EC);
DOSensor          zB_t2_do(CH_B_TANK2_DO, &ads_zone_b2, ADDR_B_T2_DO);
TemperatureSensor zB_t2_temp(PIN_B_TANK2_TEMP);

// Tank 3
PHSensor          zB_t3_ph(CH_B_TANK3_PH, &ads_zone_b2, ADDR_B_T3_PH);
ECSensor          zB_t3_ec(CH_B_TANK3_EC, &ads_zone_b2, ADDR_B_T3_EC);
DOSensor          zB_t3_do(CH_B_TANK3_DO, &ads_zone_b3, ADDR_B_T3_DO);
TemperatureSensor zB_t3_temp(PIN_B_TANK3_TEMP);

// --- ZONE C: Cultivation Line (EC Gradient) ---
// All on ADS_ZONE_B3
ECSensor          zC_start_ec(CH_C_START_EC, &ads_zone_b3, ADDR_C_START_EC);
ECSensor          zC_mid_ec(CH_C_MID_EC, &ads_zone_b3, ADDR_C_MID_EC);
ECSensor          zC_end_ec(CH_C_END_EC, &ads_zone_b3, ADDR_C_END_EC);

// --- System Globals ---
File data_file;
unsigned long last_reading_time = 0;
unsigned long last_sd_write_time = 0;

// SD Log config
#define SD_LOG_INTERVAL 600 
#define SD_DATA_FILENAME "datalog.csv"
#define ENABLE_SD_LOGGING true
#define DEBUG_SERIAL true

// Data Structure (Updated for 3 Nutrient Tanks)
struct SystemState {
  // Zone A (Filter)
  float za_t1[4]; // pH, Turb, Lvl, Temp
  float za_t2[4];
  float za_t3[4];
  // Zone B (Nutrient)
  float zb_t1[4]; // pH, EC, DO, Temp
  float zb_t2[4];
  float zb_t3[4];
  // Zone C (Line)
  float zc[3];    // Start, Mid, End
  String status;
} sysState;

// ============================================================
// SETUP
// ============================================================

void setup() {
  wdt_disable(); // Disable watchdog during setup

  Serial.begin(SERIAL_BAUD_RATE);
  // Wait for Serial to stabilize
  delay(2000); 
  if (DEBUG_SERIAL) Serial.println(F("=== Aquaponics System Booting (Multi-Zone) ==="));

  // 1. Initialize ADS1115 Modules
  if (DEBUG_SERIAL) Serial.println(F("[INIT] Starting I2C & ADS1115..."));
  
  bool ads_ok = true;
  if (!ads_zone_a.begin(ADS_ADDR_ZONE_A))  { Serial.println(F("ERR: ADS Zone A Failed")); ads_ok = false; }
  if (!ads_zone_b1.begin(ADS_ADDR_ZONE_B1)) { Serial.println(F("ERR: ADS Zone B1 Failed")); ads_ok = false; }
  if (!ads_zone_b2.begin(ADS_ADDR_ZONE_B2)) { Serial.println(F("ERR: ADS Zone B2 Failed")); ads_ok = false; }
  if (!ads_zone_b3.begin(ADS_ADDR_ZONE_B3)) { Serial.println(F("ERR: ADS Zone B3 Failed")); ads_ok = false; }

  if (ads_ok && DEBUG_SERIAL) Serial.println(F("[INIT] All ADS1115 Modules OK"));

  // 2. Initialize SD Card
  pinMode(SD_CHIP_SELECT_PIN, OUTPUT);
  if (ENABLE_SD_LOGGING) {
    if (!SD.begin(SD_CHIP_SELECT_PIN)) {
      if (DEBUG_SERIAL) Serial.println(F("ERR: SD Card Failed"));
    } else {
      if (DEBUG_SERIAL) Serial.println(F("[INIT] SD Card Initialized"));
    }
  }

  // 3. Sensor Calibration Load
  // Handled automatically by constructors (Sensors load from EEPROM)

  if (DEBUG_SERIAL) Serial.println(F("[INIT] System Ready."));
  wdt_enable(WDTO_8S); // Enable 8-second watchdog
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {
  wdt_reset(); // Pet the watchdog

  unsigned long current_time = millis();

  // Handle Serial Commands (Calibration, etc.)
  if (Serial.available()) {
    handle_serial_command();
  }

  // Periodic Sensor Reading
  if (current_time - last_reading_time >= READ_INTERVAL_MS) {
    read_all_sensors();
    send_json_data();
    
    // Log to SD periodically
    if (ENABLE_SD_LOGGING && (current_time - last_sd_write_time >= (SD_LOG_INTERVAL * 1000UL))) {
      log_to_sd();
      last_sd_write_time = current_time;
    }

    last_reading_time = current_time;
  }
}

// ============================================================
// SENSOR LOGIC
// ============================================================

void read_all_sensors() {
  // 1. READ TEMPERATURES FIRST (For ATC)
  // ------------------------------------
  float tA1 = zA_t1_temp.read();
  float tA2 = zA_t2_temp.read();
  float tA3 = zA_t3_temp.read();
  
  float tB1 = zB_t1_temp.read();
  float tB2 = zB_t2_temp.read();
  float tB3 = zB_t3_temp.read();

  // Store temps
  sysState.za_t1[3] = tA1; sysState.za_t2[3] = tA2; sysState.za_t3[3] = tA3;
  sysState.zb_t1[3] = tB1; sysState.zb_t2[3] = tB2; sysState.zb_t3[3] = tB3;

  // 2. APPLY ATC (Automatic Temperature Compensation)
  // -----------------------------------------------
  // Zone A (pH only)
  if(tA1 > 0) zA_t1_ph.set_temperature(tA1);
  if(tA2 > 0) zA_t2_ph.set_temperature(tA2);
  if(tA3 > 0) zA_t3_ph.set_temperature(tA3);
  
  // Zone B (pH, EC, DO)
  if(tB1 > 0) { zB_t1_ph.set_temperature(tB1); zB_t1_ec.set_temperature(tB1); zB_t1_do.set_temperature(tB1); }
  if(tB2 > 0) { zB_t2_ph.set_temperature(tB2); zB_t2_ec.set_temperature(tB2); zB_t2_do.set_temperature(tB2); }
  if(tB3 > 0) { zB_t3_ph.set_temperature(tB3); zB_t3_ec.set_temperature(tB3); zB_t3_do.set_temperature(tB3); }

  // Zone C (EC Gradient) - Flows from Tank 3, use T3 temp
  if(tB3 > 0) {
    zC_start_ec.set_temperature(tB3);
    zC_mid_ec.set_temperature(tB3);
    zC_end_ec.set_temperature(tB3);
  }

  // 3. READ CHEMICAL/PHYSICAL SENSORS
  // ---------------------------------
  // Zone A
  sysState.za_t1[0] = zA_t1_ph.read(); sysState.za_t1[1] = zA_t1_turb.read(); sysState.za_t1[2] = zA_t1_lvl.read();
  sysState.za_t2[0] = zA_t2_ph.read(); sysState.za_t2[1] = zA_t2_turb.read(); sysState.za_t2[2] = zA_t2_lvl.read();
  sysState.za_t3[0] = zA_t3_ph.read(); sysState.za_t3[1] = zA_t3_turb.read(); sysState.za_t3[2] = zA_t3_lvl.read();

  // Zone B
  sysState.zb_t1[0] = zB_t1_ph.read(); sysState.zb_t1[1] = zB_t1_ec.read(); sysState.zb_t1[2] = zB_t1_do.read();
  sysState.zb_t2[0] = zB_t2_ph.read(); sysState.zb_t2[1] = zB_t2_ec.read(); sysState.zb_t2[2] = zB_t2_do.read();
  sysState.zb_t3[0] = zB_t3_ph.read(); sysState.zb_t3[1] = zB_t3_ec.read(); sysState.zb_t3[2] = zB_t3_do.read();

  // Zone C
  sysState.zc[0] = zC_start_ec.read();
  sysState.zc[1] = zC_mid_ec.read();
  sysState.zc[2] = zC_end_ec.read();

  // Status Check
  sysState.status = "OK";
  if (tA1 == -127 || tB1 == -127) sysState.status = "ERR_TEMP";
}

void send_json_data() {
  // Nested JSON Format: {"zA": {"t1": ...}, "zB": {"t1": ...}, "zC": ...}
  Serial.print(F("{\"t\":")); Serial.print(millis()/1000);
  
  // Zone A
  Serial.print(F(",\"zA\":{"));
    print_tank_json("t1", sysState.za_t1, true, true); Serial.print(F(","));
    print_tank_json("t2", sysState.za_t2, true, true); Serial.print(F(","));
    print_tank_json("t3", sysState.za_t3, true, true);
  Serial.print(F("}"));

  // Zone B
  Serial.print(F(",\"zB\":{"));
    print_tank_json_b("t1", sysState.zb_t1); Serial.print(F(","));
    print_tank_json_b("t2", sysState.zb_t2); Serial.print(F(","));
    print_tank_json_b("t3", sysState.zb_t3);
  Serial.print(F("}"));

  // Zone C
  Serial.print(F(",\"zC\":{"));
    Serial.print(F("\"s\":")); Serial.print(sysState.zc[0], 0);
    Serial.print(F(",\"m\":")); Serial.print(sysState.zc[1], 0);
    Serial.print(F(",\"e\":")); Serial.print(sysState.zc[2], 0);
  Serial.print(F("}"));

  Serial.print(F(",\"st\":\"")); Serial.print(sysState.status); Serial.print(F("\""));
  Serial.println(F("}"));
}

// Helper for Zone A JSON (pH, Turb, Lvl, Temp)
void print_tank_json(String id, float* data, bool hasTurb, bool hasLvl) {
    Serial.print(F("\"")); Serial.print(id); Serial.print(F("\":{"));
    Serial.print(F("\"ph\":")); Serial.print(data[0], 2);
    if(hasTurb) { Serial.print(F(",\"tb\":")); Serial.print(data[1], 0); }
    if(hasLvl)  { Serial.print(F(",\"lv\":")); Serial.print(data[2], 1); }
    Serial.print(F(",\"tp\":")); Serial.print(data[3], 1);
    Serial.print(F("}"));
}

// Helper for Zone B JSON (pH, EC, DO, Temp)
void print_tank_json_b(String id, float* data) {
    Serial.print(F("\"")); Serial.print(id); Serial.print(F("\":{"));
    Serial.print(F("\"ph\":")); Serial.print(data[0], 2);
    Serial.print(F(",\"ec\":")); Serial.print(data[1], 0);
    Serial.print(F(",\"do\":")); Serial.print(data[2], 2);
    Serial.print(F(",\"tp\":")); Serial.print(data[3], 1);
    Serial.print(F("}"));
}

// ============================================================
// SD LOGGING
// ============================================================

void log_to_sd() {
  data_file = SD.open(SD_DATA_FILENAME, FILE_WRITE);
  if (data_file) {
    data_file.print(millis()/1000); data_file.print(",");
    data_file.print(sysState.za_t1[0]); data_file.print(","); // ZA T1 pH
    data_file.print(sysState.zb_t1[1]); // ZB T1 EC
    // ... Add more columns as needed
    data_file.println();
    data_file.close();
  }
}

// ============================================================
// COMMAND HANDLING
// ============================================================

void handle_serial_command() {
  String input = Serial.readStringUntil('\n');
  input.trim();
  if (input.length() == 0) return;

  // Split Command: COMMAND_TARGET:PARAM:VALUE
  int idx1 = input.indexOf(':');
  if (idx1 == -1) return;
  String target = input.substring(0, idx1);
  String remainder = input.substring(idx1 + 1);
  int idx2 = remainder.indexOf(':');
  String param = (idx2 != -1) ? remainder.substring(0, idx2) : remainder;
  float val = (idx2 != -1) ? remainder.substring(idx2 + 1).toFloat() : 0.0;

  // Map Targets to Sensors
  // ZONE A (Filter)
  if      (target == "CALIB_ZA_T1_PH")   handle_ph_calib(zA_t1_ph, param, val);
  else if (target == "CALIB_ZA_T2_PH")   handle_ph_calib(zA_t2_ph, param, val);
  else if (target == "CALIB_ZA_T3_PH")   handle_ph_calib(zA_t3_ph, param, val);
  else if (target == "CALIB_ZA_T1_TURB") handle_turb_calib(zA_t1_turb, val);
  else if (target == "CALIB_ZA_T2_TURB") handle_turb_calib(zA_t2_turb, val);
  else if (target == "CALIB_ZA_T3_TURB") handle_turb_calib(zA_t3_turb, val);

  // ZONE B (Nutrient)
  else if (target == "CALIB_ZB_T1_PH")   handle_ph_calib(zB_t1_ph, param, val);
  else if (target == "CALIB_ZB_T2_PH")   handle_ph_calib(zB_t2_ph, param, val);
  else if (target == "CALIB_ZB_T3_PH")   handle_ph_calib(zB_t3_ph, param, val);
  
  else if (target == "CALIB_ZB_T1_EC")   handle_ec_calib(zB_t1_ec, param, val);
  else if (target == "CALIB_ZB_T2_EC")   handle_ec_calib(zB_t2_ec, param, val);
  else if (target == "CALIB_ZB_T3_EC")   handle_ec_calib(zB_t3_ec, param, val);

  else if (target == "CALIB_ZB_T1_DO")   handle_do_calib(zB_t1_do, val);
  else if (target == "CALIB_ZB_T2_DO")   handle_do_calib(zB_t2_do, val);
  else if (target == "CALIB_ZB_T3_DO")   handle_do_calib(zB_t3_do, val);

  // ZONE C (Line)
  else if (target == "CALIB_ZC_START")   handle_ec_calib(zC_start_ec, param, val);
  else if (target == "CALIB_ZC_MID")     handle_ec_calib(zC_mid_ec, param, val);
  else if (target == "CALIB_ZC_END")     handle_ec_calib(zC_end_ec, param, val);

  else if (target == "RESET") {
    wdt_enable(WDTO_15MS);
    while(1);
  }
}

// --- Calibration Helpers ---
void handle_ph_calib(PHSensor &sensor, String point, float val) {
  if (point == "LOW") sensor.set_calib_low(val);
  else if (point == "MID") sensor.set_calib_mid(val);
  else if (point == "HIGH") sensor.set_calib_high(val);
  sensor.save_calibration();
  Serial.println(F("{\"msg\":\"PH Saved\"}"));
}

void handle_ec_calib(ECSensor &sensor, String point, float val) {
  sensor.set_calib_standard(val);
  sensor.save_calibration();
  Serial.println(F("{\"msg\":\"EC Saved\"}"));
}

void handle_do_calib(DOSensor &sensor, float val) {
  sensor.set_calib_span(val);
  sensor.save_calibration();
  Serial.println(F("{\"msg\":\"DO Saved\"}"));
}

void handle_turb_calib(TurbiditySensor &sensor, float val) {
  sensor.set_calib_clear(val);
  sensor.save_calibration();
  Serial.println(F("{\"msg\":\"Turb Saved\"}"));
}