#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run 챗봇 원클릭 빌드 & 배포 스크립트
# 사용법:
#   ./deploy_to_cloud_run.sh [SERVICE_NAME] [REGION] [PROJECT_ID]
# 예시:
#   ./deploy_to_cloud_run.sh gemini-chatbot-cloudrun us-central1 iceu-songpa23
# ==============================================================================

set -euo pipefail

SERVICE_NAME="${1:-gemini-chatbot-cloudrun}"
REGION="${2:-us-central1}"
PROJECT_ID="${3:-$(gcloud config get-value project 2>/dev/null || echo '')}"

if [ -z "$PROJECT_ID" ]; then
  echo "[ERROR] GCP Project ID가 설정되지 않았습니다."
  echo "gcloud config set project <PROJECT_ID> 를 실행하거나 스크립트 인자로 전달하세요."
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo " [Google Cloud Run 챗봇 배포 시작]"
echo " - 서비스명:   $SERVICE_NAME"
echo " - 리전(Region): $REGION"
echo " - 프로젝트 ID: $PROJECT_ID"
echo " - 소스 경로:   $SCRIPT_DIR"
echo "=========================================================="

# 1. 필수 GCP API 활성화 확인
echo "[1/4] 필수 GCP API 활성화 상태 확인..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  --project="$PROJECT_ID"

# 2. 프로젝트 번호 및 기본 서비스 계정 확인
echo "[2/4] Cloud Run 서비스 계정 및 Secret Manager 권한 확인..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Secret Manager 접근 권한 부여 (필요 시)
if gcloud secrets describe GEMINI_API_KEY --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "  - Secret Manager(GEMINI_API_KEY) 권한 확인 및 부여 중..."
  gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
    --project="$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet || true
else
  echo "[WARN] Secret Manager에 GEMINI_API_KEY가 없습니다. 배포 전 시크릿을 생성하거나 환경변수로 전달하세요."
fi

# 3. Cloud Run 배포 (Cloud Build를 통한 소스 기반 자동 빌드 및 배포)
echo "[3/4] Cloud Run 컨테이너 빌드 및 배포 실행 중..."
SECRET_FLAG=""
if gcloud secrets describe GEMINI_API_KEY --project="$PROJECT_ID" >/dev/null 2>&1; then
  SECRET_FLAG="--set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest"
fi

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --platform=managed \
  --allow-unauthenticated \
  --min-instances=0 \
  --max-instances=5 \
  --memory=512Mi \
  --cpu=1 \
  --timeout=300 \
  $SECRET_FLAG

# 4. 배포 완료 URL 확인
echo "[4/4] 배포 완료 URL 확인..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)")

echo "=========================================================="
echo " [배포 성공!]"
echo " - 서비스 URL:   ${SERVICE_URL}"
echo " - 상태 확인:    ${SERVICE_URL}/health"
echo " - API 상태:     ${SERVICE_URL}/api/status"
echo " - 자동 HTTPS:   Google 관리형 SSL 적용 완료"
echo "=========================================================="
