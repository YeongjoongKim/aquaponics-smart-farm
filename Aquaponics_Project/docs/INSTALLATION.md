# Aquaponics Smart Farm - Installation Guide

This comprehensive guide details the installation process using **Docker** for the Raspberry Pi and the firmware upload for the Arduino Mega. It includes advanced setup for backups, security, and maintenance.

---

## 1. System Requirements

### Hardware Requirements
- **Raspberry Pi:**
  - Model: Raspberry Pi 4B (4GB+) or Raspberry Pi 5
  - Storage: MicroSD Card 32GB+ (Class 10 / High Endurance recommended)
  - Power: Official USB-C Power Supply (5.1V 3A for Pi 4, 5A for Pi 5)
  - Network: Ethernet (preferred for stability) or WiFi 5GHz
- **Arduino & Expansion:**
  - Model: **Arduino Mega 2560 R3** (Main Controller)
  - Expansion: **4x ADS1115 ADC Modules** (Essential for connecting 20+ analog sensors)
  - Connection: USB Type-A to Type-B Cable (Shielded, <30cm length recommended)
- **Sensors & Actuators (Multi-Zone Config):**
  - **Zone A (3x Filter Tanks):** 3x pH, 3x Turbidity, 3x Level, 3x Temp
  - **Zone B (3x Nutrient Tanks):** 3x pH, 3x EC, 3x DO, 3x Temp
  - **Zone C (1x Cultivation Line):** 3x EC (Start/Mid/End Gradient)
- **Power Supply (Critical):**
  - **External 5V (3A+):** Powers ~20 analog sensors (pH, EC, DO, Turbidity, Temp) & ADS modules.
  - **24V DC SMPS:** Exclusively for **Water Level Sensors (KIT0139)** via I/V Converters.

### Software Requirements
- **Operating System:** Raspberry Pi OS (64-bit) - Lite (Headless) or Desktop
- **Container Engine:** Docker Engine 20.10+ & Docker Compose V2
- **Firmware Tools:** Arduino IDE 1.8.x or 2.x
- **Utilities:** Git, HTOP, Curl, Nano/Vim

---

## 2. Raspberry Pi Setup (Host Environment)

### Step 1: Operating System Preparation
1. Flash **Raspberry Pi OS (64-bit)** using Raspberry Pi Imager.
2. **Advanced Options:** Set hostname (e.g., `aquaponics-pi`), enable SSH, and set username/password.
3. Insert SD card, power on, and connect via SSH.

```bash
# 1. Update system repositories and packages
sudo apt update && sudo apt upgrade -y

# 2. Install essential system utilities
sudo apt install -y git curl htop vim net-tools sqlite3
```

### Step 2: Install Docker Engine
We use Docker to isolate the application environment, ensuring stability and easy updates.

```bash
# 1. Download and run the official Docker installation script
curl -sSL [https://get.docker.com](https://get.docker.com) | sh

# 2. Add current user ('pi') to docker group (for Docker commands)
sudo usermod -aG docker $USER

# 3. Add user to dialout group (REQUIRED for Serial Port access to Arduino)
sudo usermod -aG dialout $USER

# 4. Apply group changes (Log out and back in, or run this)
newgrp docker

# 5. Verify installation
docker version
docker compose version
```

### Step 3: Application Deployment
Download the source code and prepare the directory structure.

```bash
# 1. Clone the repository into 'aquaponics' folder explicitly
cd ~
git clone <repository-url> aquaponics
cd aquaponics

# 2. Create directory structure for persistent data
# These folders will be mounted into the Docker container
mkdir -p data/logs
mkdir -p data/backups

# 3. Set directory permissions
# Ensures the container user has write access to save DB and Logs
chmod -R 777 data/
```

### Step 4: System Configuration (Crucial)
Create and customize the configuration file to match your Multi-Zone hardware setup.

```bash
# 1. Create config from template
cp config.example.json config.json

# 2. Edit configuration
nano config.json
```

