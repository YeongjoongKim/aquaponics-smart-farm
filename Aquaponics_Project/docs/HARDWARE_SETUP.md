# Aquaponics Smart Farm - Hardware Setup Guide

This document provides detailed wiring instructions for the **Multi-Zone Aquaponics System**, specifically tailored for the **Arduino Mega 2560** and **Raspberry Pi 4/5**.

Due to the expanded requirements (**3 Filter Tanks, 3 Nutrient Tanks, 1 Cultivation Line**), this system utilizes **4x ADS1115 (16-bit ADC) Modules** via I2C communication. This allows the system to handle high-precision analog sensors beyond the Arduino Mega's native capacity.

**CRITICAL SAFETY WARNINGS:**
1.  **24V Hazard:** Water Level Sensors (KIT0139) require **24V**. Connecting 24V directly to Arduino will destroy it. Use the I/V Converter.
2.  **I2C Addressing:** You must configure the 4 ADS1115 modules to have unique addresses (`0x48` ~ `0x4B`) using the ADDR pin jumpers.
3.  **Power:** Do not power sensors from the Arduino 5V pin. Use an **External 5V (3A+) Adapter**.

---

## 1. Bill of Materials (BOM)

### Core Controllers
| Component | Quantity | Description |
| :--- | :---: | :--- |
| **Raspberry Pi** | 1 | Model 4B or 5 (4GB+ RAM), 32GB+ SD Card |
| **Arduino Mega** | 1 | Mega 2560 R3 (Main Controller) |
| **ADS1115** | **4** | **16-bit ADC Module (4 Channels each)** for I2C Expansion |
| **USB Cable** | 1 | Type-A to Type-B (Shielded, Short length recommended) |

### Sensors (Multi-Zone Configuration)
| Sensor Type | Model | Quantity | Allocation |
| :--- | :--- | :---: | :--- |
| **pH** | SEN0169-V2 | **6** | 3x Filter Tanks, 3x Nutrient Tanks |
| **EC** | SEN0451 | **6** | 3x Nutrient Tanks, 3x Cultivation Line |
| **DO** | SEN0237 | **3** | 3x Nutrient Tanks |
| **Temp** | DS18B20 | **6** | 3x Filter Tanks, 3x Nutrient Tanks |
| **Level** | KIT0139 | **3** | 3x Filter Tanks (**24V Req**) |
| **Turbidity** | SEN0189 | **3** | 3x Filter Tanks |

### Power & Wiring
| Component | Quantity | Purpose |
| :--- | :---: | :--- |
| **External 5V PSU** | 1 | Powers 20+ sensors and ADS modules (**Min 3A, Rec 5A**) |
| **24V SMPS** | 1 | Power source for 3x Water Level Sensors (KIT0139) |
| **I/V Converter** | 3 | Converts 4-20mA current signal to 0-5V voltage (For KIT0139) |
| **Terminal Blocks** | 2-3 | For splitting 5V/GND power and SDA/SCL lines |
| **4.7kΩ Resistor** | 1 | Pull-up resistor for DS18B20 OneWire data line |
| **Enclosure** | 1 | IP67 Waterproof Box (Large size recommended for all modules) |

---

## 2. ADS1115 Configuration (Crucial)

To support **20+ analog sensors**, this system uses **4x ADS1115 modules** connected via I2C. You must configure unique addresses using the **ADDR** pin on each module.

| Module | **ADDR Pin Connection** | **I2C Address** | Allocated Zone |
| :---: | :---: | :---: | :--- |
| **#1** | Connect to **GND** | `0x48` | Zone A: Filter Tanks (pH) |
| **#2** | Connect to **VCC** | `0x49` | Zone B: Nutrient Tank 1 (All) + Tank 2 (pH) |
| **#3** | Connect to **SDA** | `0x4A` | Zone B: Nutrient Tank 2 (EC, DO) + Tank 3 (pH, EC) |
| **#4** | Connect to **SCL** | `0x4B` | Zone B: Nutrient Tank 3 (DO) + Zone C: Line (EC) |

