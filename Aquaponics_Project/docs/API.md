# Aquaponics Smart Farm - API Documentation

## Overview

The **Aquaponics Smart Farm Multi-Zone** system provides a RESTful API for accessing sensor data across **3 Filter Tanks, 3 Nutrient Tanks, and 1 Cultivation Line**.

The API allows for real-time monitoring, alert management, specific sensor calibration (per tank), and dynamic configuration. It is built with Python Flask and returns standard JSON responses.

## Base URL

All endpoints are prefixed with `/api`.

```
http://<raspberry-pi-ip>:5000/api
```
*(e.g., `http://localhost:5000/api` or `http://192.168.0.10:5000/api`)*

## Authentication & Security

The system is designed for **Local Network (LAN)** use.
* **Authentication:** Open access within the local network (No API Key required by default).
* **CORS:** Enabled to allow the Web Dashboard to communicate with the API.
* **Security:** Ensure the Raspberry Pi is behind a firewall if connected to a wider network.

## Response Format

All API responses follow a unified JSON envelope structure (`JSend` style):

**Success Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "status": "success",
  "data": {
    // Endpoint-specific payload (Example: Filter Tank 1 Data)
    "filter_tank_1": {
        "ph": 7.01,
        "turbidity": 45,
        "water_level": 85.0
    }
  }
}
```

**Error Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "status": "error",
  "message": "Sensor timeout detected on Nutrient Tank 3",
  "code": 500
}
```

---

## Endpoints

### 1. System Health

#### Health Check
**GET** `/api/status`

Check if the system services (Docker, Flask, Database) are running and if the connection to the Arduino Mega is active.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-03T12:34:56",
  "system": {
    "version": "1.5.0",
    "mode": "Multi-Zone (3 Filter / 3 Nutrient / 1 Line)",
    "uptime": "2 days, 4 hours"
  },
  "components": {
    "database": "connected",
    "serial_connection": "active",
    "port": "/dev/ttyUSB0"
  }
}
```

---

### 2. Sensor Data

#### Get Current Readings
**GET** `/api/current`

Retrieve the latest sensor readings organized by Zone (A, B, C).

**Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "status": "success",
  "data": {
    "zone_a_filtered": {
      "tank_1": { "ph": 6.8, "turbidity": 50, "level": 85.5, "temp": 24.5 },
      "tank_2": { "ph": 6.8, "turbidity": 48, "level": 85.0, "temp": 24.5 },
      "tank_3": { "ph": 6.9, "turbidity": 45, "level": 84.5, "temp": 24.4 }
    },
    "zone_b_nutrient": {
      "tank_1": { "ph": 6.9, "ec": 1350, "do": 6.2, "temp": 24.6 },
      "tank_2": { "ph": 6.8, "ec": 1340, "do": 6.1, "temp": 24.5 },
      "tank_3": { "ph": 6.9, "ec": 1360, "do": 6.3, "temp": 24.6 }
    },
    "zone_c_cultivation": {
      "start": { "ec": 1340 },
      "middle": { "ec": 1320 },
      "end": { "ec": 1300 }
    }
  }
}
```
*(Note: Zone C monitors EC Gradient only. pH is controlled at the Nutrient Tanks (Zone B).)*

#### Get Historical Data
**GET** `/api/history`

Retrieve historical sensor data for charting or analysis.

**Query Parameters:**
- `hours` (optional, default=24): Number of past hours to retrieve.
- `zone` (optional): Filter by 'zone_a', 'zone_b', or 'zone_c'.
- `limit` (optional, default=1000): Maximum number of records.

**Example:**
`GET /api/history?hours=24&limit=500`

**Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "range_hours": 24,
  "count": 2,
  "data": [
    {
      "timestamp": "2025-12-03T12:30:00",
      "zone_b": {
        "tank_1": { "ph": 6.8, "ec": 1350, "temp": 24.5, "do": 6.2 },
        "tank_2": { "ph": 6.8, "ec": 1345, "temp": 24.5, "do": 6.1 },
        "tank_3": { "ph": 6.8, "ec": 1355, "temp": 24.5, "do": 6.2 }
      },
      "zone_c": { "start_ec": 1340, "mid_ec": 1320, "end_ec": 1300 }
    },
    {
      "timestamp": "2025-12-03T12:25:00",
      "zone_b": {
        "tank_1": { "ph": 6.8, "ec": 1345, "temp": 24.4, "do": 6.1 },
        "tank_2": { "ph": 6.7, "ec": 1340, "temp": 24.4, "do": 6.0 },
        "tank_3": { "ph": 6.8, "ec": 1350, "temp": 24.4, "do": 6.1 }
      },
      "zone_c": { "start_ec": 1335, "mid_ec": 1315, "end_ec": 1295 }
    }
  ]
}
```

#### Get Statistics
**GET** `/api/statistics`

Get Min/Max/Avg statistical analysis of sensor data for a specific time window.

**Query Parameters:**
- `hours` (optional, default=24): Hours to analyze.

**Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "hours": 24,
  "statistics": {
    "zone_b_tank1_ph": { "min": 6.5, "max": 7.2, "avg": 6.85, "count": 1440 },
    "zone_b_tank1_ec": { "min": 1300, "max": 1400, "avg": 1350, "count": 1440 },
    "zone_b_tank2_ph": { "min": 6.4, "max": 7.1, "avg": 6.80, "count": 1440 },
    "zone_a_tank1_level": { "min": 90, "max": 100, "avg": 95, "count": 1440 },
    "zone_a_tank1_turbidity": { "min": 0, "max": 55, "avg": 45, "count": 1440 }
  }
}
```

---

### 3. Alerts Management

#### Get Active Alerts
**GET** `/api/alerts/active`

Retrieve all active (unresolved) alerts.

**Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "count": 1,
  "alerts": [
    {
      "id": 42,
      "timestamp": "2025-12-03T11:30:00",
      "sensor_id": "zone_b_tank1_ph",
      "alert_type": "CRITICAL",
      "value": 5.2,
      "threshold_min": 6.0,
      "threshold_max": 8.0,
      "message": "CRITICAL: zone_b_tank1_ph value 5.2 is below minimum threshold 6.0",
      "resolved": false
    }
  ]
}
```

#### Get Alerts by Date Range
**GET** `/api/alerts`

Retrieve alert history logs.

**Query Parameters:**
- `start_date` (optional): ISO format datetime (default: 7 days ago)
- `end_date` (optional): ISO format datetime (default: now)
- `limit` (optional): Max records (default: 100)

**Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "count": 5,
  "alerts": [
    // Array of alert objects similar to 'Get Active Alerts'
  ]
}
```

#### Create Alert (Manual)
**POST** `/api/alert`

Manually trigger an alert (Useful for testing system notifications or "System Fault" logic).

**Request Body:**
```json
{
  "sensor_id": "zone_b_tank1_ph",
  "alert_type": "WARNING",
  "value": 5.2,
  "message": "Manual test alert: pH deviation detected in Nutrient Tank 1"
}
```

**Response:**
```json
{
  "timestamp": "2025-12-03T12:35:10",
  "status": "success",
  "alert_id": 43,
  "message": "Alert created successfully"
}
```

---

### 4. Calibration

#### Calibrate Sensor
**POST** `/api/calibration/<sensor_id>`

Trigger calibration logic for a specific sensor. The backend will calculate the slope/intercept based on the provided reference points.

**Sensor IDs (Examples):**
- Zone A (Filter): `zone_a_tank1_ph`, `zone_a_tank2_turbidity`
- Zone B (Nutrient): `zone_b_tank1_ph`, `zone_b_tank1_ec`, `zone_b_tank1_do`
- Zone C (Line): `zone_c_start_ec`

**Request Body (pH - 3-point):**
```json
{
  "calibration_type": "3-point",
  "points": {
    "low": 410,   // Raw ADC value for pH 4.0
    "mid": 307,   // Raw ADC value for pH 7.0
    "high": 205   // Raw ADC value for pH 10.0
  },
  "notes": "Standard monthly calibration for Zone B Tank 1"
}
```

**Request Body (EC - 1-point):**
```json
{
  "calibration_type": "1-point",
  "points": {
    "standard": 1413  // Target EC value (uS/cm)
  },
  "notes": "Using 1413uS standard solution (K=1.0 Probe)"
}
```

**Request Body (DO - 2-point):**
```json
{
  "calibration_type": "2-point",
  "points": {
    "zero": 0,    // Voltage/Value at 0% (Sodium Sulfite)
    "span": 100   // Voltage/Value at 100% (Air Saturated)
  },
  "notes": "Full 2-point calibration performed"
}
```

**Request Body (Turbidity - Baseline):**
```json
{
  "calibration_type": "baseline",
  "points": {
    "clear": 0    // Voltage offset for clear water (0 NTU)
  },
  "notes": "Clear water baseline established for Filter Tank 1"
}
```