**Configuration Checklist:**
- [ ] **Serial Port:** Set to `/dev/ttyUSB0` (Verify using `ls /dev/ttyUSB*`).
- [ ] **ADS1115 Mapping:** Ensure `adc_modules` addresses (`0x48`~`0x4B`) match your physical wiring jumpers.
- [ ] **Zone Definition:** Verify all **3 Filter Tanks** and **3 Nutrient Tanks** are enabled in the `zones` array.
- [ ] **Thresholds:** Update `alert_thresholds` (especially **EC < 2000** and **Level > 40%**) to match your safety requirements.
- [ ] **Interval:** Verify `reading_interval_seconds` (Default: 60s).

---

## 3. Arduino Setup (Sensor Node)

### Step 1: Install Arduino IDE & Libraries
Perform this step on a PC or Laptop before connecting the Arduino to the Pi.

**Required Libraries (Manage Libraries):**
1.  **`Adafruit ADS1X15`** (by Adafruit) - **Critical for 4x ADC Modules**
2.  `OneWire` (by Paul Stoffregen) - For DS18B20 Temp
3.  `DallasTemperature` (by Miles Burton) - For DS18B20 Temp
4.  `ArduinoJson` (by Benoit Blanchon) - **Must be Version 6.x**
5.  *(Optional)* `DFRobot_EC` / `DFRobot_PH` (If using specific vendor logic, though custom logic is recommended for ADS1115)

### Step 2: Flash Firmware
1.  Open `arduino/arduino.ino` in Arduino IDE.
2.  Go to **Tools > Board** and select **Arduino Mega 2560**.
3.  Select the correct **Port**.
4.  Click **Upload**.
5.  **Verify:** Open Serial Monitor (115200 baud). You should see a **Nested JSON stream**:
    * Example: `{"zone_a": {"tank_1": {...}}, "zone_b": ...}`

### Step 3: Connect to Raspberry Pi
1.  Connect the Arduino to the Raspberry Pi USB port.
2.  Verify the device name on the Pi:
    ```bash
    ls -l /dev/ttyUSB*
    # Output should look like: crw-rw---- 1 root dialout ... /dev/ttyUSB0
    ```

---

## 4. Launching the Application

### Step 1: Build and Run
Use Docker Compose to build the Python environment and start the service.

```bash
cd ~/aquaponics

# Build images and start containers in detached mode (background)
docker-compose up -d --build
```

### Step 2: Verification
Check if the system is running correctly.

```bash
# 1. Check Container Status
docker ps
# STATUS should be "Up X seconds"

# 2. Check Application Logs
# This shows the live output from the Python application
docker logs -f aquaponics
# Look for: "INFO: Serial connection established"
# Look for: "INFO: Multi-Zone Configuration Loaded"
# Press Ctrl+C to exit logs
```

### Step 3: Access Dashboard
Open a browser on any device connected to the same network.
* **URL:** `http://<raspberry-pi-ip>:5000`

---

## 5. Post-Installation & Maintenance

### A. Automatic Startup (Service)
Docker Compose handles the auto-start policy. The `docker-compose.yml` file includes `restart: unless-stopped`.
* **Test:** Run `sudo reboot`. The system should come back online automatically within 60 seconds.

### B. Setup Automated Backups (Cron Job)
This script creates a daily backup of the SQLite database and deletes backups older than 30 days to save space.

1.  **Create Backup Script:**
    ```bash
    nano backup.sh
    ```

2.  **Paste the following content:**
    ```bash
    #!/bin/bash
    # Configuration
    # Ensure this path matches your git clone folder
    PROJECT_DIR="/home/pi/aquaponics"
    DATA_DIR="$PROJECT_DIR/data"
    BACKUP_DIR="$DATA_DIR/backups"
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)

    # Ensure backup directory exists
    mkdir -p $BACKUP_DIR

    # 1. Perform Backup (Copy SQLite DB)
    # Using simple copy with WAL checkpointing implies potential risk if active, 
    # but 'sqlite3 .backup' is safer if sqlite3 is installed on host.
    if command -v sqlite3 &> /dev/null; then
        sqlite3 "$DATA_DIR/aquaponics.db" ".backup '$BACKUP_DIR/aquaponics_$TIMESTAMP.db'"
    else
        cp "$DATA_DIR/aquaponics.db" "$BACKUP_DIR/aquaponics_$TIMESTAMP.db"
    fi

    # 2. Cleanup: Delete backups older than 30 days
    find $BACKUP_DIR -name "aquaponics_*.db" -mtime +30 -delete

    echo "Backup $TIMESTAMP completed."
    ```

