# Aquaponics Smart Farm - Quick Start Guide

Get the **Multi-Zone Aquaponics System** (3 Filter Tanks, 3 Nutrient Tanks, 1 Line) up and running safely.

## Quick Setup (Raspberry Pi & Arduino)

### Prerequisites
- **Raspberry Pi:** Model 4B or 5 (Raspbian OS, 64-bit recommended)
- **Arduino Mega 2560:** Connected via USB (`/dev/ttyUSB0`)
- **Hardware:** 4x ADS1115 Modules + 27 Sensors properly wired.
- **Software:** Docker & Docker Compose installed.

---

### Step 0: Critical Hardware Check (Do NOT Skip)
Before connecting power, verify these points to prevent hardware damage:
1.  **24V Safety:** Ensure **Water Level Sensors** use the I/V Converter. **NEVER** connect 24V directly to Arduino.
2.  **I2C Addresses:** Verify your 4 ADS1115 modules have unique addresses set via jumpers:
    * `0x48` (GND), `0x49` (VCC), `0x4A` (SDA), `0x4B` (SCL)
3.  **Power:** Use an **External 5V (3A+)** supply for sensors. Do NOT use the Arduino 5V pin.
4.  **Grounding:** Verify Arduino GND, Ext 5V GND, and 24V GND are all connected.

### Step 1: Prepare Arduino
The Pi cannot read data if the Arduino firmware is missing or lacks libraries.
1.  Connect Arduino to PC.
2.  Open Arduino IDE.
3.  **Install Library:** Go to **Sketch > Include Library > Manage Libraries** and install **`Adafruit ADS1X15`**.
4.  Upload `arduino/arduino.ino`.
5.  Disconnect from PC and connect to **Raspberry Pi**.

### Step 2: Install & Run (Raspberry Pi)

Run the following commands in your terminal:

```bash
# 1. Clone the repository
git clone <repository-url> aquaponics
cd aquaponics

# 2. Configure System (CRITICAL)
# Copy template and map your 3 Tank Sets & ADS1115 addresses
cp config.example.json config.json
nano config.json

# [Check] Verify Arduino connection
ls -l /dev/ttyUSB0
# If missing, check USB cable or permissions

# 3. Start Application
# This builds the Python environment and starts the container
docker-compose up -d --build

# 4. Access Dashboard
# Open browser at: http://<YOUR-PI-IP>:5000
```

**System is live!** Check the dashboard to verify data from all 3 Zones (Filtered Tanks, Nutrient Tanks, Cultivation Line).

---

## First Steps: Verification & Calibration

After the system starts, follow these steps to verify operation and calibrate sensors for accuracy.

### 1. Check Sensor Readings (Dashboard)
Open your browser to: **`http://<RASPBERRY_PI_IP>:5000`**

Verify that data is appearing for all 3 Zones:
* **Zone A (Filter Tanks):**
    * Check **3 separate widgets** for Filter Tanks 1, 2, and 3.
    * Verify **Water Level**, **Turbidity**, and **pH** are updating for each.
* **Zone B (Nutrient Tanks):**
    * Check **3 separate widgets** for Nutrient Tanks 1, 2, and 3.
    * Verify **pH**, **EC**, **DO**, and **Temp** are updating for each.
* **Zone C (Cultivation Line):**
    * Verify the **EC Gradient Graph** shows values for **Start**, **Middle**, and **End** points.

### 2. Verify Data Collection (Terminal)
Ensure data is being saved to the database with the correct **Tank IDs**:

```bash
# Check system status via API
curl -s http://localhost:5000/api/status | python3 -m json.tool

# Query the last 5 readings to verify 'tank_id' column exists
sqlite3 data/aquaponics.db \
  "SELECT timestamp, tank_id, sensor_type, value FROM sensor_readings ORDER BY timestamp DESC LIMIT 5;"
```

### 3. Initial Calibration (Crucial)
**Sensors will provide incorrect data until calibrated.** Perform this immediately for each tank.

#### A. pH Sensors (Software Calibration)
* **Target:** 6 Sensors (3x Filter Tanks, 3x Nutrient Tanks).
* **Method:** 3-Point Calibration.
* **Steps:**
    1.  Go to **Dashboard > Settings > Calibration**.
    2.  **Select Target:** Choose specific sensor (e.g., **"Nutrient Tank 1 - pH"**).
    3.  Dip probe in **pH 7.0**, wait, click **"Calibrate 7.0"**.
    4.  Rinse, dip in **pH 4.0**, click **"Calibrate 4.0"**.
    5.  Rinse, dip in **pH 10.0**, click **"Calibrate 10.0"**.
    6.  **Repeat** for the other 5 pH sensors.

