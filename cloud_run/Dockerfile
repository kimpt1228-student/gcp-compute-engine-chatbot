# ==============================================================================
# Google Cloud Run Container Image for Gemini Flash Chatbot
# ==============================================================================
FROM python:3.11-slim

# 파이썬 출력 버퍼링 비활성화 및 바이트코드 생성 억제
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8080

WORKDIR /app

# 시스템 필수 패키지 설치 (필요시)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# 종속성 복사 및 사전 설치 (Docker 빌드 캐시 최적화)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스 및 정적 리소스 복사
COPY app.py .
COPY static/ ./static/

# Cloud Run 표준 포트 노출
EXPOSE 8080

# Cloud Run의 동적 $PORT 환경변수를 수신하여 uvicorn 프로세스로 직접 교체 실행 (SIGTERM 정상 처리)
CMD exec uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