**Wiring to Arduino Mega:**
* **VCC** -> External 5V
* **GND** -> Common GND
* **SCL** -> Pin 21
* **SDA** -> Pin 20

---

## 3. Pin Assignments

Ensure your physical wiring matches this table exactly. This mapping corresponds to `config.json`.

### Zone A: Filtered Water Tanks (3 Tanks)
* **Strategy:** Use **ADS1115** for precision pH, and **Native Analog Pins** for Level/Turbidity to save ADC channels.

| Tank ID | Sensor | Model | Connection Pin | Note |
| :---: | :---: | :---: | :---: | :--- |
| **Tank 1** | pH | SEN0169 | **ADS(0x48) - Ch 0** | Precision |
| | Turbidity | SEN0189 | **Native A0** | Analog Switch "A" |
| | Water Level | KIT0139 | **Native A1** | **24V -> I/V Conv** |
| | Temp | DS18B20 | **Digital D2** | |
| **Tank 2** | pH | SEN0169 | **ADS(0x48) - Ch 1** | |
| | Turbidity | SEN0189 | **Native A2** | |
| | Water Level | KIT0139 | **Native A3** | |
| | Temp | DS18B20 | **Digital D3** | |
| **Tank 3** | pH | SEN0169 | **ADS(0x48) - Ch 2** | |
| | Turbidity | SEN0189 | **Native A4** | |
| | Water Level | KIT0139 | **Native A5** | |
| | Temp | DS18B20 | **Digital D4** | |

### Zone B: Nutrient Tanks (3 Tanks)
* **Strategy:** High precision required. All chemical sensors use **ADS1115**.

| Tank ID | Sensor | Connection Pin | ADS Module Addr |
| :---: | :---: | :---: | :---: |
| **Tank 1** | pH | **ADS Ch 0** | **0x49** |
| | EC | **ADS Ch 1** | **0x49** |
| | DO | **ADS Ch 2** | **0x49** |
| | Temp | **Digital D5** | - |
| **Tank 2** | pH | **ADS Ch 3** | **0x49** |
| | EC | **ADS Ch 0** | **0x4A** |
| | DO | **ADS Ch 1** | **0x4A** |
| | Temp | **Digital D6** | - |
| **Tank 3** | pH | **ADS Ch 2** | **0x4A** |
| | EC | **ADS Ch 3** | **0x4A** |
| | DO | **ADS Ch 0** | **0x4B** |
| | Temp | **Digital D7** | - |

### Zone C: Cultivation Line (EC Gradient)
* **Strategy:** Monitors EC drop-off across the line.

| Position | Sensor | Model | Connection Pin | Note |
| :---: | :---: | :---: | :---: | :--- |
| **Start** | EC | SEN0451 | **ADS(0x4B) - Ch 1** | |
| **Middle**| EC | SEN0451 | **ADS(0x4B) - Ch 2** | |
| **End** | EC | SEN0451 | **ADS(0x4B) - Ch 3** | |

> **Summary**:
> * **ADS1115 Channels Used**: 15 Channels (Spread across 4 Modules)
> * **Native Analog Used**: A0 ~ A5 (6 Pins for Turbidity/Level)
> * **Digital Used**: D2 ~ D7 (6 Pins for Temp)

---

## 4. Detailed Wiring Diagrams

### Power Distribution (CRITICAL)
**Common Ground (GND) Rule:**
The **GND** of External 5V, **GND** of 24V PSU, and **GND** of Arduino **MUST ALL BE CONNECTED**.

```text
[ Ext 5V PSU ]       [ Ext 24V PSU ]        [ Arduino Mega ]
     (+) ──────────────────┐                       |
      |                    |                       |
     (-) ───────┬──────── (-) ─────────┬──────── [ GND ]
                |                      |
      [ Common Ground ]      [ ADS1115 GNDs ]
```

### A. I2C Bus (ADS1115 Chain)
To use 4 modules, daisy-chain the SDA/SCL lines or use a terminal block/breadboard.

