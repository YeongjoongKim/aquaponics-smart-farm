<!-- 2025-11-23. 서천 늘푸른 아쿠아포닉스 방문

[요구사항 확인]
1. 어류 배설물을 걸러 깨끗해진 물을 펌프를 통해 다시 수조에 물을 채우는 방식을 사용한다. 이때, 깨끗해진 물을 담은 통에 센서(PH, 수온, 수위, 탁도)를 설치하여 데이터를 수집하고, 해당 데이터의 변화를 모니터로 확인

2. 식물에게 배양액을 제공하기 전, 배양액 통에 센서(PH, 수온, EC, 용존 산소량)를 설치하여 데이터를 수집하고, 해당 데이터의 변화를 모니터로 확인

3. 스마트팜 배양 라인은 총 4개가 존재함, 그 중 하나의 라인에 처음, 중간, 끝에 센서(EC)을 설치하여 처음, 중간, 끝의 농도 차이를 모니터로 확인 (처음에 심어진 식물이 영양을 흡수하면, 끝에 갈 수록 영양을 받지 못하는지 확인)

4. 실측값은 센서 설치 이후 직접 확인하면서 조정

[아쿠아포닉스 센서 설치 위치]
1. 여과 물탱크 3개
2. 배양액 탱크 3개
3. 재배 라인 1개

-->

<!-- 2025-11-25. 센서 모델 선정 → 2025-12-02. 센서 개수 및 추가 센서 파악, 필요 물품 파악
 [센서]
 PH : SEN0169-V2 (6개 - 여과 물탱크 3개, 배양액 탱크 3개)
 EC : SEN0451 (6개 - 배양액 탱크 3개, 재배 라인 3개)
 DO : SEN0237 (3개 - 배양액 탱크 3개)
 수온 : DS18B20 (6개 - 여과 물탱크 3개, 배양액 탱크 3개)
 수위 : KIT0139 (3개 - 여과 물탱크 3개 / 24V 전원 필수)
 탁도 : SEN0189 (3개 - 여과 물탱크 3개)

 [제어 및 모듈]
 Arduino Mega 2560 : (1개 - 메인 컨트롤러 / 예비용 1개 추가 권장)
 ADS1115 : ADC 모듈 (4개 - PH, EC, DO 정밀 측정용 15채널 확보)
 DFR0504 : 아날로그 아이솔레이터 (15개 - PH, EC, DO 센서 간 전기적 간섭 방지 필수품)
 터미널 쉴드 : Mega 용 (1개 - 진동에 선이 빠지지 않도록 나사로 조이는 방식)

[전원 및 변환 모듈]
SMPS (24V) : 용량 10~15A 이상 (1개 - 수위 센서 구동 및 추후 펌프/밸브 전원 공급용)
DC-DC 강압 컨버터 : LM2596 등 (3개 - 24V 전압을 5V/9V로 낮춰 아두이노 및 5V 센서에 전원 공급)

 [배선 및 잡자재]
 STP or FTP 케이블 : (1롤 - 센서 데이터 노이즈 차폐용 연장 케이블 / 100m 이상 권장)
 2P 쉴드 케이블 : (1롤 - 수위 센서 전용 연장선 / 기존 STP 케이블에서 2가닥 추출하여 사용 가능)
 저항 4.7kΩ : (10개 - 수온 센서 풀업용 / 여분 포함)
 방수 하이박스 : (N개 - 수조 옆에 설치하여 센서 변환 보드 및 아이솔레이터 보호)
 와고(Wago) 커넥터 : 또는 터미널 블록 (1봉 - 24V 및 5V 전원 분배용)

-->

# Aquaponics Smart Farm Multi-Zone Monitoring System

A comprehensive IoT solution optimized for large-scale Aquaponics, utilizing **Arduino Mega 2560** and **Raspberry Pi** with **Dockerized** deployment.

This system is designed to manage complex field requirements by simultaneously monitoring:
* **3 Filtration Tanks**: Analyzing purification efficiency via PH, Temperature, Water Level, and Turbidity sensors.
* **3 Nutrient Tanks**: Controlling nutrient supply via PH, Temperature, EC, and DO sensors.
* **1 Cultivation Line**: Monitoring nutrient gradients (EC) across three points (Start, Mid, End) to ensure uniform growth.