**Response:**
```json
{
  "status": "success",
  "sensor_id": "zone_b_tank1_ph",
  "timestamp": "2025-12-03T12:40:00",
  "message": "Calibration constants updated successfully"
}
```

> **Note:** **Water Level Sensors (KIT0139)** are calibrated via hardware potentiometers on the I/V Converter module (Zero/Span), not via this API.

#### Get Calibration History
**GET** `/api/calibration/<sensor_id>`

Retrieve the last 10 calibration records for a specific sensor.

**Response:**
```json
{
  "sensor_id": "zone_b_tank1_ph",
  "history": [
    {
      "timestamp": "2025-12-03T10:00:00",
      "calibration_type": "3-point",
      "points": {
        "low": 410,
        "mid": 307,
        "high": 205
      },
      "valid": true,
      "notes": "Standard monthly calibration"
    }
  ]
}
```

---

### 5. Configuration

#### Get Current Configuration
**GET** `/api/config`

Retrieve current system configuration, including active zones, hardware settings (ADC mapping), and alert thresholds.

**Response:**
```json
{
  "timestamp": "2025-12-03T12:45:00",
  "config": {
    "site_name": "Aquaponics Smart Farm Multi-Zone",
    "hardware": {
      "port": "/dev/ttyUSB0",
      "baud_rate": 115200,
      "platform": "arduino_mega",
      "adc_modules": [
        { "address": "0x48", "usage": "Filter Tank Sensors" },
        { "address": "0x49", "usage": "Nutrient Tank Sensors (1 & 2)" }
      ]
    },
    "zones": {
      "filtered_tanks": [
        { "id": "filter_tank_1", "description": "Recirculation water tank #1", "sensors": [...] },
        { "id": "filter_tank_2", "description": "Recirculation water tank #2", "sensors": [...] },
        { "id": "filter_tank_3", "description": "Recirculation water tank #3", "sensors": [...] }
      ],
      "nutrient_tanks": [
        { "id": "nutrient_tank_1", "description": "Nutrient solution tank #1", "sensors": [...] },
        { "id": "nutrient_tank_2", "description": "Nutrient solution tank #2", "sensors": [...] },
        { "id": "nutrient_tank_3", "description": "Nutrient solution tank #3", "sensors": [...] }
      ],
      "cultivation_line": {
        "id": "zone_cultivation_1",
        "points": { "start": [...], "middle": [...], "end": [...] }
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
          "critical_min": 800,
          "critical_max": 2000  // Hardware Limit (Saturation)
        },
        "water_level": {
          "min": 80,
          "critical_min": 40    // Pump Cut-off Level
        },
        "turbidity": {
          "max": 50,
          "critical_max": 100
        }
      }
    }
  }
}
```

#### Update Configuration
**POST** `/api/config`

Update system settings dynamically. This supports "Hot-Reload" for thresholds and intervals without restarting the container.

**Request Body:**
```json
{
  "monitoring": {
    "reading_interval_seconds": 60,
    "alert_thresholds": {
      "pH": {
        "min": 6.5,
        "max": 7.2
      },
      "EC": {
        "min": 1200,
        "max": 1500
      }
    }
  }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Configuration updated. New settings applied immediately."
}
```

---

### 6. Data Management

#### Export Data
**GET** `/api/export`

Export sensor data in CSV, JSON, or Excel format for offline analysis.

**Query Parameters:**
- `format` (required): `csv`, `json`, or `xlsx` (Excel).
- `hours` (optional, default=24): Hours of data to export.
- `zone` (optional): Filter by specific zone (e.g., `zone_a`, `zone_b`, `zone_c`).

**Example:**
`GET /api/export?format=csv&hours=168&zone=zone_b`

**JSON Response:**
```json
{
  "timestamp": "2025-12-03T12:34:56",
  "hours": 168,
  "count": 288,
  "data": [
    // Array of flat reading objects
  ]
}
```

**CSV Response:**
(Returns a downloadable file attachment with specific Tank IDs in headers)
```csv
timestamp,zone_b_tank1_ph,zone_b_tank1_ec,zone_b_tank2_ph,zone_b_tank2_ec,status
2025-12-03T12:30:00,6.8,1350,6.9,1340,OK
2025-12-03T12:25:00,6.8,1345,6.8,1345,OK
...
```

---

## Error Responses