#### B. EC Sensors (Software Calibration)
* **Target:** 6 Sensors (3x Nutrient Tanks, 3x Cultivation Line).
* **Method:** 1-Point Standard.
* **Steps:**
    1.  **Dry the probe completely.**
    2.  Dip in **1413 μS/cm** standard solution.
    3.  Shake gently to remove air bubbles.
    4.  Select target (e.g., **"Line Start - EC"**) and click **"Calibrate 1413"**.
    5.  **Repeat** for all 6 EC sensors.

#### C. Water Level Sensors (Hardware Calibration)
* **Target:** 3 Sensors (Filter Tanks 1, 2, 3).
* **Method:** Physical adjustment on the **I/V Converter Module** (Not Software).
* **Important:** Perform this **BEFORE** sealing the electronics box.

* **Steps (Per Tank):**
    1.  **Zero Point:** Lift sensor into empty air. Adjust the **"Zero" potentiometer** on the module until the specific Tank Widget reads **0%**.
    2.  **Span Point:** Submerge sensor to max depth. Adjust the **"Span" potentiometer** until the widget reads **100%**.

### 4. Set Alert Thresholds
Edit `config.json` to match your specific crop requirements.

> **CRITICAL WARNING (EC SENSOR LIMIT):**
> The **SEN0451 (K=1.0)** sensor has a hardware limit of **2000 μS/cm**.
> * **Do NOT set `critical_max` above 2000.**
> * If readings hit 2000, the sensor is saturated (blind). Dilute the solution immediately.

```json
"alert_thresholds": {
  "pH": { 
    "min": 6.8, 
    "max": 7.0, 
    "critical_min": 6.0, 
    "critical_max": 8.0 
  },
  "EC": { 
    "min": 1200, 
    "max": 1600, 
    "critical_min": 800, 
    "critical_max": 2000  // Hardware Limit
  },
  "water_level": { 
    "min": 80, 
    "critical_min": 40    // Pump Cut-off Level
  }
}
```
*After editing, restart the system:* `docker-compose restart`

---

## Common Operational Tasks

Here are the most frequent commands you will need for daily management of the Multi-Zone system.

### 1. View Dashboard & Real-time Status
Access the graphical interface to monitor:
* **Zone A:** 3x Filter Tanks
* **Zone B:** 3x Nutrient Tanks
* **Zone C:** 1x Cultivation Line
* **URL:** `http://<RASPBERRY_PI_IP>:5000`

### 2. Get Raw Sensor Data (API)
Use these commands to inspect the raw JSON data. Note that data is now nested by **Zone** and **Tank ID**.

```bash
# Get current real-time readings (Returns nested JSON: Zone -> Tank -> Sensor)
curl -s http://localhost:5000/api/current | python3 -m json.tool

# Get statistics for the last 24 hours (Min/Max/Avg per Tank)
curl -s http://localhost:5000/api/statistics?hours=24 | python3 -m json.tool
```

### 3. Export Data for Excel/Analysis
Download historical data. You can filter by specific zones to keep files manageable.

```bash
# Export ALL data for last 24 hours to CSV
curl "http://localhost:5000/api/export?format=csv&hours=24" -o daily_full.csv

# Export ONLY Nutrient Tanks (Zone B) for the last week
curl "http://localhost:5000/api/export?format=csv&hours=168&zone=zone_b" -o nutrient_report.csv
```

### 4. Apply Configuration Changes
If you edited `config.json` (e.g., changed the EC threshold for Nutrient Tank 2), you must restart the service.

```bash
# 1. Edit the file
nano config.json

# 2. Restart the container to apply changes
docker-compose restart
```

### 6. Monitor Logs & Debugging
Check what the system is doing behind the scenes.

```bash
# View real-time logs (Press Ctrl+C to exit)
docker logs -f aquaponics

# View the last 100 lines of the log file on the host
tail -n 100 data/logs/app.log

# Filter logs for Errors or Warnings only
grep -E "ERROR|WARNING" data/logs/app.log
```

---

## Arduino Setup (Firmware)