It integrates precision analog sensors via **ADS1115** expansion to ensure strict water quality control and data-driven farming.

## Features

### 1. Zone-Specific Monitoring (Field Requirements)
- **Filtered Water Tanks (Recirculation)**:
  - **3 Separate Tanks**: Monitors water quality independently for each filtration stage (3 Sets) before recirculation.
  - **Sensors (Per Tank)**: pH, Water Level, Water Temperature, Turbidity.

- **Nutrient Tanks (Supply)**:
  - **3 Separate Tanks**: Independently analyzes the nutrient solution composition for multiple supply lines.
  - **Sensors (Per Tank)**: pH, EC (Electrical Conductivity), Dissolved Oxygen (DO), Water Temperature.

- **Cultivation Line (Gradient Analysis)**:
  - **Single Main Line Monitoring**: Focuses on precise nutrient absorption analysis along the flow.
  - **3-Point Check (EC Only)**: Monitors **Start, Middle, and End** points using **EC sensors** to analyze nutrient absorption efficiency as the solution flows through the crops.
  - **Optimization**: pH is centrally controlled at the Nutrient Tanks, so the line focuses solely on EC gradients to maximize resource efficiency.

### 2. Core System Features
- **Dockerized Architecture**: Fully containerized application for easy deployment on Raspberry Pi.
- **Scalable Data Management**: Handles high-frequency data from 15+ sensors with granular aggregation (Sec/Min/Hour/Day).
- **Data Export**: Support for **Excel (.xlsx)**, JSON, and CSV formats for research analysis.
- **Real-time Dashboard**: Web interface for visualization, sensor calibration, and threshold alerts.
- **Intelligent Alerting**: Configurable thresholds with WARNING/CRITICAL levels for each specific tank and line.
- **Offline Capable**: Fully functional without an internet connection (Local Network).

## Quick Start

### Prerequisites

- **Arduino**: Arduino IDE 1.8.19+, **Arduino Mega 2560** (Required for multi-sensor support)
- **Raspberry Pi**: Python 3.9+, Raspbian OS (or Docker installed)
- **Hardware**: 
  - 4x ADS1115 Modules (Address: 0x48, 0x49, 0x4A, 0x4B)
  - Sensors (pH, EC, DO, Temp, Water Level, Turbidity)
  - I2C & Analog wiring components

### Installation and Run (Docker Method)
```bash
# 1. Clone the repository
git clone [https://github.com/your-repo/aquaponics.git](https://github.com/your-repo/aquaponics.git)
cd aquaponics

# 2. Configure hardware and zones (CRITICAL)
# Map your 3 Filter Tanks, 3 Nutrient Tanks, and ADS1115 addresses here.
cp config.example.json config.json
nano config.json 

# 3. Build and Run
docker-compose up -d --build
```
### Arduino Setup
**Note**: Before uploading, ensure you have installed the required libraries via **Sketch > Include Library > Manage Libraries**:
* `Adafruit ADS1X15` (For ADC Modules)
* `OneWire` & `DallasTemperature` (For Water Temp Sensors)
* `DFRobot_PH`, `DFRobot_EC` (If using specific vendor libraries)

```bash
cd arduino/
# 1. Open arduino.ino in Arduino IDE
# 2. Select Board: Arduino Mega 2560
# 3. Select Port: /dev/ttyUSB0 (or similar)
# 4. Upload Firmware
```

### Raspberry Pi Setup (Manual Method)
```bash
cd raspberry_pi/
# Install dependencies including serial and I2C support
pip install -r requirements.txt
python app/main.py
```

Access the dashboard at: `http://localhost:5000`

## Architecture & File Structure

The project structure supports a hybrid architecture (Arduino Mega + Raspberry Pi) with Dockerized deployment, optimized for **Multi-Zone (3 Filter / 3 Nutrient / 1 Grow Line)** monitoring.

All detailed guides are located in the `docs/` directory.

