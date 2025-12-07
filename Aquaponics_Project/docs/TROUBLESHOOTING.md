# Aquaponics Smart Farm - Troubleshooting Guide

This document provides diagnostic steps and solutions for common issues encountered with the **Smart Aquaponics Multi-Zone System**.
It focuses on diagnosing communication faults between the **Dockerized Raspberry Pi**, the **Arduino Mega**, and the **4x ADS1115 I2C modules** which manage 20+ sensors.

---

## Quick Diagnostics

Run these commands on the Raspberry Pi terminal to check the system status in sequential order.

```bash
# 0. Verify Arduino USB Connection (Serial Port Mapping)
ls -l /dev/ttyUSB0
# CRITICAL: If this file is not found, check the USB cable or 'dialout' permissions.

# 1. Check if the Docker container is running
docker ps | grep aquaponics
# Status should be 'Up X hours'

# 2. View real-time application logs
docker logs -f aquaponics
# Look for: "Serial connection established" or "I2C Device Not Found"

# 3. Check Database Integrity
sqlite3 data/aquaponics.db "PRAGMA integrity_check;"
# Should output: "ok"

# 4. Check recent log file content (Host Volume)
tail -f data/logs/app.log
# Use this to check historical Python errors.
```

---

## Common Issues and Solutions

### 1. Dashboard Not Loading
**Symptom:** Cannot access web interface at `http://<RPI-IP>:5000`

**Possible Causes:**
- Docker container stopped or crashed.
- Port 5000 is blocked or used by another app.
- SD Card is full.

**Solutions:**
```bash
# Check container status
docker-compose ps

# If State is 'Exit', check logs for crash reason
docker logs aquaponics
# Look for Python syntax errors or address binding errors.

# Restart the service
docker-compose restart

# Check disk space usage
df -h
```

---

### 2. No Sensor Readings / Specific Sensor Failures
**Symptom:** Dashboard shows empty, zero, or "NaN" readings.

#### A. Critical Hardware/I2C Checks
* **All Sensors on a Zone Missing (e.g., All Zone B data is 0):**
    * **Cause:** The **ADS1115 module** for that zone might have an **I2C Address Conflict** or a faulty I2C connection.
    * **Fix:** Check **ADS1115 ADDR jumpers** (`0x48`~`0x4B`) as per `HARDWARE_SETUP.md`. Ensure SCL/SDA lines are secure.
* **Water Level (KIT0139) reads 0%:**
    * **Cause:** **24V SMPS** is off or wiring error in the 4-20mA loop.
    * **Fix:** Ensure the **24V SMPS** is powering the I/V converter.
* **EC (SEN0451) reads flat 2000:**
    * **Cause:** **Saturation.** The water salinity exceeds the sensor limit (>2.0 EC).
    * **Fix:** Dilute the water immediately.
* **Turbidity (SEN0189) reads max/min:**
    * **Cause:** Connector housing got wet (Not waterproof).
    * **Fix:** Dry the connector immediately and check the adapter switch is set to "A".

#### B. General Software Diagnostics (Command Line)
If hardware seems fine, use these commands to trace the data path.

**Step 1: Verify Arduino Serial Connection**
```bash
# Check if Pi sees the Arduino
ls -l /dev/ttyUSB0
# If missing, check USB cable or ensure your user is in the 'dialout' group.
```

**Step 2: Check Arduino I2C Initialization Logs**
```bash
# View logs for ADS initialization errors
docker logs aquaponics | grep -i "I2C"
# Look for: "I2C Device Not Found" or "ADS1115 Error".
```

**Step 3: Check Real-time Data Parsing (API)**
```bash
# Check individual sensor health via API (using a specific Tank ID)
curl http://localhost:5000/api/current | python -m json.tool
# Verify nested data structure (Zone -> Tank) is present and values are non-zero/non-NaN.
```

---

### 3. Sensor Readings Fluctuating Wildly
**Symptom:** Values jump erratically (e.g., pH jumps 6.0 -> 8.5 -> 6.0).

**Possible Causes:**
- **Ground Loops:** Caused by noise from pumps or mixed 5V/24V power sources.
- **I2C Bus Noise:** Unstable power to the ADS1115 modules.
- **Moisture:** Water contamination on non-waterproof connectors (especially Turbidity/EC).
- **Calibration Drift:** EC or pH probe membranes aging or dirty.

