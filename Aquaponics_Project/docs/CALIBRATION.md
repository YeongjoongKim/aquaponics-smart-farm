# Aquaponics Smart Farm - Calibration Guide

## Introduction

Proper sensor calibration is critical for accurate water quality monitoring. This guide covers calibration procedures for all sensors across the **Multi-Zone System (3 Filter Tanks, 3 Nutrient Tanks, 1 Cultivation Line)**, ensuring alignment with the Dockerized backend logic.

**Note:** Most sensors are calibrated via the **Web Dashboard** or **API**, except for the **Water Level Sensor**, which requires physical adjustment on the module.

## Calibration Schedule & Methods

| Sensor | Model | Frequency | Method | Stability Goal |
| :--- | :--- | :--- | :--- | :--- |
| **pH** | SEN0169-V2 | Monthly | **Software** (3-Point) | ±0.1 pH |
| **EC** | SEN0451 | Monthly | **Software** (1-Point) | ±10 μS/cm |
| **DO** | SEN0237 | Quarterly | **Software** (2-Point) | ±0.5 mg/L |
| **Turbidity**| SEN0189 | Quarterly | **Software** (Baseline) | ±5 NTU |
| **Water Level**| KIT0139 | Quarterly | **Hardware** (Potentiometer) | ±1 % |
| **Temp** | DS18B20 | - | Factory Calibrated | - |

---

## pH Sensor Calibration (3-Point)

**Target Sensors:**
* **Zone A:** Filter Tanks 1, 2, 3 (3 Sensors)
* **Zone B:** Nutrient Tanks 1, 2, 3 (3 Sensors)

### Required Materials

1.  **Calibration Solutions:**
    * **pH 4.0** buffer solution (Acidic)
    * **pH 7.0** buffer solution (Neutral)
    * **pH 10.0** buffer solution (Alkaline)

2.  **Equipment:**
    * 3x Clean beakers (labeled 4.0, 7.0, 10.0)
    * Distilled water (for rinsing probe)
    * Soft tissue (for gently blotting, **do not rub**)
    * Web Dashboard or API Client (to submit values)

### Step-by-Step Procedure

#### 1. Prepare Calibration Solutions

```
1. Pour each buffer solution (4.0, 7.0, 10.0) into separate clean beakers.
2. Ensure solutions are at room temperature (approx. 25°C) for accuracy.
3. Rinse the probe with distilled water before starting.
```

#### 2. Access Calibration Interface

**Method A: Web Dashboard (Recommended)**
```
1. Open dashboard: http://<pi-ip>:5000
2. Navigate to **Settings > Calibration**.
3. Select the specific target sensor (e.g., "Zone B - Nutrient Tank 1 - pH").
4. You will see the "Live Raw ADC Value" updating in real-time.
```

**Method B: API (For Developers)**
```
1. Use a tool like Postman or Terminal.
2. Monitor real-time values: `curl http://localhost:5000/api/current`
3. Submit calibration command: `POST /api/calibration/<specific_sensor_id>`
   (e.g., `zone_b_tank1_ph`)
```

> **Important:** Do not disconnect the Arduino from the Raspberry Pi. Perform calibration while the system is connected and running via Docker.

#### 3. Calibration Process (Order: 7.0 → 4.0 → 10.0)

**Step 1: Mid-Point (pH 7.0 - Neutral)**
*Always start with 7.0 to establish the zero-offset.*

```
1. Dip the probe into **pH 7.0** solution.
2. Gently stir and wait 60 seconds for the "Raw ADC" value to stabilize.
3. Dashboard: Click **"Calibrate Mid (7.0)"**.
   (Or API: Send `{"points": {"mid": <current_raw_value>}}`)
4. Rinse probe with distilled water.
```

**Step 2: Low-Point (pH 4.0 - Acidic)**

```
1. Dip the probe into **pH 4.0** solution.
2. Wait 60 seconds for stabilization.
3. Dashboard: Click **"Calibrate Low (4.0)"**.
   (Or API: Send `{"points": {"low": <current_raw_value>}}`)
4. Rinse probe with distilled water.
```

**Step 3: High-Point (pH 10.0 - Alkaline)**
*Optional: Skip if your crop environment never exceeds pH 8.0.*

```
1. Dip the probe into **pH 10.0** solution.
2. Wait 60 seconds for stabilization.
3. Dashboard: Click **"Calibrate High (10.0)"**.
   (Or API: Send `{"points": {"high": <current_raw_value>}}`)