```
aquaponics/
├── docker-compose.yml          # [Docker] Service orchestration (App + DB + Network)
├── config.json                 # [Config] Master Configuration (CRITICAL: Maps 4x ADCs, 3 Tank Sets, & Pins)
├── .env                        # [Config] Environment variables (Secrets, Ports) - Optional
├── README.md                   # Project Overview
│
├── arduino/                    # [Firmware] Arduino Mega 2560 Code
│   ├── arduino.ino             # Main sketch (Iterates through Tank/Sensor Objects)
│   ├── config.h                # Pin definitions & Global Constants
│   ├── sensors.h               # Sensor Class Definitions (Polymorphic logic for PH, EC, DO)
│   └── libraries/              # Third-party Arduino libraries (ADS1X15, OneWire, etc.)
│
├── raspberry_pi/               # [Host] Raspberry Pi Python Application
│   ├── Dockerfile              # [Docker] Python Image build instructions
│   ├── requirements.txt        # Python dependencies (Flask, Pandas, Serial, etc.)
│   ├── app/                    # Source Code
│   │   ├── main.py             # Application Entry Point (Initializes System)
│   │   ├── sensors.py          # Sensor Manager (Parses complex serial packets from Mega)
│   │   ├── database.py         # SQLite ORM (Schema support for 7 distinct zones)
│   │   ├── api.py              # REST API Endpoints (Data retrieval per Tank/Line)
│   │   ├── dashboard.py        # Web Dashboard Logic (Rendering Multi-Zone Views)
│   │   ├── serial_handler.py   # Serial Communication Handler (Reliable reading loop)
│   │   ├── flask_app.py        # Flask Application Factory
│   │   └── config.py           # Configuration Loader (Parses config.json for Python)
│   └── tests/                  # Unit & Integration Tests
│
├── data/                       # [Volume] Persistent Data Storage (Mapped in Docker)
│   ├── aquaponics.db           # SQLite Database file (Expanded Schema)
│   └── logs/                   # Application Logs
│
├── docs/                       # [Docs] Comprehensive Documentation
│   ├── QUICKSTART.md           # Fast-track guide & Safety checks
│   ├── INSTALLATION.md         # Full OS setup, Docker installation & Firmware upload
│   ├── HARDWARE_SETUP.md       # Wiring diagrams (15 Sensors, 24V Logic, & ADS1115)
│   ├── CALIBRATION.md          # Sensor Calibration (pH 3-point, EC 1-point, Level HW)
│   ├── API.md                  # REST API Endpoints, Usage & Response formats
│   ├── TROUBLESHOOTING.md      # Diagnostics, Error Codes & Common Solutions
│   └── IMPLEMENTATION_SUMMARY.md # Project Status, Architecture Overview & Tech Specs
│
└── specs/                      # [Specs] Data Models & Design Specifications
```

## Sensor Specifications

Selected sensor models based on **2025-11-25 Hardware Selection**, optimized for Arduino Mega 2560 integration.

| Sensor | Sensor Model | Type | Range | Resolution | Calibration |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **pH** | SEN0169-V2 | Analog (0-5V) | 0 - 14 | ±0.1 | 3-point (4.0, 7.0, 10.0) |
| **EC** | SEN0451 (K=1) | Analog (0-5V) | 0 - 2000 μS/cm | ±1% F.S | 1-point (1413 μS/cm)* |
| **Temp** | DS18B20 | Digital (1-Wire) | -55 ~ +125°C | ±0.5°C | Factory Calibrated |
| **DO** | SEN0237 | Analog (0-5V) | 0 - 20 mg/L | ±0.1 mg/L | 2-point (0%, 100%) |
| **Level** | KIT0139 | Analog (4-20mA) | 0 - 5m (Depth) | <1mm | Zero/Span (Empty/Full) |
| **Turbidity**| SEN0189 | Analog (0-4.5V) | 0 - 3000 NTU | - | 1-point (Clear Water) |

> **Hardware Notes & Safety Warnings**:
> * **EC (SEN0451)**: This K=1.0 probe has a hardware limit of **2000 μS/cm (2.0 EC)**. It cannot measure high salinity (e.g., seawater). Use **1413 μS/cm standard solution** ONLY for calibration.
> * **Water Level (KIT0139)**: This is an industrial **4-20mA Current Loop** sensor.
>     * **Requirement**: It requires a separate **24V Power Supply** and a **Current-to-Voltage (I/V) Converter** module.
>     * **Danger**: NEVER connect the 24V line directly to the Arduino.
> * **Turbidity (SEN0189)**: The black connector on top of the probe is **NOT waterproof**. Only submerge the transparent prism prongs.

