from flask import Flask, jsonify, request, Blueprint, send_file
from datetime import datetime
import csv
import io

api_bp = Blueprint('api', __name__)
sensor_mgr = None  # main.py에서 주입받을 예정

def init_api(mgr):
    """main.py에서 센서 매니저를 받아오는 함수"""
    global sensor_mgr
    sensor_mgr = mgr

@api_bp.route('/health', methods=['GET'])
def health_check():
    """서버 상태 확인"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@api_bp.route('/api/current', methods=['GET'])
def get_current():
    """실시간 센서 데이터 반환"""
    data = sensor_mgr.get_current_readings()
    return jsonify({
        "timestamp": datetime.now().isoformat(),
        "readings": data
    })

@api_bp.route('/api/history', methods=['GET'])
def get_history():
    """DB에서 최근 데이터 조회 (기본 100개)"""
    try:
        limit = int(request.args.get('limit', 100))
        # DB에서 데이터 가져오기
        readings = sensor_mgr.db.get_recent_readings(limit)
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(readings),
            "data": readings
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@api_bp.route('/api/export', methods=['GET'])
def export_data():
    """데이터를 CSV 파일로 다운로드"""
    try:
        limit = int(request.args.get('limit', 1000))
        readings = sensor_mgr.db.get_recent_readings(limit)
        
        # CSV 파일 만들기 (메모리 상에서)
        output = io.StringIO()
        if readings:
            writer = csv.DictWriter(output, fieldnames=readings[0].keys())
            writer.writeheader()
            writer.writerows(readings)
        
        # 파일로 변환하여 전송
        output.seek(0)
        return send_file(
            io.BytesIO(output.getvalue().encode('utf-8-sig')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'sensor_data_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500