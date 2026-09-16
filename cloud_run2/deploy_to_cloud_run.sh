#!/usr/bin/env bash
# ==============================================================================
# Google Cloud Run 챗봇 (ADC 모드) 원클릭 빌드 & 배포 스크립트
# 특징:
#   - API 키나 Secret Manager 관리 불필요
#   - Application Default Credentials (ADC) 기반 서비스 계정 자동 인증
# 사용법:
#   ./deploy_to_cloud_run.sh [SERVICE_NAME] [REGION] [PROJECT_ID]
# 예시:
#   ./deploy_to_cloud_run.sh gemini-chatbot-adc us-central1 iceu-songpa23
# ==============================================================================

set -euo pipefail

SERVICE_NAME="${1:-gemini-chatbot-adc}"
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
echo " [Google Cloud Run 챗봇 (ADC 모드) 배포 시작]"
echo " - 서비스명:     $SERVICE_NAME"
echo " - 리전(Region): $REGION"
echo " - 프로젝트 ID:  $PROJECT_ID"
echo " - 인증 방식:    Application Default Credentials (ADC)"
echo " - 소스 경로:    $SCRIPT_DIR"
echo "=========================================================="

# 1. 필수 GCP API 활성화 확인
echo "[1/4] 필수 GCP API 활성화 상태 확인..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  --project="$PROJECT_ID"

# 2. 프로젝트 번호 및 기본 서비스 계정에 Vertex AI 권한 부여
echo "[2/4] Cloud Run 서비스 계정(ADC) 권한 확인 및 설정..."
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "  - 서비스 계정 (${COMPUTE_SA})에 Vertex AI 사용자 권한(roles/aiplatform.user) 부여 중..."
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:${COMPUTE_SA}" \
  --role="roles/aiplatform.user" \
  --quiet >/dev/null 2>&1 || true

# 3. Cloud Run 배포 (API 키 / 시크릿 플래그 없이 순수 ADC로 배포)
echo "[3/4] Cloud Run 컨테이너 빌드 및 배포 실행 중..."
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
  --timeout=300

# 4. 배포 완료 URL 확인
echo "[4/4] 배포 완료 URL 확인..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --project="$PROJECT_ID" --format="value(status.url)")

echo "=========================================================="
echo " [배포 성공! (ADC 모드)]"
echo " - 서비스 URL:   ${SERVICE_URL}"
echo " - 상태 확인:    ${SERVICE_URL}/health"
echo " - API 상태:     ${SERVICE_URL}/api/status"
echo " - 인증 방식:    Application Default Credentials (No Secret Key)"
echo "=========================================================="
