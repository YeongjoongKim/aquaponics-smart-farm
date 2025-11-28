from flask import Flask, jsonify
from flask_cors import CORS
import random
import time
import threading

app = Flask(__name__)
CORS(app)  # 다른 포트에서의 접근 허용 (보안 이슈 방지)

# 시뮬레이션용 초기 데이터 설정
simulated_data = {
    "pH": 7.0,
    "EC": 1340,
    "temperature": 21.7,
    "DO": 7.7,
    "water_level": 78,
    "turbidity": 30,
    "status": "SIMULATION"
}

def update_simulation():
    """센서 값을 조금씩 변화시켜서 시뮬레이션 효과를 주는 함수"""
    while True:
        # 1. pH: 6.5 ~ 7.5 사이에서 랜덤 변화
        simulated_data["pH"] += random.uniform(-0.1, 0.1)
        simulated_data["pH"] = max(5.0, min(9.0, simulated_data["pH"])) 
        
        # 2. EC: 10씩 변동
        simulated_data["EC"] += random.uniform(-10, 10)
        
        # 3. 수온: 조금씩 변동
        simulated_data["temperature"] += random.uniform(-0.2, 0.2)
        
        # 4. DO(용존산소량): 변동
        simulated_data["DO"] += random.uniform(-0.1, 0.1)
        
        # 5. 수위: 물을 쓴다고 가정하고 조금씩 줄어들다가, 너무 낮으면 다시 채움
        simulated_data["water_level"] -= 0.5
        if simulated_data["water_level"] < 40:
            simulated_data["water_level"] = 100
            
        # 6. 탁도: 랜덤 변동
        simulated_data["turbidity"] = max(0, simulated_data["turbidity"] + random.uniform(-2, 2))

        time.sleep(1)  # 1초마다 데이터 변경

# 백그라운드에서 가짜 데이터 생성 시작
threading.Thread(target=update_simulation, daemon=True).start()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "healthy", "mode": "simulation"})

@app.route('/api/current', methods=['GET'])
def get_current_readings():
    """대시보드가 요청하면 현재 가짜 데이터를 보내주는 API"""
    # docs/API.md 문서 형식을 따름
    response = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "readings": {
            "pH": round(simulated_data["pH"], 2),
            "EC": round(simulated_data["EC"], 1),
            "temperature": round(simulated_data["temperature"], 1),
            "DO": round(simulated_data["DO"], 2),
            "water_level": int(simulated_data["water_level"]),
            "turbidity": int(simulated_data["turbidity"]),
            "status": "OK"
        }
    }
    return jsonify(response)

if __name__ == '__main__':
    print("=== 아쿠아포닉스 시뮬레이션 서버 시작 ===")
    print("주소: http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)