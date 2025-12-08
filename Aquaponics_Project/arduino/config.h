#pragma once

/**
 * Aquaponics Smart Farm - Arduino Configuration (Finalized)
 * - Centralized EC Limits
 * - Sensor Filtering Parameters
 * - DS18B20 Resolution (used in sensors.h)
 */

#ifndef CONFIG_H
#define CONFIG_H

// ============================================================
// GLOBAL SENSOR FLAG CODES (for JSON output)
// ============================================================
#define FLAG_OK           0
#define FLAG_DISCONNECTED 1
#define FLAG_SATURATED    2

// DS18B20 async conversion wait (ms, for non-blocking pattern)
// 12-bit resolution takes max 750ms.
#define TEMP_CONVERT_MS   750


// ============================================================
// SYSTEM SETTINGS & DEBUG
// ============================================================
#define FIRMWARE_VERSION        "1.6.1"
#define DEBUG_MODE              true
#define SERIAL_BAUD_RATE        115200
#define READ_INTERVAL_MS        1000
#define SENSOR_STABILIZE_MS     20


// ============================================================
// SENSOR SAMPLING / FILTERING
// ============================================================

// Raw sampling settings: Reads N samples with delay, then averages
#define SENSOR_SAMPLES          10
#define SENSOR_SAMPLE_DELAY_MS  5     // per sample

// Low-Pass Filter Alpha (0.0 ~ 1.0)
// Lower value = Stronger filter (Slower response, smoother data)
// Higher value = Weaker filter (Faster response, more noise)
#define SENSOR_FILTER_ALPHA_PH      0.10    // Slow chemical change
#define SENSOR_FILTER_ALPHA_EC      0.10    // Slow chemical change
#define SENSOR_FILTER_ALPHA_DO      0.10    // Slow chemical change
#define SENSOR_FILTER_ALPHA_TEMP    0.20    // Moderate thermal inertia
#define SENSOR_FILTER_ALPHA_LEVEL   0.30    // Water surface ripples
#define SENSOR_FILTER_ALPHA_TURB    0.30    // Suspension variance

// Temperature sensor resolution (9–12 bits)
// 12-bit = 0.0625°C resolution (slowest), 9-bit = 0.5°C (fastest)
#define TEMP_DS18_RESOLUTION    12


// ============================================================
// I2C ADDRESS CONFIG (ADS1115)
// ============================================================
#define ADS_ADDR_ZONE_A     0x48
#define ADS_ADDR_ZONE_B1    0x49
#define ADS_ADDR_ZONE_B2    0x4A
#define ADS_ADDR_ZONE_B3    0x4B

#include <Adafruit_ADS1X15.h>

#define ADS_GAIN_SETTING    GAIN_TWOTHIRDS
#define ADS_VOLTAGE_MAX     6.144
#define ADS_BIT_RESOLUTION  32768.0


// ============================================================
// SENSOR PIN / CHANNEL
// ============================================================

// --- ZONE A (Filter Tanks)
#define CH_A_TANK1_PH       0
#define PIN_A_TANK1_TURB    A0
#define PIN_A_TANK1_LEVEL   A1
#define PIN_A_TANK1_TEMP    2

#define CH_A_TANK2_PH       1
#define PIN_A_TANK2_TURB    A2
#define PIN_A_TANK2_LEVEL   A3
#define PIN_A_TANK2_TEMP    3

#define CH_A_TANK3_PH       2
#define PIN_A_TANK3_TURB    A4
#define PIN_A_TANK3_LEVEL   A5
#define PIN_A_TANK3_TEMP    4

// --- ZONE B (Nutrient Tanks)
#define CH_B_TANK1_PH       0
#define CH_B_TANK1_EC       1
#define CH_B_TANK1_DO       2
#define PIN_B_TANK1_TEMP    5

#define CH_B_TANK2_PH       3
#define CH_B_TANK2_EC       0
#define CH_B_TANK2_DO       1
#define PIN_B_TANK2_TEMP    6

#define CH_B_TANK3_PH       2
#define CH_B_TANK3_EC       3
#define CH_B_TANK3_DO       0
#define PIN_B_TANK3_TEMP    7

// --- ZONE C (EC Gradient)
#define CH_C_START_EC       1
#define CH_C_MID_EC         2
#define CH_C_END_EC         3


// ============================================================
// SYSTEM PINS
// ============================================================
#define PIN_WATCHDOG_LED    13
#define PIN_BUZZER          40


// ============================================================
// CALIBRATION REFERENCE
// ============================================================
#define PH_REF_LOW          4.0
#define PH_REF_MID          7.0
#define PH_REF_HIGH         10.0

#define EC_REF_STANDARD     1413.0
#define DO_REF_ZERO         0.0
#define DO_REF_SPAN         100.0

#define TURB_REF_CLEAR      0.0


// ============================================================
// EEPROM MAP
// ============================================================
#define EEPROM_MAGIC        0xAB
#define ADDR_MAGIC          0

#define ADDR_A_T1_PH        10
#define ADDR_A_T2_PH        30
#define ADDR_A_T3_PH        50
#define ADDR_A_T1_TURB      70
#define ADDR_A_T2_TURB      90
#define ADDR_A_T3_TURB      110

#define ADDR_B_T1_PH        130
#define ADDR_B_T2_PH        150
#define ADDR_B_T3_PH        170
#define ADDR_B_T1_EC        190
#define ADDR_B_T2_EC        210
#define ADDR_B_T3_EC        230
#define ADDR_B_T1_DO        250
#define ADDR_B_T2_DO        270
#define ADDR_B_T3_DO        290

#define ADDR_C_START_EC     310
#define ADDR_C_MID_EC       330
#define ADDR_C_END_EC       350


// ============================================================
// LIMITS & ALERTS (CENTRALIZED)
// ============================================================

// [NEW] Single Source of Truth for EC Hardware Saturation
// Used by ECSensor to clamp values and set FLAG_SATURATED
#define EC_HARDWARE_LIMIT   2000.0

// [Legacy] Kept for backward compatibility if needed, but prefer EC_HARDWARE_LIMIT
#define EC_LIMIT            2000.0

#define HARD_TEMP_MIN       -10.0
#define HARD_TEMP_MAX       80.0

// SOFT ALERT threshold (Software Logic Use)
#define ALERT_LEVEL_LOW     40.0
#define ALERT_PH_LOW        5.5
#define ALERT_PH_HIGH       8.5
#define ALERT_DO_LOW        4.5
#define ALERT_EC_HIGH       1800.0

#endif