## Aquaponics Water Quality Targets

Defined optimal ranges for the "Smart Farm Multi-Zone System". These values determine the **Green (Optimal)**, **Yellow (Warning)**, and **Red (Critical)** states on the dashboard.

| Parameter | Optimal Range | Unit | Warning Range (Yellow) | Critical Threshold (Red) | Note |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **pH** | 6.8 - 7.0 | - | 6.0 - 6.8 / 7.0 - 7.5 | **< 6.0** or **> 8.0** | Fish/Plant Compromise |
| **EC** | 1200 - 1600 | μS/cm | 1000 - 1200 / 1600 - 1800 | **< 800** or **≥ 2000*** | *Sensor Max Limit (Saturation) |
| **Temp** | 20 - 26 | °C | 18 - 20 / 26 - 28 | **< 15** or **> 32** | Root Rot Risk at >28°C |
| **DO** | 5.0 - 8.0 | mg/L | 3.0 - 5.0 | **< 3.0** | Hypoxia Risk |
| **Level** | 80 - 100 | % | 60 - 80 | **< 60** (Refill) / **< 40** (Stop Pump) | Cavitation Protection |
| **Turbidity**| 0 - 50 | NTU | 50 - 100 | **> 100** | Filter Maintenance Req. |

> **Calibration Note:**
> * **EC Warning:** The selected EC probe (`SEN0451`, K=1.0) cannot read above **2000 μS/cm**. If the reading hits 2000, it indicates the water is effectively "Over Saline" (System Fault).
> * **Water Level:** A critical low level (<40%) should trigger an automated **Pump Cut-off** to prevent hardware damage.

## API Endpoints

The system provides a RESTful API accessible at `http://<RPI-IP>:5000/api` for integration and frontend communication.

```http
# System & Health
GET  /api/status                 # Check system health, uptime, and database connection

# Real-time & Historical Data
GET  /api/current                # Get latest readings (Nested by Zone A, B, C)
GET  /api/history?hours=24       # Get historical data (Optional params: &zone=zone_b &limit=100)
GET  /api/statistics?hours=24    # Get Min/Max/Avg statistics for analysis
GET  /api/export?format=csv      # Download data report (Supports: csv, json, xlsx)

# Alert Management
GET  /api/alerts/active          # List currently unresolved warnings/critical alerts
GET  /api/alerts                 # View full alert history log
POST /api/alert                  # Trigger a manual test alert

# Calibration (Per Sensor)
GET  /api/calibration/<id>       # View calibration history for a specific sensor
POST /api/calibration/<id>       # Submit new calibration points (3-point pH, 1-point EC, etc.)
                                 # IDs: zone_a_tank1_ph, zone_b_ec, zone_c_start_ec...

# Configuration
GET  /api/config                 # Retrieve current system settings (Thresholds, Intervals)
POST /api/config                 # Update configuration dynamically (Hot-reload supported)
```

## Configuration (`config.json`)

Edit `config.json` to customize the system. Below is the configuration matching the **3 Filter Tanks + 3 Nutrient Tanks + 1 Cultivation Line** requirement, including the expanded sensor array.