```text
[ Arduino Mega ]      [ ADS #1 ]      [ ADS #2 ]      [ ADS #3 ] ...
   Pin 20 (SDA) ─────── SDA ─────────── SDA ─────────── SDA
   Pin 21 (SCL) ─────── SCL ─────────── SCL ─────────── SCL
        5V      ─────── VCC ─────────── VCC ─────────── VCC
       GND      ─────── GND ─────────── GND ─────────── GND
```
* **Note:** Remember to set the **ADDR** jumper differently for each module (`GND`, `VCC`, `SDA`, `SCL`) as defined in Section 2.

### B. Water Level (KIT0139) - 24V Loop
**DANGER:** Never connect 24V to Arduino. Use the I/V Converter.

```text
[ 24V PSU ]          [ KIT0139 Sensor ]           [ I/V Converter ]
   (+) ────────────────── [ Red ]
    |
    |                                            /── [ I+ Input ]
    |                     [ Black ] ────────────/
   (-) ───────────────────────────────────────────── [ I- Input ]
    |                                                    |
    └──────────────────── [ GND ] ────────────────── [ GND ]

                                                  [ Output to Arduino ]
                                                     [ VOUT ] ────> Native Pin A1 / A3 / A5
                                                     [ GND  ] ────> Common GND
```

### C. Turbidity Sensor (SEN0189)
Connect to Native Analog Pins. Ensure the adapter switch is set to **"A"**.

```text
[ Adapter Board ]          [ Arduino Mega ]
     VCC ────────────────────> Ext 5V
     GND ────────────────────> Common GND
     OUT ────────────────────> Native Pin A0 / A2 / A4
```

### D. Temperature (DS18B20) - Digital
Each sensor goes to a separate Digital Pin (D2 ~ D7). Use a 4.7kΩ pull-up resistor between VCC and Data.

```text
      [ Ext 5V ] ─────────────────────────┐
                                          |
      [ Arduino D2 ] ──────┬──────────────┼───── [ Sensor Red (VCC) ]
                           |              |
                        [4.7kΩ]           └───── [ Sensor Yellow (Data) ]
                           |
      [ Common GND ] ──────┴──────────────────── [ Sensor Black (GND) ]
```

---

## 4. Raspberry Pi Connection

1.  **Component Mounting (Layout):**
    * Secure the **Raspberry Pi**, **Arduino Mega**, **4x ADS1115 Modules**, and **I/V Converters** in the enclosure.
    * **Separation:** Keep the **24V Power lines** (Level Sensors) physically separated from the **5V Logic lines** (Pi/Arduino) to prevent noise and accidental shorts.
    * Use nylon standoffs for all boards.

2.  **Data Link:** Connect the USB Cable from **Arduino USB** to any **Raspberry Pi USB Port**.
    * **Recommendation:** Use a short (15-30cm) **shielded USB cable** with a ferrite bead to minimize electrical noise from the pumps/motors affecting the data stream.

3.  **Port Identification:**
    * The Pi usually identifies the Arduino as `/dev/ttyUSB0` (or sometimes `/dev/ttyACM0`).
    * Run this command to verify:
        ```bash
        ls -l /dev/ttyUSB*
        ```
    * **Permission Check:** Ensure your user (usually `pi`) has permission to access the port:
        ```bash
        groups $USER
        # Output should include 'dialout'. If not: sudo usermod -aG dialout $USER
        ```

---

## 5. Verification Steps (Critical)

Since this system uses a hybrid of **Native Analog Pins** and **External ADS1115 Modules**, verification is more complex. Follow this order:

### 1. I2C Bus Scan (First Step)
Before connecting sensors, ensure the Arduino can see all 4 ADC modules.
1.  Connect Arduino to PC.
2.  Open Arduino IDE Serial Monitor (115200 baud).
3.  Reset the Arduino. The firmware should print detected devices on startup.
4.  **Success:** You must see "Found ADS at 0x48, 0x49, 0x4A, 0x4B".
5.  **Failure:** If an address is missing, check the **ADDR jumper** wiring on that specific module.

### 2. Voltage Safety Check
* **External 5V Rail:** Must be stable (4.8V - 5.2V). **Do not use USB power alone** for 20+ sensors.
* **24V Rail:** Must be stable 24V.
* **Leakage Check:** Ensure NO 24V is present on Arduino 5V, GND, or Analog pins.