The Arduino Mega acts as the data collector. It manages the **I2C Bus (4x ADS1115)** and **Native Analog Pins** to read from 27+ sensors, converting raw data into a structured JSON stream.

### Prerequisites
- **Computer:** Windows, Mac, or Linux with USB port.
- **Software:** [Arduino IDE](https://www.arduino.cc/en/software) installed.
- **Hardware:** Arduino Mega 2560 connected to PC via USB.
- **Wiring:** All sensors and **4x ADS1115 modules** wired according to `HARDWARE_SETUP.md`.

### Step 1: Install Required Libraries
The firmware depends on specific drivers. In Arduino IDE, go to **Sketch > Include Library > Manage Libraries...** and install:
1.  **`Adafruit ADS1X15`** (by Adafruit) - **CRITICAL:** Required for the 4 ADC modules.
2.  `OneWire` (by Paul Stoffregen) - For DS18B20 Temp sensors.
3.  `DallasTemperature` (by Miles Burton) - For DS18B20 Temp sensors.
4.  `ArduinoJson` (by Benoit Blanchon) - **Must be Version 6.x** (For generating nested JSON).

### Step 2: Configure Firmware
1.  Open the file `arduino/arduino.ino`.
2.  Navigate to the `config.h` tab.
3.  **Verify I2C Addresses:** Ensure the defined addresses match your physical jumper settings:
    * `#define ADS_ADDR_FILTER 0x48`
    * `#define ADS_ADDR_NUTRIENT_1 0x49`
    * ... (and so on).
4.  **Verify Pin Mapping:** Check that native pins (e.g., Level Sensors on `A1`, `A3`, `A5`) match your wiring.

### Step 3: Select Board & Port
Configure the IDE to talk to the Mega 2560:
1.  **Tools > Board**: Select **"Arduino Mega or Mega 2560"**.
2.  **Tools > Processor**: Select **"ATmega2560 (Mega 2560)"**.
3.  **Tools > Port**: Select the COM port (Windows) or `/dev/tty...` (Mac/Linux).

### Step 4: Upload Sketch
1.  Click the **Verify (✓)** button to check for compilation errors.
2.  Click the **Upload (→)** button.
3.  Wait until the status bar says **"Done uploading"**.

### Step 5: Verify Operation (Sanity Check)
Before connecting to the Pi, ensure the Arduino is detecting the hardware.
1.  Open **Serial Monitor** (Tools > Serial Monitor).
2.  Set Baud Rate to **115200**.
3.  **Check Startup Log:** You should see:
    ```text
    [INIT] Starting Aquaponics System...
    [I2C] Found ADS1115 at 0x48
    [I2C] Found ADS1115 at 0x49
    ...
    ```
4.  **Check Data Stream:** Ensure it prints JSON lines like:
    ```json
    {"zone_a": {"tank_1": {"ph": 7.01, ...}}, "zone_b": ...}
    ```

---

## Troubleshooting Common Issues

For a complete diagnostic guide, refer to [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### 1. Dashboard Won't Load
If `http://<IP>:5000` is unreachable:
```bash
# 1. Check Docker Status
docker ps
# If container is not listed, it crashed or stopped.

# 2. Check Startup Logs
docker logs aquaponics
# Look for "Address already in use" (Port conflict) or Python errors.

# 3. Check IP Address
ifconfig
# Ensure you are using the correct IP of the Raspberry Pi.
```

### 2. No Sensor Readings (Empty/Null)
If the dashboard loads but charts are empty or show "NaN":
```bash
# 1. Verify USB Connection
ls -l /dev/ttyUSB0
# If "No such file", unplug/replug the Arduino.

# 2. Check Serial Permissions
groups $USER
# Must include 'dialout'.

# 3. Check for I2C Errors in Logs
docker logs -f aquaponics
# If you see "ADS1115 Error" or "I2C Device Not Found", check your wiring.
```

### 3. Specific Sensor Failures (Hardware)
* **Entire Zone is Dead (e.g., All Nutrient Tanks read 0):**
    * **Check:** The **ADS1115 module** for that zone might have an **I2C Address Conflict**. Verify jumpers (`0x48`~`0x4B`).
* **Water Level reads 0%:**
    * **Check:** Is the **24V SMPS** turned on? (Required for KIT0139).
    * **Check:** Is the **I/V Converter** wired correctly?
* **EC reads flat 2000:**
    * **Check:** **Saturation.** The water is too salty (> 2.0 EC). Dilute with fresh water immediately.
    * **Check:** Is the probe connected?
* **Turbidity reads Max/Min constant:**
    * **Check:** Did the **black connector** get wet? It is **NOT** waterproof. Dry it immediately.

### 4. Database Locked / Errors
If logs show `sqlite3.OperationalError: database is locked`:
```bash
# 1. Check File Permissions
ls -la data/
# The 'aquaponics.db' file must be writable by the user.

# 2. Fix Permissions (if needed)
sudo chmod 666 data/aquaponics.db
```

### 5. Application Crashes Repeatedly
```bash
# 1. Check the tail of the log file
tail -n 50 data/logs/app.log

# 2. Enable Debug Mode for more details
# Edit config.json -> set "level": "DEBUG"
# Then restart:
docker-compose restart
```

---

## Next Steps: Post-Installation

Once your system is running, establish a routine to ensure long-term stability for all 3 Zones.

### 1. Establish a Maintenance Routine
* **Weekly:**
    * **Turbidity Sensors:** Check the black connectors for moisture (Zone A). Wipe the optical prism.
    * **Wiring Check:** Ensure screw terminals on the **4x ADS1115 modules** haven't loosened due to pump vibrations.
* **Monthly:**
    * **Probes:** Rinse **pH and EC probes** with clean water. (Nutrient tanks build biofilm quickly).
    * **Calibration:** Re-run the 3-point pH calibration wizard for all 6 pH sensors.
    * **DO Sensor:** Check the electrolyte level and membrane cap status.
* **Data Backup:** Ensure the `backup.sh` cron job is running. Check `data/backups/` for recent files.

### 2. Optimize System Performance
* **Fine-tune Thresholds:** After a week of data, adjust `config.json` to set tighter Warning limits for each specific Tank.
* **Hot-Reload:** Apply config changes immediately without downtime:
    ```bash
    curl -X POST http://localhost:5000/api/config -d '{"reload": true}'
    ```

### 3. Advanced Integration
The system is API-first. You can integrate it with other tools:
* **Grafana:** Connect to the SQLite DB (`data/aquaponics.db`) for custom multi-zone dashboards.
* **Home Assistant:** Poll `/api/current` to trigger smart home automations (e.g., lights/pumps).
* **Excel/Google Sheets:** Automate data import using the CSV export endpoint.

---

## API Quick Reference

The system exposes a RESTful API on port `5000`.

| Endpoint | Method | Description | Example Command |
| :--- | :--- | :--- | :--- |
| **/api/status** | `GET` | System health & I2C bus status | `curl -s http://localhost:5000/api/status` |
| **/api/current** | `GET` | Get nested readings (Zone->Tank) | `curl -s http://localhost:5000/api/current` |
| **/api/history** | `GET` | Get history (Filter by Zone) | `curl -s "http://localhost:5000/api/history?hours=24&zone=zone_b"` |
| **/api/export** | `GET` | Download CSV/Excel | `curl -O "http://localhost:5000/api/export?format=csv"` |
| **/api/calibration/<id>** | `POST` | Calibrate specific sensor | `curl -X POST -d '{"points":...}' http://localhost:5000/api/calibration/zone_b_tank1_ph` |
| **/api/alert** | `POST` | Trigger a manual test alert | `curl -X POST -d '{"message":"Test"}' http://localhost:5000/api/alert` |

> **Developer Note:** All API responses are in **JSON** format (except for the CSV/Excel export).
---

## Useful Keyboard Shortcuts

Here are the essential shortcuts for managing the system efficiently.

| Context | Shortcut | Action |
| :--- | :--- | :--- |
| **Terminal** | `Ctrl + C` | Stop the currently running command (e.g., stopping logs). |
| | `Ctrl + L` | Clear the terminal screen. |
| | `Tab` | Autocomplete file names or commands (Type `dock` + Tab -> `docker`). |
| | `Up Arrow` | Recall previous commands history. |
| **Docker** | `Ctrl + P`, then `Ctrl + Q` | **Detach** from a running container without stopping it. |
| **Arduino IDE** | `Ctrl + U` | Compile and Upload firmware to the board. |
| | `Ctrl + Shift + M` | Open Serial Monitor to view raw sensor data. |

---

## System Requirements

### Computing Unit (Raspberry Pi)
| Spec | Minimum | Recommended |
| :--- | :--- | :--- |
| **Model** | Raspberry Pi 4B (2GB RAM) | **Raspberry Pi 4B (4GB+) or Pi 5** |
| **Storage** | 16GB microSD (Class 10) | **32GB+ High Endurance microSD** (Better for database reliability) |
| **OS** | Raspbian Buster (Legacy) | **Raspberry Pi OS (64-bit)** |
| **Network** | WiFi (2.4GHz) | **Ethernet (Wired)** for stability |

### Power Supply (Critical)
The system requires **3 separate power sources** to prevent noise and damage.

1.  **Main Controller (Pi):** 5V 3A USB-C Adapter (Official Raspberry Pi PSU).
2.  **Sensors (pH, EC, etc.):** **External 5V 3A+ Adapter** (Required for 4x ADS1115 modules and 20+ sensors).
3.  **Level Sensors (KIT0139):** **24V DC SMPS** (Required for 4-20mA loop).

### Sensor Capacity
* **Microcontroller:** Arduino Mega 2560 (**Required for I2C and Digital Pin count**).
* **Analog Inputs Managed:** **21 Channels** (15 ADS1115 I2C Channels + 6 Mega Native Pins).
* **Digital Inputs Used:** 6 Pins (D2 ~ D7 for 6 Temp sensors).

---

## File Structure Overview

This structure supports a hybrid architecture (Arduino Mega + Raspberry Pi) with Dockerized deployment, optimized for **Multi-Zone (3 Filter / 3 Nutrient / 1 Grow Line)** monitoring.

```bash
aquaponics/
├── docker-compose.yml          # [Docker] Service orchestration (App + DB + Network)
├── config.json                 # [Config] Master Configuration (CRITICAL: Maps 4x ADCs, 3 Tank Sets, & Thresholds)
├── .env                        # [Config] Environment variables (Secrets, Ports) - Optional
├── README.md                   # Project Overview
│
├── arduino/                    # [Firmware] Arduino Mega 2560 Code (I2C Master)
│   ├── arduino.ino             # Main sketch (Handles I2C polling and Serial output)
│   ├── config.h                # Pin definitions, ADS Addresses, & Global Constants
│   ├── sensors.h               # Sensor Class Definitions & Hardware Logic (EC Saturation, etc.)
│   └── libraries/              # Third-party Arduino libraries (ADS1X15, OneWire, etc.)
│
├── raspberry_pi/               # [Host] Raspberry Pi Python Application
│   ├── Dockerfile              # [Docker] Python Image build instructions
│   ├── requirements.txt        # Python dependencies (Flask, Pandas, Serial, etc.)
│   ├── app/                    # Source Code
│   │   ├── main.py             # Application Entry Point & Scheduler
│   │   ├── sensors.py          # Serial Handler & Nested JSON Data Parser
│   │   ├── database.py         # SQLite ORM (Schema support for 7 distinct zones)
│   │   ├── api.py              # REST API Endpoints (Data retrieval per Tank/Line)
│   │   ├── dashboard.py        # Web Dashboard Rendering Logic (Multi-Zone Views)
│   │   └── config.py           # Configuration Loader (Parses config.json for Python)
│   └── tests/                  # Unit & Integration Tests (Includes nested JSON parsing tests)
│
├── data/                       # [Volume] Persistent Data Storage (Mapped in Docker)
│   ├── aquaponics.db           # SQLite Database file (Expanded Multi-Zone Schema)
│   └── logs/                   # Application Logs
│
└── docs/                       # [Docs] Comprehensive Documentation Suite (9 Guides)
    ├── QUICKSTART.md           # Fast-track deployment & safety checks
    ├── INSTALLATION.md         # OS setup, Docker installation & Firmware upload
    ├── HARDWARE_SETUP.md       # Detailed wiring diagrams (4x ADS1115 & 24V Logic)
    ├── CALIBRATION.md          # Sensor Calibration (pH 3-point, EC 1-point, Level HW)
    ├── API.md                  # REST API Endpoints with nested Tank ID support
    ├── TROUBLESHOOTING.md      # Diagnostics for I2C conflicts, sensor errors & Docker issues
    └── IMPLEMENTATION_SUMMARY.md # Final project status and architecture overview
```

---

## Support & Resources

Refer to these documents for detailed operations:

* **Wiring & Pinout:** See `docs/HARDWARE_SETUP.md` (Crucial for **4x ADS1115** and **24V** safety).
* **Fixing Issues:** Check `docs/TROUBLESHOOTING.md` for error codes (e.g., I2C bus conflicts and sensor saturation).
* **API Documentation:** See `docs/API.md` for integration guides and **nested JSON** structure.
* **Logs:** Application logs are stored in `data/logs/app.log`.
* **Configuration:** All settings, including **ADS addresses** and **Thresholds**, are in `config.json`.

---

## Tips & Tricks for Operators

### 1. Check System Health (Communication & Resources)
Monitor resource usage and verify the critical communication links are active.

```bash
# Check CPU/Memory usage of the container
docker stats aquaponics --no-stream

# Check Disk Space (Database grows over time)
df -h | grep /dev/root

# Check Network IP
hostname -I
```

### 2. Monitor Data in Real-Time (Formatted)
Use `watch` combined with `python3` to see the clean, **nested JSON** stream from the API.

```bash
# Updates every 5 seconds, checking all Zones
watch -n 5 "curl -s http://localhost:5000/api/current | python3 -m json.tool"
```

### 3. Database Backup & Restore
The automated cron job runs daily, but you can trigger a manual backup immediately using the script.

```bash
# Backup: Execute the automated script manually
./backup.sh

# Restore: Overwrite current DB with a backup (CRITICAL: Must stop Docker first!)
docker-compose down
cp backups/aquaponics_20251202.db data/aquaponics.db
docker-compose up -d
```

### 4. Quick Configuration Update
Changed a threshold? Apply it without downtime using a simple restart.

```bash
# 1. Edit config (Update thresholds or ADS mapping)
nano config.json

# 2. Restart container to reload config
docker-compose restart
```

### 5. Export Data for Reports
Generate a CSV file for the last week, filtering by zone (e.g., Zone B).

```bash
# Download CSV for the last 168 hours (7 days) for ALL ZONES
curl "http://localhost:5000/api/export?format=csv&hours=168" -o weekly_full_report.csv

# Download CSV only for Nutrient Tanks (Zone B)
curl "http://localhost:5000/api/export?format=csv&hours=168&zone=zone_b" -o nutrient_only_report.csv
```

---

## Customization Examples

Modify `config.json` to tailor the system to your specific crop requirements and troubleshooting needs. This file is critical as it defines **Zone Mapping**, **ADS1115 Addressing**, and all **Alert Thresholds**.
*Note: Ensure you maintain the correct nesting structure (`"monitoring"` -> `"alert_thresholds"`) as shown below.*

---

### 1. Enable Debug Logging (Troubleshooting)
If you need to troubleshoot I2C communication or serial data parsing issues, switch the logging level to see every detail.

```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

### 2. Adjust Monitoring Intervals (Performance Tuning)
Change how often data is saved and smoothed. These settings are found under the `"monitoring"` section.

* **reading_interval_seconds:** Default is 60. Set to 300 for 5-minute intervals (reducing database load).
* **averaging_window:** Default is 10. Increase to 20 or 30 if sensor readings (especially Turbidity/EC) are too jittery.

```json
{
  "monitoring": {
    "reading_interval_seconds": 300,
    "averaging_window": 20
  }
}
```

### 3. Custom Alert Thresholds (Multi-Zone Targets)
Define the **Optimal**, **Warning**, and **Critical** state boundaries based on your specific fish and crop needs. These settings are nested under `"monitoring" > `"alert_thresholds"`.

**Example: Strict Optimal pH/EC limits and Critical Safety Limits**
(Note: These align with the latest recommended targets.)

```json
{
  "monitoring": {
    "alert_thresholds": {
      "pH": {
        "min": 6.8, 
        "max": 7.0, 
        "warning_min": 6.0,
        "warning_max": 7.5,
        "critical_min": 6.0,
        "critical_max": 8.0
      },
      "EC": {
        "min": 1200,
        "max": 1600,
        "warning_min": 1000,
        "warning_max": 1800,
        "critical_min": 800,
        "critical_max": 2000 // Hardware Saturation Limit
      },
      "water_level": {
        "min": 80, 
        "critical_min": 40    // Critical: Pump Cut-off Level
      }
    }
  }
}
```

---

**Happy Monitoring!**
Your Aquaponics System is now fully configured and ready to grow.