```json
{
  "site_name": "Aquaponics Smart Farm Multi-Zone",
  "hardware": {
    "platform": "arduino_mega",
    "port": "/dev/ttyUSB0",
    "baud_rate": 115200,
    "adc_modules": [
      { "address": "0x48", "usage": "Filter Tank Sensors" },
      { "address": "0x49", "usage": "Nutrient Tank Sensors (1 & 2)" },
      { "address": "0x4A", "usage": "Nutrient Tank Sensors (3) & Line" },
      { "address": "0x4B", "usage": "Spare / Precision Sensors" }
    ]
  },
  "zones": {
    "filtered_tanks": [
      {
        "id": "filter_tank_1",
        "description": "Recirculation water tank #1",
        "sensors": [
          { "type": "ph", "model": "SEN0169-V2", "pin": "ADS_0x48_0" },
          { "type": "turbidity", "model": "SEN0189", "pin": "A0" },
          { "type": "water_level", "model": "KIT0139", "pin": "A1" },
          { "type": "temperature", "model": "DS18B20", "pin": "D2" }
        ]
      },
      {
        "id": "filter_tank_2",
        "description": "Recirculation water tank #2",
        "sensors": [
          { "type": "ph", "model": "SEN0169-V2", "pin": "ADS_0x48_1" },
          { "type": "turbidity", "model": "SEN0189", "pin": "A2" },
          { "type": "water_level", "model": "KIT0139", "pin": "A3" },
          { "type": "temperature", "model": "DS18B20", "pin": "D3" }
        ]
      },
      {
        "id": "filter_tank_3",
        "description": "Recirculation water tank #3",
        "sensors": [
          { "type": "ph", "model": "SEN0169-V2", "pin": "ADS_0x48_2" },
          { "type": "turbidity", "model": "SEN0189", "pin": "A4" },
          { "type": "water_level", "model": "KIT0139", "pin": "A5" },
          { "type": "temperature", "model": "DS18B20", "pin": "D4" }
        ]
      }
    ],
    "nutrient_tanks": [
      {
        "id": "nutrient_tank_1",
        "description": "Nutrient solution tank #1",
        "sensors": [
          { "type": "ph", "model": "SEN0169-V2", "pin": "ADS_0x49_0" },
          { "type": "ec", "model": "SEN0451", "pin": "ADS_0x49_1" },
          { "type": "do", "model": "SEN0237", "pin": "ADS_0x49_2" },
          { "type": "temperature", "model": "DS18B20", "pin": "D5" }
        ]
      },
      {
        "id": "nutrient_tank_2",
        "description": "Nutrient solution tank #2",
        "sensors": [
          { "type": "ph", "model": "SEN0169-V2", "pin": "ADS_0x49_3" },
          { "type": "ec", "model": "SEN0451", "pin": "ADS_0x4A_0" },
          { "type": "do", "model": "SEN0237", "pin": "ADS_0x4A_1" },
          { "type": "temperature", "model": "DS18B20", "pin": "D6" }
        ]
      },
      {
        "id": "nutrient_tank_3",
        "description": "Nutrient solution tank #3",
        "sensors": [
          { "type": "ph", "model": "SEN0169-V2", "pin": "ADS_0x4A_2" },
          { "type": "ec", "model": "SEN0451", "pin": "ADS_0x4A_3" },
          { "type": "do", "model": "SEN0237", "pin": "ADS_0x4B_0" },
          { "type": "temperature", "model": "DS18B20", "pin": "D7" }
        ]
      }
    ],
    "cultivation_line": {
      "id": "zone_cultivation_1",
      "total_lines": 1,
      "description": "Main cultivation line gradient (Start/Mid/End)",
      "points": {
        "start": [
          { "type": "ec", "model": "SEN0451", "pin": "ADS_0x4B_1" }
        ],
        "middle": [
          { "type": "ec", "model": "SEN0451", "pin": "ADS_0x4B_2" }
        ],
        "end": [
          { "type": "ec", "model": "SEN0451", "pin": "ADS_0x4B_3" }
        ]
      }
    }
  },
  "monitoring": {
    "reading_interval_seconds": 60,
    "averaging_window": 10,
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
        "critical_max": 2000,
        "note": "Hardware saturation at 2000"
      },
      "temperature": { 
        "min": 20, 
        "max": 26, 
        "warning_min": 18,
        "warning_max": 28,
        "critical_min": 15, 
        "critical_max": 32 
      },
      "DO": { 
        "min": 5.0,
        "warning_min": 3.0,
        "critical_min": 3.0 
      },
      "water_level": { 
        "min": 80, 
        "warning_min": 60,
        "critical_min": 40,
        "note": "Stop pump at 40%"
      },
      "turbidity": { 
        "max": 50, 
        "warning_max": 100,
        "critical_max": 100 
      }
    }
  },
  "database": {
    "type": "sqlite",
    "path": "./data/aquaponics.db",
    "backup_path": "./data/backups/"
  }
}
```