### 3. Signal Value Range Check
Understand that you will see two different ranges of numbers depending on the sensor:

* **Native Analog Sensors (Turbidity, Level):**
    * Connected to Pins **A0 ~ A5**.
    * Range: **0 ~ 1023** (10-bit resolution).
    * *Error:* Pure 0 or 1023 usually means open circuit or short.

* **Precision Sensors (pH, EC, DO):**
    * Connected to **ADS1115 Modules**.
    * Range: **0 ~ 26000+** (16-bit resolution).
    * *Note:* These values are much larger than standard Arduino readings. This is normal.

### 4. Digital Temp Sensor Test (DS18B20)
Check the values on the Dashboard or Serial Monitor:
* **Normal:** 18.0°C - 28.0°C (Room/Water Temp).
* **-127.0°C:** Wiring broken or sensor disconnected.
* **85.0°C:** Power issue or Pull-up resistor (4.7kΩ) missing.

### 5. Final Dry Run
1.  Assemble the full system in the box.
2.  Connect to Raspberry Pi and start Docker.
3.  Check the **Web Dashboard**.
4.  Disconnect one sensor (e.g., Zone B EC).
5.  Verify the specific widget on the dashboard stops updating or drops to 0.

---

## 6. Maintenance & Safety Best Practices

With over 20 sensors connected, proper cable management and regular maintenance are vital for system longevity.

### 1. Cable Management (Crucial)
* **Label Everything:** You have 6 pH sensors and 6 EC sensors that look identical. **Label both ends** of every cable (e.g., "Zone A - Tank 1 - pH"). Troubleshooting is impossible without labels.
* **Cable Glands:** Always use waterproof cable glands for wires entering the electronics box.
* **Drip Loops:** Create a U-shape loop with cables just outside the box. This ensures water drips off the bottom of the loop instead of running down the wire into the electronics.

### 2. Moisture Control
* **Desiccant:** The electronics box will "breathe" due to day/night temperature changes. Place a large pack of **Silica Gel** inside to absorb condensation. Replace or recharge it monthly.
* **Corrosion Check:** Inspect the ADS1115 modules and Arduino pins quarterly for signs of green/white corrosion.

### 3. Probe Storage & Cleaning
* **pH / DO:** **Never let them dry out.** Keep the membrane wet with 3M KCL solution (or tap water temporarily) in the protective cap when not in use.
* **EC:** Rinse with clean water. Dry storage is acceptable.
* **Turbidity:** The optical lens gets dirty quickly in fish water. Wipe it weekly with a soft cloth to prevent false high readings.

### 4. Connection Tightness
* **Terminal Blocks:** Screw terminals can loosen over time due to micro-vibrations from nearby water pumps. **Retighten all power and I2C screw terminals every 3 months.**

---

## 7. Hardware Troubleshooting (Quick Check)

If sensors are not reading correctly immediately after wiring, check these common hardware faults first. For comprehensive software diagnostics (Docker logs, Database locks), refer to [**TROUBLESHOOTING.md**](TROUBLESHOOTING.md).

| Symptom | Likely Hardware Cause | Immediate Solution |
| :--- | :--- | :--- |
| **All ADS Sensors "NaN"** | **I2C Address Conflict** | Check ADS1115 ADDR jumpers. They must be unique (`GND`, `VCC`, `SDA`, `SCL`). |
| **Water Level = 0%** | **Missing 24V Power** | Confirm the **24V SMPS** is ON. This sensor does not work on 5V. |
| **Temp = 85.0°C** | **Missing Pull-up** | Ensure the **4.7kΩ resistor** is connected between VCC and Data line. |
| **Turbidity = Max/Erratic** | **Moisture / Switch** | 1. Dry the black connector (Not waterproof).<br>2. Check adapter switch is on **"A"**. |
| **Noisy/Jittery Data** | **Ground Loop** | Verify **Arduino GND**, **Ext 5V GND**, and **24V GND** are all tied together to a common point. |