4. Final rinse with distilled water.
```

#### 4. Verify Calibration

```
1. Rinse the probe thoroughly and place it back in the pH 7.0 solution.
2. Verify the system reads **7.00 ± 0.1**.
3. If the error exceeds 0.2 pH, repeat the process.
4. Calibration constants (Slope/Intercept) are automatically saved to the SQLite Database.
```

### Troubleshooting pH Calibration

| Issue | Possible Cause | Solution |
| :--- | :--- | :--- |
| **Drifting Readings** | Old/Contaminated Buffer | Replace with fresh calibration solutions. |
| **Slow Response** | Biofilm on bulb | Clean probe gently with soft brush/water. |
| **Value > 14.0 or < 0.0** | Wiring/ADC Error | Check 5V/GND connections and ADS1115 mapping. |

---

## EC Sensor Calibration (1-Point)

**Target Sensors:**
* **Zone B:** Nutrient Tanks 1, 2, 3 (3 Sensors)
* **Zone C:** Cultivation Line Start, Middle, End (3 Sensors)

> **CRITICAL WARNING:** The SEN0451 (K=1.0) probe has a hardware limit of **2000 μS/cm (2.0 EC)**.
> * Do **NOT** use 12.88 mS/cm (12880 μS/cm) calibration solution.
> * Use **ONLY 1413 μS/cm** standard solution.
> * If your water exceeds 2.0 EC, this sensor will saturate (flatline).

### Required Materials

1.  **Calibration Solution:**
    * **1413 μS/cm** Standard Solution (1.413 EC)

2.  **Equipment:**
    * 1x Clean beaker
    * Distilled water (for cleaning)
    * Dry tissue (Probe must be dry before starting)

### Step-by-Step Procedure

#### 1. Prepare Calibration Solution

```
1. Pour 1413 μS/cm standard solution into a clean beaker.
2. Ensure the solution is at room temperature.
3. **CRITICAL:** Wash the probe with distilled water and **dry it completely** with a tissue.
   (Any water droplets left on the probe will dilute the standard solution and cause errors.)
```

#### 2. Calibration Process (1-Point Standard)

**Target:** 1413 μS/cm

```
1. Dip the dry probe into the **1413 μS/cm** solution.
2. Shake the probe gently in the liquid to dislodge any air bubbles trapped in the electrode.
3. Wait 60 seconds for the temperature compensation to stabilize.
4. Dashboard: Select specific sensor (e.g., "Nutrient Tank 1 EC") and click **"Calibrate 1413"**.
   (Or API: POST to `/api/calibration/zone_b_tank1_ec` with payload `{"points": {"standard": 1413}}`)
5. You should see the reading adjust to approximately 1413.
```

#### 3. Verification

```
1. Remove probe, rinse with distilled water, and dry.
2. Dip back into the 1413 solution.
3. Verify the reading is **1413 ± 20 μS/cm**.
4. If the error is large, repeat the process.
```

### EC Sensor Maintenance

**Probe Type:** Laboratory Grade K=1.0 (Graphite/Platinum)

```
Daily/Weekly:
- Rinse with clean tap water or distilled water after measuring.
- **Note:** Unlike pH sensors, EC probes can be stored dry.

Monthly (Biofilm Removal):
- In Aquaponics, organic biofilm (slime) can coat the electrodes, causing lower readings.
- Use a soft toothbrush with mild detergent to gently clean the black electrode area.
- Rinse thoroughly before use.

Troubleshooting:
- If readings stay at 0: Check wiring and ADS1115 connection.
- If readings stay at 2000: The water salinity exceeds the sensor limit (>2.0 EC). Dilute the water immediately.
```

---

## DO (Dissolved Oxygen) Sensor Calibration (2-Point)

**Target Sensors:** Zone B: Nutrient Tanks 1, 2, 3 (3 Sensors) - **Model: SEN0237**

> **Note:** For general aquaponics monitoring, **1-Point (100% Saturation)** calibration is often sufficient. Perform **2-Point (0% & 100%)** only if high precision at low oxygen levels is required.

### Required Materials

1.  **Calibration Solutions:**
    * **0% Standard:** **Sodium Sulfite ($Na_2SO_3$)** solution (dissolve until saturated). This creates an oxygen-free environment.
    * **100% Standard:** Air-saturated water (Prepare using an air pump/bubbler).

2.  **Equipment:**
    * 2x Clean beakers
    * **Air Pump & Airstone** (Critical for creating 100% saturation)
    * Distilled water

### Step-by-Step Procedure

#### 1. Prepare Calibration Standards

```
1. **0% Solution:** Dissolve Sodium Sulfite in water until no more dissolves.
2. **100% Solution:** Place an airstone in a beaker of water and pump air for at least 10 minutes.
3. **Probe Check:** Ensure the membrane cap is filled with 0.5mol/L NaOH solution and has no air bubbles inside.
```

#### 2. Zero Point Calibration (0%)
*Optional: Skip this step if you only need general accuracy > 4mg/L.*

```
1. Rinse the probe with distilled water.
2. Dip the probe into the **Sodium Sulfite (0%)** solution.
3. Wait at least 60 seconds until the reading stabilizes near 0.
4. Dashboard: Select specific sensor (e.g., "Nutrient Tank 1 DO") and click **"Calibrate Zero (0%)"**.
   (Or API: POST to `/api/calibration/zone_b_tank1_do` with payload `{"calibration_type": "2-point", "points": {"zero": <current_raw_value>}}`)