## Calibration Procedures

Standard calibration protocols for the specific sensors used in the Multi-Zone system.

### pH Sensor (3-point)
* **Target:** Filter Tanks (3), Nutrient Tanks (3)
* **Solutions:** pH 4.0, 7.0, 10.0 Standard Buffers
* **Procedure:**
    1.  Clean probe with distilled water.
    2.  Start with **pH 7.0** (Mid-point) to set the zero offset.
    3.  Proceed to **pH 4.0** (Low) and **pH 10.0** (High).
    4.  Wait ~60 seconds per point for stability before confirming on the dashboard.

### EC Sensor (1-point)
* **Target:** Nutrient Tanks (3), Cultivation Line (3)
* **Solution:** **1413 μS/cm** Standard Solution ONLY.
* **Procedure:**
    1.  **Crucial:** Rinse and **completely dry** the probe before immersion (Water droplets cause errors).
    2.  Immerse in standard solution and shake gently to remove air bubbles.
    3.  Wait 1-2 mins for temperature compensation.
    4.  Trigger calibration via dashboard.

### DO Sensor (2-point)
* **Target:** Nutrient Tanks (3)
* **Solutions:**
    * **0% (Zero):** Sodium Sulfite ($Na_2SO_3$) saturated solution.
    * **100% (Span):** Air-saturated water (use an air stone/bubbler for 10 mins).
* **Procedure:**
    1.  Calibrate **0%** first in the Sodium Sulfite solution.
    2.  Rinse thoroughly.
    3.  Calibrate **100%** in the bubbled water (Suspend probe, do not touch airstone).

### Water Level (Hardware Calibration)
* **Target:** Filter Tanks (3)
* **Method:** **Physical Potentiometer Adjustment** (Not Software).
* **Procedure:**
    1.  **Zero:** Lift sensor to air (Empty). Adjust "Zero" screw on I/V Module until dashboard reads 0%.
    2.  **Span:** Submerge to max depth. Adjust "Span" screw on I/V Module until dashboard reads 100%.

### Turbidity (1-point Baseline)
* **Target:** Filter Tanks (3)
* **Solution:** Clear Water (0 NTU).
* **Procedure:**
    1.  Ensure the adapter switch is set to **"A"** (Analog).
    2.  Dip probe in clear water (Do NOT submerge the black top connector).
    3.  Trigger "Clear Calibration" on the dashboard to set the baseline voltage.

## Testing

Unit and integration tests are designed to run inside the Docker container to ensure environment consistency.

```bash
# 1. Run all tests (Recommended)
docker-compose run --rm aquaponics pytest tests/ -v

# 2. Run specific test module (e.g., Sensor Logic)
docker-compose run --rm aquaponics pytest tests/test_sensors.py -v

# 3. Run specific test case (e.g., PH Sensor 3-point Calibration)
docker-compose run --rm aquaponics pytest tests/test_sensors.py::TestPHSensor -v

# 4. Generate Coverage Report
# Displays code coverage percentage in the terminal
docker-compose run --rm aquaponics pytest --cov=app --cov-report=term-missing tests/
```

## Docker Deployment (Raspberry Pi)

Run the system in a detached Docker container.

### 1. Configuration Check (CRITICAL)
Before running, ensure `config.json` maps all 3 Filter Tanks, 3 Nutrient Tanks, and ADS1115 addresses correctly.

```bash
# Create config from example if missing
cp config.example.json config.json
nano config.json
```

### 2. Build and Start
Use `--build` to ensure the latest Python dependencies and code changes are applied.

```bash
# Build image and start container in background
docker-compose up -d --build
```

### 3. Verify Operation
Check if the container is running and reading serial data.

```bash
# Check container status
docker ps

# View live logs (Press Ctrl+C to exit)
docker logs -f aquaponics
```

### 4. Access Dashboard
* **Localhost:** `http://localhost:5000`
* **Remote:** `http://<RASPBERRY_PI_IP>:5000`

### 5. Stop System
```bash
docker-compose down
```

## Troubleshooting

### 1. Hardware & Sensor Issues