3.  **Enable Automation:**
    ```bash
    chmod +x backup.sh

    # Open Crontab
    crontab -e

    # Add this line to run daily at 03:00 AM
    0 3 * * * /home/pi/aquaponics/backup.sh >> /home/pi/aquaponics/data/logs/backup.log 2>&1
    ```

### C. Sensor Calibration
**Critical Step:** The sensors are not calibrated out-of-the-box.
1.  Go to Dashboard > **Settings**.
2.  Select **Calibration**.
3.  **Select Target:** Choose the specific tank sensor (e.g., **"Nutrient Tank 1 - pH"**).
4.  Follow the wizard instructions (3-point for pH, 1-point for EC).
5.  See `CALIBRATION.md` for detailed procedures.

---

## 6. Developer & Testing Tools

If you are modifying code or need to debug, use these commands.

### Running Unit Tests (Inside Docker)
You don't need to install pytest on the host. Run it inside the container to verify the new **Multi-Zone logic** and **Sensor Saturation** checks.

```bash
# Run all tests (Recommended)
docker-compose run --rm aquaponics pytest

# Run specific test file (e.g., Sensor Logic)
docker-compose run --rm aquaponics pytest tests/test_sensors.py

# Run with verbose output to see individual test cases
docker-compose run --rm aquaponics pytest -v
```

### Accessing Database Directly
```bash
# Open SQLite shell on the host
sqlite3 data/aquaponics.db

# Example Queries (Multi-Zone Schema):
# .tables                                         -- List tables
# SELECT * FROM sensor_readings LIMIT 5;          -- Raw data check
# -- Check specific tank data
# SELECT timestamp, tank_id, value FROM sensor_readings WHERE tank_id='nutrient_tank_1' ORDER BY timestamp DESC LIMIT 5;
# -- Check active alerts
# SELECT * FROM alerts WHERE resolved=0;
# .quit                                           -- Exit
```

---

## 7. Safety Checklist (Final Review)

Before leaving the system unattended, verify the following critical points:

- [ ] **Power Stability:** Raspberry Pi power supply is 5.1V/3A+ (Official PSU recommended).
- [ ] **Aux Power:** **24V PSU** is connected **ONLY** to Water Level Sensors via I/V Converters.
- [ ] **I2C Bus:** Confirm all **4 ADS1115 modules** are detected (`0x48`, `0x49`, `0x4A`, `0x4B`) on startup.
- [ ] **Wiring:** All wires are secured in cable glands; no exposed copper (especially 24V lines).
- [ ] **Leak Check:** Sensor probes are sealed; no water entering the electronics box.
- [ ] **Network:** Static IP or DHCP Reservation set for the Raspberry Pi.
- [ ] **Recovery:** System auto-restarts after power loss simulation.
- [ ] **Data:** Database is being populated (Check `ls -l data/aquaponics.db` size increasing).
- [ ] **Alerts:** Test a manual alert (e.g., unplug a sensor) and verify the Dashboard shows a "System Fault".

---

## 8. Updating the System

To update the software when a new version is released (e.g., adding new sensor logic or dashboard features):

```bash
cd ~/aquaponics

# 1. Backup Data (Highly Recommended)
# Run the backup script manually before updating
./backup.sh

# 2. Get latest code
git pull origin main

# 3. Rebuild container
# This updates Python dependencies and applies new hardware logic
docker-compose up -d --build

# 4. Cleanup
# Remove old unused Docker images to free up SD card space
docker image prune -f
```

---

## 9. Getting Help

If you encounter issues during installation or operation:

- **Troubleshooting:** Refer to `docs/TROUBLESHOOTING.md` for error codes (e.g., "I2C Bus Error").
- **API Documentation:** Check `docs/API.md` for endpoint details.
- **Hardware Setup:** Verify wiring in `docs/HARDWARE_SETUP.md`.
- **System Logs:**
    ```bash
    # View real-time application logs
    docker logs -f aquaponics
    
    # View historical logs
    tail -n 100 data/logs/app.log
    ```
- **Status Checks:**
    ```bash
    # Check if container is running
    docker ps
    
    # Check resource usage (CPU/RAM)
    docker stats --no-stream
    ```