```

#### 3. Span Point Calibration (100% Saturation)

```
1. Rinse the probe thoroughly with distilled water to remove any Sodium Sulfite.
2. Suspend the probe in the **Air-Saturated Water (bubbling)**.
   (Do not let the probe touch the airstone directly).
3. Wait 60 seconds for the reading to stabilize.
4. Dashboard: Click **"Calibrate Span (100%)"**.
   (Or API: POST to `/api/calibration/zone_b_tank1_do` with payload `{"calibration_type": "2-point", "points": {"span": 100}}`)
5. The system automatically adjusts the slope based on the current temperature.
```

### DO Sensor Maintenance (Crucial)

**Model:** SEN0237 (Galvanic Probe)

| Frequency | Task | Procedure |
| :--- | :--- | :--- |
| **Weekly** | **Check Membrane** | Inspect the cap for dirt/biofilm. Wipe gently with a wet sponge. |
| **Monthly** | **Refill Solution** | 1. Unscrew the membrane cap.<br>2. Pour out old electrolyte.<br>3. Refill with **0.5mol/L NaOH** solution (~2/3 full).<br>4. Screw cap back on tightly (ensure no bubbles). |
| **Yearly** | **Replace Cap** | Replace the membrane cap if it is wrinkled, damaged, or readings are slow. |

> **Storage Warning:** Never let the membrane cap dry out. Keep the probe tip in water or a moist protective cap when not in use.

---

## Water Level Sensor Calibration (Hardware)

**Target Sensors:** Zone A: Filter Tanks 1, 2, 3 (3 Sensors)
**Model:** KIT0139 (Throw-in Type) + Current-to-Voltage Module

> **Hardware Adjustment Required:** Unlike other sensors, this sensor is calibrated by physically turning screws on the **I/V Converter Module** using a small screwdriver. Do not calibrate via software API.

### Prerequisites
1.  **Power:** Ensure the **24V Power Supply** is turned on.
2.  **Access:** You must have physical access to the I/V Converter Module inside the electronics box.
3.  **Safety:** Be careful not to short-circuit the 24V lines.
4.  **Dashboard:** Open the dashboard to view the specific tank's level (e.g., "Filter Tank 1 Level").

### Step-by-Step Procedure

Repeat this process for **each** of the 3 Filter Tanks.

#### 1. Zero Point (Empty State)

```
1. Lift the sensor probe out of the water (simulate 0cm depth).
2. Watch the specific "Filter Tank X Level" reading on the Dashboard.
3. Locate the **ZERO potentiometer** on the I/V Module corresponding to that sensor.
4. Turn the screw gently until the dashboard reading is **0%**.
   - If reading > 0%, turn counter-clockwise.
   - If reading stays 0% but acts dead, turn clockwise until it responds, then dial back to 0.
```

#### 2. Span Point (Full State)

```
1. Submerge the sensor to the **Maximum Depth** of the tank (e.g., 100cm).
   (Or use a bucket of known depth if the tank is empty).
