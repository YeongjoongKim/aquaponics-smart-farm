from flask import Flask, jsonify, render_template
from flask_cors import CORS
import random
import time
import threading
import os

template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'templates'))
app = Flask(__name__, template_folder=template_dir)
CORS(app)

# [추가됨] 가짜 설정 데이터 (여기에 기준값을 정의합니다)
MOCK_CONFIG = {
    "monitoring": {
        "alert_thresholds": {
            "pH": { "min": 6.8, "max": 7.0, "critical_min": 6.0, "critical_max": 8.0 },
            "EC": { "min": 1200, "max": 1600, "critical_min": 800, "critical_max": 2000 },
            "temperature": { "min": 20, "max": 26, "critical_min": 15, "critical_max": 32 },
            "DO": { "min": 5.0, "critical_min": 3.0 },
            "water_level": { "min": 80, "critical_min": 40 },
            "turbidity": { "max": 50, "critical_max": 100 }
        }
    }
}

# 초기 데이터
simulated_data = {
    "zone_a_filtered": {
        "tank_1": {"ph": 7.0, "turbidity": 30, "water_level": 80, "temperature": 24.0},
        "tank_2": {"ph": 7.1, "turbidity": 25, "water_level": 79, "temperature": 24.1},
        "tank_3": {"ph": 6.9, "turbidity": 35, "water_level": 81, "temperature": 23.9}
    },
    "zone_b_nutrient": {
        "tank_1": {"ph": 6.8, "ec": 1350, "do": 6.5, "temperature": 24.2},
        "tank_2": {"ph": 6.7, "ec": 1340, "do": 6.4, "temperature": 24.3},
        "tank_3": {"ph": 6.8, "ec": 1360, "do": 6.6, "temperature": 24.1}
    },
    "zone_c_cultivation": {
        "start": {"ec": 1350},
        "middle": {"ec": 1300},
        "end": {"ec": 1250}
    },
    "status": "SIMULATION"
}

def update_simulation():
    while True:
        # Zone A 변동 (수위를 40~90 사이로 크게 움직임)
        for t in ["tank_1", "tank_2", "tank_3"]:
            simulated_data["zone_a_filtered"][t]["ph"] = round(random.uniform(6.5, 7.5), 2)
            # 수위: 경고(80미만), 위험(40미만) 테스트를 위해 넓게 변동
            simulated_data["zone_a_filtered"][t]["water_level"] = round(random.uniform(35.0, 95.0), 1)
            simulated_data["zone_a_filtered"][t]["temperature"] = round(random.uniform(18.0, 28.0), 1)
            simulated_data["zone_a_filtered"][t]["turbidity"] = int(random.uniform(20, 110))

        # Zone B 변동
        for t in ["tank_1", "tank_2", "tank_3"]:
            simulated_data["zone_b_nutrient"][t]["ec"] = int(random.uniform(1100, 1700))
            simulated_data["zone_b_nutrient"][t]["do"] = round(random.uniform(4.0, 7.0), 1)

        # Zone C 변동
        base_ec = simulated_data["zone_b_nutrient"]["tank_3"]["ec"]
        simulated_data["zone_c_cultivation"]["start"]["ec"] = base_ec - 10
        simulated_data["zone_c_cultivation"]["middle"]["ec"] = base_ec - 50
        simulated_data["zone_c_cultivation"]["end"]["ec"] = base_ec - 100

        time.sleep(2) # 2초마다 변경

threading.Thread(target=update_simulation, daemon=True).start()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/status', methods=['GET'])
def get_status():
    return jsonify({"status": "healthy"})

# [핵심 추가] 설정값(임계값) 제공 API
@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        "status": "success",
        "data": { "config": MOCK_CONFIG }
    })

@app.route('/api/current', methods=['GET'])
def get_current_readings():
    return jsonify({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "success",
        "data": simulated_data
    })

if __name__ == '__main__':
    print("=== 시뮬레이션 서버 재시작 (http://localhost:5001) ===")
    app.run(host='0.0.0.0', port=5001, debug=True)