The API uses standard HTTP status codes. Error bodies follow the same JSON structure as successful responses but with `status: "error"`.

### 400 Bad Request
Occurs when required parameters are missing or invalid (e.g., wrong calibration points).

```json
{
  "timestamp": "2025-12-03T12:34:56",
  "status": "error",
  "message": "Invalid request parameters: missing 'format'",
  "code": 400
}
```

### 404 Not Found
Occurs when the requested resource (e.g., a specific Alert ID or Sensor ID) does not exist.

```json
{
  "timestamp": "2025-12-03T12:34:56",
  "status": "error",
  "message": "Resource not found: Sensor 'zone_b_tank99_ph' does not exist",
  "code": 404
}
```

### 500 Internal Server Error
Occurs when the server encounters a critical issue (e.g., Database lock, Serial port disconnection).

```json
{
  "timestamp": "2025-12-03T12:34:56",
  "status": "error",
  "message": "Internal server error: Serial port /dev/ttyUSB0 is unresponsive",
  "code": 500
}
```

---

## Rate Limiting

Rate limits are enforced to prevent system overload on the Raspberry Pi. Limits are applied per **IP Address**.

- **Default Limit:** 60 requests per minute (Configurable via `config.json`)
- **Headers:** The API includes standard rate-limit headers in every response:

| Header | Description |
| :--- | :--- |
| `X-RateLimit-Limit` | The maximum number of requests allowed per window. |
| `X-RateLimit-Remaining` | The number of requests remaining in the current window. |
| `X-RateLimit-Reset` | The time (in UTC epoch seconds) when the limit will reset. |

**Example Headers:**
```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 55
X-RateLimit-Reset: 1733112000
Content-Type: application/json
```

---

## Example Usage

### Curl Command

**Get Current Readings:**
```bash
curl -s http://localhost:5000/api/current | python3 -m json.tool
```

**Calibrate EC Sensor (1413 uS/cm):**
```bash
# Calibrate Zone B - Tank 1 EC Sensor
curl -X POST http://localhost:5000/api/calibration/zone_b_tank1_ec \
  -H "Content-Type: application/json" \
  -d '{"calibration_type": "1-point", "points": {"standard": 1413}}'
```

**Export Last 24 Hours to CSV:**
```bash
curl "http://localhost:5000/api/export?format=csv&hours=24&zone=zone_b" > nutrient_report.csv
```

### Python Example

```python
import requests
import json

BASE_URL = "http://localhost:5000/api"

def get_system_status():
    try:
        # 1. Check API Connection
        status_resp = requests.get(f"{BASE_URL}/status")
        status_resp.raise_for_status()
        print(f"System Uptime: {status_resp.json()['system'].get('uptime')}")

        # 2. Get Real-time Sensor Data
        data_resp = requests.get(f"{BASE_URL}/current")
        data_resp.raise_for_status()
        
        payload = data_resp.json()
        
        # Accessing Zone B (Nutrient Tanks) -> Tank 1 Data
        zone_b = payload['data']['zone_b_nutrient']
        tank_1 = zone_b['tank_1']
        
        print(f"Nutrient Tank 1 pH: {tank_1['ph']}")
        print(f"Nutrient Tank 1 EC: {tank_1['ec']} uS/cm")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    get_system_status()
```

---

## CORS Support

The API supports **Cross-Origin Resource Sharing (CORS)** to allow the Web Dashboard (running in the browser) to communicate with the Flask backend.
- **Allowed Origins:** `*` (All origins allowed by default for local LAN access).
- **Methods:** `GET`, `POST`, `OPTIONS`.
- **Headers:** `Content-Type`, `Authorization`.

---

## Changelog

### Version 1.5.0 (2025-12-03)
- **Architecture:** Expanded to **Multi-Zone** architecture (3 Filter Tanks, 3 Nutrient Tanks, 1 Cultivation Line).
- **Hardware:** Added support for **4x ADS1115** modules to handle 15+ analog sensors.
- **Safety:** Added critical safety logic for **24V Water Level Sensors** and **EC Sensor Saturation** (>2000 uS/cm).
- **API:** Updated endpoints to support nested Tank IDs (e.g., `zone_b_tank1_ec`).
- **Deployment:** Fully Dockerized with persistent volume mapping (`~/aquaponics/data`).

### Version 1.4.0 (2025-11-20)
- Initial Docker support.
- Added SQLite WAL mode for better concurrency.
- Implemented basic 3-point pH calibration.