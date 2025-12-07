# Base Image: Python 3.9 Slim (Lightweight Debian based)
# Raspberry Pi 호환성을 위해 slim-bullseye 또는 최신 slim 버전을 사용합니다.
FROM python:3.9-slim

# 작업 디렉토리 설정
WORKDIR /app

# [환경 변수 설정]
# 1. PYTHONUNBUFFERED=1: Docker 로그에서 Python 출력을 즉시 확인 (버퍼링 방지)
# 2. PYTHONDONTWRITEBYTECODE=1: .pyc 파일 생성 방지 (컨테이너 크기 최소화)
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# [시스템 패키지 설치]
# 시리얼 통신 및 시간대 설정을 위한 필수 패키지 설치
# - gcc: 일부 Python 패키지 빌드용
# - tzdata: 시간대 설정용 (/etc/localtime 동기화)
# - curl: 헬스 체크(Healthcheck)용
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    tzdata \
    curl \
    && rm -rf /var/lib/apt/lists/*

# [의존성 설치]
# requirements.txt를 먼저 복사하여 캐시 효율성을 높입니다.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# [애플리케이션 코드 복사]
# raspberry_pi/app 폴더의 모든 내용을 컨테이너의 /app/app 으로 복사합니다.
# 주의: docker-compose에서 bind mount를 사용하는 경우 이 단계는 덮어씌워질 수 있으나,
# 프로덕션 빌드를 위해 포함하는 것이 좋습니다.
COPY app/ ./app/

# [디렉토리 생성]
# 데이터 저장을 위한 폴더 구조를 미리 생성합니다.
# (호스트 볼륨이 마운트되면 덮어씌워지지만, 권한 문제를 위해 생성해둡니다)
RUN mkdir -p /app/data/logs /app/data/backups

# [포트 노출]
# Flask 기본 포트 5000
EXPOSE 5000

# [실행 명령]
# main.py가 스케줄러(데이터 수집)와 웹 서버(Flask)를 모두 포함하고 있으므로,
# Python 모듈로 직접 실행하는 것이 가장 안정적입니다.
CMD ["python", "-m", "app.main"]