**Solutions:**
1.  **Check Grounds:** Ensure **Arduino GND, Ext 5V GND, and 24V GND** are securely connected at a single common point (essential for reducing noise).
2.  **Check Isolation:** Verify the **DFR0504 Analog Isolators** are correctly wired between the pH/EC/DO probes and the ADS1115 inputs.
3.  **Increase Averaging:**
    ```bash
    # Edit config.json: Increase "averaging_window" (e.g., 10 -> 20)
    nano config.json
    docker-compose restart
    ```
4.  **Inspect Connections:** Check terminal blocks and ADS1115 boards for loose wiring.

---

### 4. "Sensor Timeout" Errors
**Symptom:** Logs show `SENSOR_TIMEOUT`, `I2C Bus Lockup`, or dashboard is offline.

**Solutions:**
1.  **Check USB Cable:** Unplug and replug the USB cable between the Pi and Arduino.
2.  **Test Raw Serial Data (Isolate Arduino):**
```bash
# Stop app first to free the serial port
docker-compose stop

# Read raw serial data (Requires minicom on host)
minicom -D /dev/ttyUSB0 -b 115200
# Output should show the NESTED JSON structure: {"zone_a": {...}, "zone_b": {...}}

# Restart app
docker-compose up -d
```
3.  **Check I2C Connection:** Verify the physical connection of the ADS1115 modules (SDA/SCL) and run the I2C scan on the Arduino.

---

### 5. Database Errors
**Symptom:** `database is locked` or `disk I/O error`.

**Solutions:**
```bash
# 1. Check File Permissions (Ensure Docker user can write)
ls -la data/
# The 'aquaponics.db' file must be writable by the user.

# 2. Fix Permissions (Set Docker user as owner)
sudo chown -R $USER:$USER data/
sudo chmod 775 data/

# 3. Reset Database (Last Resort - Data Loss!)
# Use this ONLY if integrity is permanently broken. Back up data first.
docker-compose down
mv data/aquaponics.db data/aquaponics.db.bak
docker-compose up -d
```

---

### 6. Calibration Issues
**Symptom:** Calibration fails or readings remain incorrect across one or more tanks.

**Specific Sensor Procedures (Check if you used the correct standard):**
- **EC (SEN0451 / 6x):**
    - Must use **1413 μS/cm** standard solution. Do not use high-salinity standards.
    - **CRITICAL:** Check if the probe is reading a flat **2000 μS/cm**. If so, the sensor is saturated (the water is too concentrated).
- **pH (SEN0169-V2 / 6x):**
    - Supports 3-point calibration (4.0, 7.0, 10.0). Ensure probe bulb is moist.
- **DO (SEN0237 / 3x):**
    - Requires 2-point calibration (0% Sodium Sulfite / 100% Air Saturation).
- **Turbidity (SEN0189 / 3x):**
    - Requires 1-point baseline (Clear Water 0 NTU).
- **Water Level (KIT0139 / 3x):**
    - **Hardware Only:** Calibration must be done by adjusting the **ZERO/SPAN potentiometers** on the I/V Converter module.

**Possible Causes:**
- Calibration solutions expired or contaminated.
- Sensor probe is dirty, dry (pH), or membrane cap is faulty (DO).
- **ADS1115 Gain Issue:** If raw ADC values are too high/low after calibration, check ADS1115 gain settings in the firmware.

**Solutions (Check DB Persistence):**
```bash
# Verify calibration data persistence for a specific sensor (e.g., Nutrient Tank 1 pH)
sqlite3 data/aquaponics.db "SELECT * FROM calibrations WHERE sensor_id='zone_b_tank1_ph' ORDER BY timestamp DESC LIMIT 5;"
# If the entry is missing or valid=0, repeat calibration.
```

---

### 7. High Alert Threshold

**Symptom:** System constantly triggering false alerts across one or more tanks.

**Possible Causes:**
- **Thresholds Set Too Tight:** Current `min`/`max` bounds in `config.json` are narrower than natural system fluctuation.
- **Calibration Issue:** Sensor value is offset due to drift or incorrect initial calibration.
- **Systematic Noise:** Ground loop or I2C/Serial instability causing readings to jump (See Section 3).

**Solutions:**
1.  **Review System Statistics:** Analyze the actual Min/Max range for the last 24 hours per tank.
```bash
# Review Min/Max/Avg readings per tank
curl http://localhost:5000/api/statistics?hours=24 | python -m json.tool
```

2.  **Check Current Thresholds (Configuration is Nested):**
```bash
# Check current thresholds structure in config.json
curl http://localhost:5000/api/config | python -m json.tool | grep -A 20 alert_thresholds
```