2. Watch the Dashboard reading.
3. Locate the **SPAN potentiometer** on the I/V Module.
4. Turn the screw until the dashboard reading shows **100%** (or your max target).
```

#### 3. Verification

```
1. Move the sensor to ~50% depth.
2. Verify the dashboard shows approximately 50%.
3. If accurate, seal the electronics box and proceed to the next tank.
```

> **Note on Firmware:** The Arduino firmware maps the converted 0-5V analog signal directly to 0-100%. This hardware calibration ensures that 0cm water = 0V and Max water = 5V, aligning the physical voltage with the software logic.

---

## Turbidity Sensor Calibration (1-Point Baseline)

**Target Sensors:** Zone A: Filter Tanks 1, 2, 3 (3 Sensors)
**Model:** SEN0189 (Analog)

> **HARDWARE WARNING:**
> 1. **Not Waterproof:** The black connector on top of the probe is **NOT waterproof**. Only submerge the transparent prism part.
> 2. **Switch Setting:** Ensure the switch on the small adapter board is set to **"A"** (Analog), not "D".

### Required Materials

1.  **Calibration Standard:**
    * **Clear Water** (Distilled water is best, or clean tap water) - Represents 0 NTU.
    * *Note: Commercial NTU standards (e.g., Formazin) are expensive and optional for general monitoring.*

2.  **Equipment:**
    * 1x Opaque container (Light interference can affect readings)

### Step-by-Step Procedure

Repeat this process for **each** of the 3 Filter Tanks.

#### 1. Setup Baseline (Clear Water)

```
1. Switch the adapter board to **"A"**.
2. Dip the probe into **Clear Water**.
   - **Caution:** Do not submerge the black wire connector.
3. Stir gently to remove air bubbles from the lens.
4. Cover the container to block external light (sunlight/lamps).
5. Wait 30 seconds for the reading to stabilize.
6. Dashboard: Select specific sensor (e.g., "Filter Tank 1 Turbidity") and click **"Calibrate Clear (0 NTU)"**.
   (Or API: POST to `/api/calibration/zone_a_tank1_turbidity` with payload `{"calibration_type": "baseline", "points": {"clear": 0}}`)
```

#### 2. Operational Verification

```
1. Place the sensor in slightly dirty water (or put your finger *near* the lens).
2. Verify the Turbidity value increases (Voltage drops, NTU goes up).
3. If the reading doesn't change, check if the switch is on "D".
```

### Turbidity Sensor Maintenance

```
Weekly:
- The optical lens gets dirty easily in fish tanks.
- Wipe the bottom prism lens gently with a soft cloth or toothbrush.
- Dirty lenses cause falsely high turbidity readings (High NTU).
```

---

## Reset to Factory Defaults

If a calibration goes wrong and readings become erratic, you can reset the sensor to its default factory slope/intercept.

```bash
# Reset specific sensor via API (Example: Zone B - Nutrient Tank 1 pH)
curl -X POST http://localhost:5000/api/calibration/zone_b_tank1_ph \
  -H "Content-Type: application/json" \
  -d '{"calibration_type": "reset"}'
```

---

## Calibration Validation

After calibration, verify accuracy using known water samples.

| Scenario | Expected Values | Note |
| :--- | :--- | :--- |
| **Tap/Fresh Water** | pH: 7.0-7.5, EC: <200 μS/cm, DO: 7-9 mg/L | Baseline check |
| **Aquaponics Optimal** | pH: 6.8-7.0, EC: 1200-1600 μS/cm, DO: >5.0 mg/L | Target operational range |
| **Sensor Limit** | **EC > 2000 μS/cm** | **DO NOT EXCEED.** Sensor will saturate. |

---

## Calibration Data Management

### View Calibration History

Check the last 10 calibration events to track sensor health (e.g., shrinking slope indicates an aging probe).

```bash
# Via API (Recommended) - Check Nutrient Tank 1 pH history
curl http://localhost:5000/api/calibration/zone_b_tank1_ph | python3 -m json.tool

# Via Database (Direct SQL)
sqlite3 data/aquaponics.db \
  "SELECT timestamp, sensor_id, calibration_type, valid FROM calibrations WHERE sensor_id='zone_b_tank1_ph' ORDER BY timestamp DESC LIMIT 5;"
```

### Export Calibration Log

Keep a record of calibration maintenance for compliance or debugging.

```bash
# Export specific sensor history to JSON
curl http://localhost:5000/api/calibration/zone_b_tank1_ph > zone_b_tank1_ph_calib.json