**All Sensors Read "0" or "NaN" (ADS1115):**
- **I2C Address Conflict:** Ensure your 4 ADS1115 modules have unique addresses (`0x48`, `0x49`, `0x4A`, `0x4B`) set via the ADDR pin.
- **Wiring:** Check SDA/SCL connections to the Arduino Mega (Pins 20 & 21).

**EC Sensor Reads Flat 2000 μS/cm:**
- **Saturation:** The sensor has hit its hardware limit (2.0 EC). Your nutrient solution is too strong. Dilute with fresh water.
- **Probe Check:** Ensure the probe is fully submerged and no air bubbles are trapped inside the cap.

**Water Level Sensor Reads 0%:**
- **Power Check:** Verify the **24V SMPS** is turned on. This sensor does not work with 5V.
- **I/V Converter:** Ensure the current-to-voltage module is wired correctly (Red to 24V+, Black to Signal).

**Turbidity Readings Maxed Out / Erratic:**
- **Moisture:** The black connector on top is **NOT waterproof**. If it got wet, dry it immediately with a hair dryer.
- **Switch:** Ensure the adapter board switch is set to "A" (Analog), not "D".

---

### 2. Arduino & Serial Connection

**Upload Failed:**
- **Board Selection:** Ensure "Arduino Mega 2560" is selected in IDE.
- **Port Access:** If using Linux/Pi, ensure your user is in the `dialout` group: `sudo usermod -aG dialout $USER`.
- **Busy Resource:** Stop the Docker container before uploading (`docker-compose down`), as it claims the serial port.

**"Serial Timeout" in Logs:**
- **Cable:** Try a shorter, shielded USB cable.
- **Reset:** Press the RST button on the Arduino Mega manually.

---

### 3. Docker & Dashboard

**Dashboard Not Loading (`Connection Refused`):**
- **Check Status:** `docker ps` - Is the container listed?
- **View Logs:** `docker logs -f aquaponics` - Look for Python syntax errors or crash logs.
- **Restart:** `docker-compose restart`

**Database Errors (`Database is locked`):**
- **Permissions:** Ensure the `data/` folder is writable: `sudo chmod -R 777 data/`.
- **Reset:** To factory reset (Data Loss!), delete the file:
  ```bash
  docker-compose down
  rm data/aquaponics.db
  docker-compose up -d
  ```

## Hardware Wiring

Detailed wiring diagrams for the **Multi-Zone System** (including ADS1115 I2C expansion and 24V level sensors) are available in the documentation.

> **Critical Safety Warning:**
> * **Water Level Sensors (KIT0139):** Require **24V**. Do NOT connect directly to Arduino 5V logic. Use the I/V Converter.
> * **ADS1115 Address:** Ensure jumpers are set correctly (`0x48` ~ `0x4B`) to avoid I2C collisions.

See [docs/HARDWARE_SETUP.md](docs/HARDWARE_SETUP.md) for detailed schematics.

## Documentation

Comprehensive guides are available in the `docs/` directory:

-   [**Quick Start Guide**](docs/QUICKSTART.md) - Fast-track deployment & safety checks.
-   [**Hardware Setup**](docs/HARDWARE_SETUP.md) - Wiring diagrams for 15+ sensors & ADS1115.
-   [**Installation Manual**](docs/INSTALLATION.md) - OS setup, Docker installation & Firmware upload.
-   [**Calibration Guide**](docs/CALIBRATION.md) - Procedures for pH (3-pt), EC (1-pt), DO & Level.
-   [**API Reference**](docs/API.md) - REST endpoint documentation.
-   [**Troubleshooting**](docs/TROUBLESHOOTING.md) - Solutions for common sensor/software issues.
-   [**Implementation Summary**](docs/IMPLEMENTATION_SUMMARY.md) - Architecture overview & technical specs.

## License

MIT License - See [LICENSE](LICENSE) file for details.

## Support

For maintenance requests or bug reports, please refer to the `docs/TROUBLESHOOTING.md` guide first.
For code contributions, please open an issue or pull request on the repository.

---

**Last Updated**: 2025-12-03
**Version**: 1.5.0 (Multi-Zone & Dockerized)
**Status**: Field Deployment Ready