3.  **Update Thresholds (Using Nested API POST):**
```bash
# Edit config.json on host, OR use API for hot-reload:
curl -X POST http://localhost:5000/api/config \
-H "Content-Type: application/json" \
-d '{"monitoring": {"alert_thresholds": {"pH": {"min": 6.5, "max": 7.5}}}}'
```

4.  **Monitor Alert Patterns (Filtering by specific Sensor ID):**
```bash
# Check alerts for a specific sensor (e.g., Nutrient Tank 1 pH)
sqlite3 data/aquaponics.db \
"SELECT timestamp, sensor_id, alert_type, value FROM alerts WHERE sensor_id='zone_b_tank1_ph' ORDER BY timestamp DESC LIMIT 20;"
```

---

### 8. Performance Issues

**Symptom:** Dashboard slow, high CPU usage, or sensor data updates lag significantly.

**Solutions:**

```bash
# 1. Check Docker Resource Usage (CPU & Memory)
docker stats aquaponics
# If CPU is consistently near 100%, check the data processing load.

# 2. Database Maintenance (Shrink SQLite size)
# Run vacuum from host to free up space from deleted historical data
sqlite3 data/aquaponics.db "VACUUM;"

# 3. Reduce Data Processing Load (Check config.json)
# If readings are too frequent, increase the interval or averaging window.
# Edit config.json -> monitoring section
# Then restart: docker-compose restart

# 4. Log Rotation
# Check if logs are consuming too much space
du -sh data/logs/
# (Config sets max_file_size_mb: 10, backup_count: 5)
```

---

### 9. Network Connectivity Issues

**Symptom:** Cannot access dashboard from another device on the local network (`http://<RPI-IP>:5000`).

**Possible Causes:**
- Raspberry Pi is offline or using the wrong IP.
- Firewall (ufw) blocking port 5000.
- Docker port mapping failed on the host.
- WiFi stability issues.

**Solutions:**

```bash
# 1. Check network status and IP address on the Pi
ip addr show
# or
ifconfig

# 2. Test connectivity (Host level check)
ping <pi-ip>

# 3. Check application binding (Verify Docker port mapping)
sudo netstat -tlnp | grep 5000
# Should show listening on 0.0.0.0:5000 on the host interface.

# 4. Check if port is open (Remotely test connection)
telnet <pi-ip> 5000
# or (if nmap is installed)
sudo nmap -p 5000 <pi-ip>

# 5. Check firewall (If UFW is active)
sudo ufw status
sudo ufw allow 5000/tcp # If needed

# 6. Restart network service (Troubleshoot WiFi/Ethernet issues)
sudo systemctl restart networking
# or for Network Manager: sudo nmcli con up <SSID>
```

---

## Advanced Diagnostics

### Enable Debug Mode
To see detailed sensor parsing and I2C communication logs:

```bash
# 1. Edit config.json
nano config.json
# Change "logging": { "level": "INFO" } -> "DEBUG"

# 2. Restart Container
docker-compose restart

# 3. Monitor Logs
docker logs -f aquaponics
# Look for detailed serial logs and I2C status updates.
```

### Manual API Testing
Use `curl` to manually trigger actions or read data, ensuring the API is functioning correctly with multi-zone targeting.

```bash
# Trigger a manual alert (Requires explicit sensor_id targeting)
curl -X POST http://localhost:5000/api/alert \
  -H "Content-Type: application/json" \
  -d '{"sensor_id": "zone_b_tank1_ph", "alert_type": "WARNING", "value": 5.2, "message": "Manual Test Alert"}'

# Download data as CSV (Note: Output headers include Tank IDs)
curl -o data_export.csv "http://localhost:5000/api/export?format=csv&hours=1"
```

### Test Sensor Hardware Directly

Since the application runs in Docker, direct serial access requires stopping the container or entering it.

**Method 1: Stop Docker and Test on Host**
```bash
docker-compose down
# Now you can use minicom or python serial on the host
minicom -D /dev/ttyUSB0 -b 115200
```

**Method 2: Check Serial Device Mapping**
```bash
# Verify the container sees the USB device
docker exec -it aquaponics ls -l /dev/ttyUSB0
```

**Arduino (via Serial Monitor):**
1. Connect Arduino to PC.
2. Open Serial Monitor (Baud 115200).
3. **Check Startup Log:** Verify `Found ADS1115 at 0x48, 0x49, 0x4A, 0x4B`.
4. Check data stream: Ensure it prints the **Nested JSON structure** (`{"zone_a": {"tank_1": {...}}, ...}`).

