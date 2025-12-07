/**
 * Aquaponics Smart Farm - Arduino Configuration
 * * [Reflected Documentation]
 * - HARDWARE_SETUP.md: 4x ADS1115 Addressing & Channel Mapping
 * - README.md: Alert Thresholds (EC Saturation, Level Cutoff)
 * - CALIBRATION.md: Calibration defaults (1413uS, etc.)
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
// I2C ADDRESS CONFIGURATION (ADS1115)
// Ref: HARDWARE_SETUP.md Section 2
// ============================================================
#define ADS_ADDR_ZONE_A     0x48 // Filter Tanks (pH)
#define ADS_ADDR_ZONE_B1    0x49 // Nutrient Tank 1 (All) + Tank 2 (pH)
#define ADS_ADDR_ZONE_B2    0x4A // Nutrient Tank 2 (EC, DO) + Tank 3 (pH, EC)
#define ADS_ADDR_ZONE_B3    0x4B // Nutrient Tank 3 (DO) + Line (EC)

// ============================================================
// SENSOR PIN & CHANNEL ASSIGNMENTS
// ============================================================

// --- ZONE A: Filtered Water Tanks (3 Tanks) ---
// ADS1115 (0x48) used for pH
// Native Pins used for Turbidity (A) & Level (24V->5V)
// Digital Pins used for Temp

// Tank 1
#define CH_A_TANK1_PH       0       // ADS(0x48) Ch 0
#define PIN_A_TANK1_TURB    A0      // Native A0
#define PIN_A_TANK1_LEVEL   A1      // Native A1
#define PIN_A_TANK1_TEMP    2       // Digital D2

// Tank 2
#define CH_A_TANK2_PH       1       // ADS(0x48) Ch 1
#define PIN_A_TANK2_TURB    A2      // Native A2
#define PIN_A_TANK2_LEVEL   A3      // Native A3
#define PIN_A_TANK2_TEMP    3       // Digital D3

// Tank 3
#define CH_A_TANK3_PH       2       // ADS(0x48) Ch 2
#define PIN_A_TANK3_TURB    A4      // Native A4
#define PIN_A_TANK3_LEVEL   A5      // Native A5
#define PIN_A_TANK3_TEMP    4       // Digital D4

// --- ZONE B: Nutrient Tanks (3 Tanks) ---
// Complex mapping across 3 ADS modules (0x49, 0x4A, 0x4B)
// Digital Pins used for Temp

// Tank 1
#define CH_B_TANK1_PH       0       // ADS(0x49) Ch 0
#define CH_B_TANK1_EC       1       // ADS(0x49) Ch 1
#define CH_B_TANK1_DO       2       // ADS(0x49) Ch 2
#define PIN_B_TANK1_TEMP    5       // Digital D5

// Tank 2
#define CH_B_TANK2_PH       3       // ADS(0x49) Ch 3
#define CH_B_TANK2_EC       0       // ADS(0x4A) Ch 0
#define CH_B_TANK2_DO       1       // ADS(0x4A) Ch 1
#define PIN_B_TANK2_TEMP    6       // Digital D6

// Tank 3
#define CH_B_TANK3_PH       2       // ADS(0x4A) Ch 2
#define CH_B_TANK3_EC       3       // ADS(0x4A) Ch 3
#define CH_B_TANK3_DO       0       // ADS(0x4B) Ch 0
#define PIN_B_TANK3_TEMP    7       // Digital D7

// --- ZONE C: Cultivation Line (EC Gradient) ---
// All on ADS(0x4B)
#define CH_C_START_EC       1       // ADS(0x4B) Ch 1
#define CH_C_MID_EC         2       // ADS(0x4B) Ch 2
#define CH_C_END_EC         3       // ADS(0x4B) Ch 3

// --- SYSTEM PINS ---
#define PIN_WATCHDOG_LED    13      // Heartbeat
#define PIN_BUZZER          40      // Optional Alert

// ============================================================
// SYSTEM CONSTANTS
// ============================================================
#define SERIAL_BAUD_RATE        115200
#define READ_INTERVAL_MS        1000    // Main loop delay
#define SENSOR_STABILIZE_MS     10      // Delay between mux switches

// ============================================================
// CALIBRATION DEFAULTS
// Ref: CALIBRATION.md
// ============================================================

// pH (3-Point)
#define PH_REF_LOW              4.0
#define PH_REF_MID              7.0
#define PH_REF_HIGH             10.0

// EC (1-Point)
#define EC_REF_STANDARD         1413.0  // 1413 uS/cm
#define EC_HARDWARE_LIMIT       2000.0  // SEN0451 K=1 Saturation Limit

// DO (2-Point)
#define DO_REF_ZERO             0.0     // 0% Saturation
#define DO_REF_SPAN             100.0   // 100% Saturation

// Turbidity (Baseline)
#define TURB_REF_CLEAR          0.0     // 0 NTU

// ============================================================
// EEPROM MEMORY MAP
// Allocated 20 bytes per sensor to prevent overlap.
// Arduino Mega EEPROM: 4096 bytes
// ============================================================

// --- ZONE A (Filter Tanks) ---
// pH (Needs 12 bytes each)
#define ADDR_A_T1_PH            0
#define ADDR_A_T2_PH            20
#define ADDR_A_T3_PH            40

// Turbidity (Needs 4 bytes each)
#define ADDR_A_T1_TURB          60
#define ADDR_A_T2_TURB          80
#define ADDR_A_T3_TURB          100

// --- ZONE B (Nutrient Tanks) ---
// pH (12 bytes)
#define ADDR_B_T1_PH            120
#define ADDR_B_T2_PH            140
#define ADDR_B_T3_PH            160

// EC (4 bytes)
#define ADDR_B_T1_EC            180
#define ADDR_B_T2_EC            200
#define ADDR_B_T3_EC            220

// DO (4 bytes)
#define ADDR_B_T1_DO            240
#define ADDR_B_T2_DO            260
#define ADDR_B_T3_DO            280

// --- ZONE C (Line) ---
// EC (4 bytes)
#define ADDR_C_START_EC         300
#define ADDR_C_MID_EC           320
#define ADDR_C_END_EC           340

// Total used: ~360 bytes (out of 4096) - Plenty of space

// ============================================================
// ALERT THRESHOLDS (Firmware Fallbacks)
// Ref: README.md
// ============================================================

// These define valid ranges. Readings outside might flag SENSOR_OUT_OF_RANGE
#define THRESH_PH_MIN           0.0
#define THRESH_PH_MAX           14.0

// Critical Hardware Safety
#define THRESH_EC_SATURATION    2000.0  // Flag SENSOR_SATURATED if > 2000
#define THRESH_LEVEL_LOW_CUTOFF 40.0    // % Pump Cutoff Risk

#endif // CONFIG_H