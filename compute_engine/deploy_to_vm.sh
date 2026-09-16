#!/usr/bin/env bash
# ==============================================================================
# GCP Compute Engine 챗봇 원클릭 배포 / 업데이트 스크립트
# 사용법:
#   ./deploy_to_vm.sh [INSTANCE_NAME] [ZONE] [PROJECT_ID]
# 예시:
#   ./deploy_to_vm.sh chatbot-instance us-central1-a iceu-songpa23
# ==============================================================================

set -euo pipefail

INSTANCE_NAME="${1:-chatbot-instance}"
ZONE="${2:-us-central1-a}"
PROJECT_ID="${3:-$(gcloud config get-value project 2>/dev/null || echo '')}"

if [ -z "$PROJECT_ID" ]; then
  echo "[ERROR] GCP Project ID가 지정되지 않았습니다. gcloud config set project <PROJECT_ID> 를 실행하거나 매개변수로 전달하세요."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=========================================================="
echo " [GCP Compute Engine 챗봇 배포 시작]"
echo " - 인스턴스: $INSTANCE_NAME"
echo " - 존(Zone):  $ZONE"
echo " - 프로젝트: $PROJECT_ID"
echo " - 소스 경로: $SCRIPT_DIR"
echo "=========================================================="

# 1. 인스턴스 존재 여부 확인
echo "[1/5] VM 인스턴스 상태 확인 중..."
gcloud compute instances describe "$INSTANCE_NAME" \
  --zone="$ZONE" \
  --project="$PROJECT_ID" \
  --format="value(status)" >/dev/null

# 2. 소스 파일 업로드 (SCP)
echo "[2/5] 챗봇 소스 파일 및 정적 리소스 업로드 중..."
# VM 내 디렉터리 준비
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" \
  --command="sudo mkdir -p /opt/chatbot/compute_engine && sudo chown -R \$USER:\$USER /opt/chatbot"

# compute_engine 하위 파일들을 VM의 /opt/chatbot/compute_engine 으로 전송
gcloud compute scp --recurse \
  "$SCRIPT_DIR/app.py" \
  "$SCRIPT_DIR/requirements.txt" \
  "$SCRIPT_DIR/chatbot.conf" \
  "$SCRIPT_DIR/chatbot.service" \
  "$SCRIPT_DIR/static" \
  "$INSTANCE_NAME:/opt/chatbot/compute_engine/" \
  --zone="$ZONE" \
  --project="$PROJECT_ID"

# 3. VM 내부 Python 가상환경 및 의존성 패키지 설치
echo "[3/5] VM 내 Python 가상환경 및 의존성 설치 중..."
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="
  sudo apt-get update -y >/dev/null 2>&1 || true
  sudo apt-get install -y python3-venv python3-pip >/dev/null 2>&1 || true

  if [ ! -d /opt/chatbot/.venv ]; then
    python3 -m venv /opt/chatbot/.venv
  fi

  /opt/chatbot/.venv/bin/pip install --upgrade pip
  /opt/chatbot/.venv/bin/pip install -r /opt/chatbot/compute_engine/requirements.txt
"

# 4. systemd 서비스 등록 및 재시작
echo "[4/5] systemd 서비스 등록 및 재시작 중..."
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="
  sudo cp /opt/chatbot/compute_engine/chatbot.service /etc/systemd/system/chatbot.service
  sudo systemctl daemon-reload
  sudo systemctl enable chatbot.service
  sudo systemctl restart chatbot.service
"

# 5. 상태 검증
echo "[5/5] 서비스 구동 상태 확인..."
gcloud compute ssh "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --command="
  sudo systemctl is-active chatbot.service
"

EXTERNAL_IP=$(gcloud compute instances describe "$INSTANCE_NAME" --zone="$ZONE" --project="$PROJECT_ID" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")

echo "=========================================================="
echo " [배포 완료!]"
echo " - 외부 IP: http://${EXTERNAL_IP}:8000"
echo " - 상태 확인 URL: http://${EXTERNAL_IP}:8000/api/status"
echo " - (HTTPS 설정된 경우): https://${EXTERNAL_IP}.sslip.io"
echo "=========================================================="