**Raspberry Pi (via Terminal):**
```bash
# Read raw serial data directly from Python and attempt JSON parsing
python3 -c "
import serial
import time
import json

try:
    ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)
    time.sleep(2) # Wait for connection
    if ser.in_waiting > 0:
        raw_data = ser.readline().decode('utf-8').strip()
        try:
            # Attempt to parse the nested JSON structure
            parsed = json.loads(raw_data)
            print('Successfully Parsed Nested JSON:')
            print(json.dumps(parsed, indent=2))
        except json.JSONDecodeError:
            print(f'ERROR: JSON Decode Failed. Raw Data: {raw_data}')
    else:
        print('No data waiting...')
    ser.close()
except Exception as e:
    print(f'Error: {e}')
"
```

### Monitor Sensor Data in Real-Time

```bash
# Watch API output (Output is NESTED JSON: Zone -> Tank)
watch -n 5 'curl -s http://localhost:5000/api/current | python3 -m json.tool'

# Or tail the logs
tail -f data/logs/app.log | grep -i "sensor\|I2C"
```

### Database Query Examples

```bash
-- Get all readings from last 24 hours for a specific tank (e.g., Nutrient Tank 1)
sqlite3 data/aquaponics.db \
  "SELECT timestamp, sensor_type, value FROM sensor_readings WHERE tank_id='nutrient_tank_1' AND timestamp > datetime('now', '-1 day') ORDER BY timestamp DESC;"

-- Get critical alerts (using specific sensor ID)
sqlite3 data/aquaponics.db \
  "SELECT timestamp, sensor_id, message FROM alerts WHERE alert_type='CRITICAL' AND sensor_id='zone_b_tank1_ph' ORDER BY timestamp DESC LIMIT 10;"

-- Get calibration history (for a specific EC sensor)
sqlite3 data/aquaponics.db \
  "SELECT timestamp, sensor_id, calibration_type, slope, intercept FROM calibrations WHERE sensor_id='zone_b_tank1_ec' ORDER BY timestamp DESC LIMIT 10;"
```

---

## Performance Metrics

### Expected System Performance

| Metric | Expected Value | Warning Level | Critical Level |
| :--- | :--- | :--- | :--- |
| **CPU Usage** | <30% | >70% | >90% |
| **Memory Usage** | <50% | >80% | >95% |
| **Disk Usage** | <70% | >85% | >95% |
| **API Response Time** | <100ms | >500ms | >2s |
| **Sensor Read Rate** | 100% | <80% | <60% |
| **Database Size** | <1GB (90 days) | >5GB | >10GB |

---

## Getting Help

If problems persist:

1.  **Collect diagnostic data (Package):**
    Gather this information before opening an issue or contacting support.

    ```bash
    mkdir aquaponics_diagnostic
    # Log path updated based on config.json
    cp data/logs/app.log aquaponics_diagnostic/

    # Current real-time readings (Multi-Zone Nested JSON)
    curl http://localhost:5000/api/current > aquaponics_diagnostic/current_readings.json
    
    # Current system configuration (Crucial for threshold/hardware checks)
    curl http://localhost:5000/api/config > aquaponics_diagnostic/current_config.json 
    
    # Database schema and data dump
    sqlite3 data/aquaponics.db ".dump" > aquaponics_diagnostic/database_dump.sql
    
    # System logs and info
    dmesg | tail -50 > aquaponics_diagnostic/system_log.txt
    uname -a > aquaponics_diagnostic/system_info.txt
    ```

2.  **Check documentation:**
    -   Review relevant sections in other docs (especially `TROUBLESHOOTING.md` itself).
    -   Check `CALIBRATION.md` for specific sensor procedures (e.g., pH/EC 3-point/1-point).
    -   Review `HARDWARE_SETUP.md` for physical wiring and **ADS1115 addressing**.
    -   Check `API.md` for correct endpoint usage and JSON structure.

3.  **Consult logs:**
    -   `data/logs/app.log` - Application logs (Look for `ERROR` or `I2C` messages).
    -   `journalctl` - System logs (if using systemd).
    -   `/var/log/syslog` - System messages.

4.  **Test in isolation:**
    -   Test sensors independently (using Arduino Serial Monitor).
    -   Test API endpoints with `curl` (verify data structure).
    -   Test database queries directly (check if the new Multi-Zone schema is populated).