# Export ALL calibration records (CSV) via Export Endpoint
curl "http://localhost:5000/api/export?format=csv&type=calibration" > calibration_log.csv
```

---

## Seasonal Considerations & Maintenance

### Summer (High Temp / Biofilm)
- **Biofilm:** Warmer water promotes algae/bacteria growth on sensor probes.
- **Action:** Increase cleaning frequency of **pH** and **DO** probes to **Weekly**.
- **Temperature:** Ensure water does not exceed 28°C (Risk of root rot).

### Winter (Low Temp)
- **Response Time:** Chemical sensors (pH/EC) react slower in cold water (<15°C).
- **Protection:**
    - **Never use Antifreeze** (Toxic to fish/plants).
    - Use submersible tank heaters to maintain min 18°C.
    - Insulate pipes to prevent freezing.

### Spring/Fall (Fluctuation)
- **Wide Swings:** Large day/night temp differences can cause condensation in the electronics box.
- **Action:** Check **Desiccant (Silica Gel)** inside the enclosure to protect the Arduino Mega.

---

## Automatic Temperature Compensation (ATC)

The system automatically corrects raw sensor readings based on the **DS18B20** temperature data **specific to that tank**.

### How it works (Firmware Logic)

1.  **EC (Electrical Conductivity):**
    - Standardized to 25°C.
    - Formula: `EC_25 = EC_raw / (1.0 + 0.02 * (Temp - 25.0))`
    - *Note:* It uses the specific temperature of the tank where the EC probe is located. If the temp sensor fails (-127), ATC defaults to 25°C.

2.  **pH (Slope Adjustment):**
    - Nernst equation correction.
    - Adjusts the millivolt-per-pH slope based on temperature.

3.  **DO (Dissolved Oxygen):**
    - Compensates for oxygen solubility changes (Cold water holds more O2).

---

## Verifying Accuracy (Cross-Check)

Instead of expensive lab tests, use a reliable **Handheld Meter** or **Chemical Test Kit** for regular validation.

### Validation Procedure

```
1. Take a water sample from a specific tank (e.g., Zone B - Nutrient Tank 1).
2. Measure immediately with the Smart Farm System (Record value from Dashboard).
3. Measure the same sample with a calibrated Handheld Pen (e.g., BlueLab/Xiaomi).
4. Compare results.
```

| Sensor | Acceptable Deviation | Action if Failed |
| :--- | :--- | :--- |
| **pH** | ±0.2 pH | Clean probe & Recalibrate (3-Point) |
| **EC** | ±50 μS/cm | Clean probe & Recalibrate (1-Point) |
| **Temp** | ±0.5 °C | Check DS18B20 wiring/position |

> **Pro Tip:** If the Smart Farm sensor consistently reads higher/lower than the handheld pen, the probe may be dirty or aging. **Clean first, then recalibrate.**

---

## Maintenance Log Template

Keep a physical record of calibration events to cross-reference with the digital database.

```
Date: _______________________
Zone/Tank ID: _______________ (e.g., zone_b_tank1, zone_a_tank3)
Sensor Type: ________________ (e.g., pH, EC, Level)
Calibration Method: _________ (e.g., 3-point, Hardware Screw)
Values Before: ______________
Values After: _______________
Result: Pass / Fail
Technician: _________________
```

---

## Reference Values

### Optimal Aquaponics Parameters
*(Target ranges based on `config.json` settings)*

```
pH: 6.8 - 7.0 (Optimal) / 6.0 - 8.0 (Safe)
EC: 1200 - 1600 μS/cm (Warning if > 1800, Max 2000)
Temperature: 20 - 26°C
DO: > 5.0 mg/L (Critical < 3.0)
Water Level: 80 - 100% (Stop Pump < 40%)
Turbidity: < 50 NTU (Clear water goal)
```

> **Note:** Parameters like Nitrogen, Potassium, and Phosphorus require manual chemical testing as they are not measured by the installed sensors.

### Sensor Specifications & Accuracy

| Sensor | Model | Accuracy | Range |
| :--- | :--- | :--- | :--- |
| **pH** | SEN0169-V2 | ±0.1 pH | 0 ~ 14 |
| **EC** | SEN0451 | ±1% F.S. | 0 ~ **2000 μS/cm** (Saturation Limit) |
| **Temp** | DS18B20 | ±0.5°C | -10 ~ +85°C |
| **DO** | SEN0237 | ±0.1 mg/L | 0 ~ 20 mg/L |
| **Level**| KIT0139 | <1mm | 0 ~ 5m (Depth) |
| **Turbidity**| SEN0189 | Qualitative | 0 ~ 3000 NTU |

---

## Support

If calibration fails repeatedly:
1.  **Check Diagnostics:** Refer to `TROUBLESHOOTING.md`.
2.  **Inspect Hardware:**
    * Is the probe dirty? (Biofilm buildup is common in nutrient tanks)
    * Is the connector wet? (Turbidity sensor issue)
    * Is the power stable? (24V for Level, 5V for others)
3.  **Verify Solutions:** Ensure buffer solutions are not expired or contaminated.
4.  **Replace Probe:** Sensors are consumables. pH/EC probes typically last 6-12 months in continuous use.