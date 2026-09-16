# ==============================================================================
# Google Cloud Run 챗봇 (ADC 모드) PowerShell 배포 스크립트
# ==============================================================================
param(
    [string]$ServiceName = "gemini-chatbot-adc",
    [string]$Region = "us-central1",
    [string]$ProjectId = ""
)

$ErrorActionPreference = "Stop"

if (-not $ProjectId) {
    $ProjectId = (gcloud config get-value project 2>$null).Trim()
}

if (-not $ProjectId) {
    Write-Host "[ERROR] GCP Project ID가 설정되지 않았습니다." -ForegroundColor Red
    Write-Host "gcloud config set project <PROJECT_ID> 를 실행하세요."
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [Google Cloud Run 챗봇 (ADC 모드) 배포 시작]" -ForegroundColor Green
Write-Host " - 서비스명:     $ServiceName"
Write-Host " - 리전(Region): $Region"
Write-Host " - 프로젝트 ID:  $ProjectId"
Write-Host " - 인증 방식:    Application Default Credentials (ADC)"
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. API 활성화
Write-Host "[1/4] 필수 GCP API 활성화 확인 중..." -ForegroundColor Yellow
gcloud services enable run.googleapis.com cloudbuild.googleapis.com aiplatform.googleapis.com artifactregistry.googleapis.com --project $ProjectId

# 2. 서비스 계정 권한 부여
Write-Host "[2/4] Cloud Run 서비스 계정(ADC) 권한 확인 및 설정..." -ForegroundColor Yellow
$projectNumber = (gcloud projects describe $ProjectId --format="value(projectNumber)").Trim()
$computeSa = "$projectNumber-compute@developer.gserviceaccount.com"
Write-Host "  - 서비스 계정 ($computeSa)에 roles/aiplatform.user 권한 부여 중..."
gcloud projects add-iam-policy-binding $ProjectId --member="serviceAccount:$computeSa" --role="roles/aiplatform.user" --quiet | Out-Null

# 3. 배포 실행
Write-Host "[3/4] Cloud Run 컨테이너 빌드 및 배포 실행 중..." -ForegroundColor Yellow
gcloud run deploy $ServiceName `
    --source . `
    --region $Region `
    --project $ProjectId `
    --platform managed `
    --allow-unauthenticated `
    --min-instances 0 `
    --max-instances 5 `
    --memory 512Mi `
    --cpu 1 `
    --timeout 300

# 4. 완료 확인
Write-Host "[4/4] 배포 완료 URL 확인..." -ForegroundColor Yellow
$serviceUrl = (gcloud run services describe $ServiceName --region $Region --project $ProjectId --format="value(status.url)").Trim()

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " [배포 성공! (ADC 모드)]" -ForegroundColor Green
Write-Host " - 서비스 URL:   $serviceUrl"
Write-Host " - 헬스체크:     $serviceUrl/health"
Write-Host " - 상태 확인:    $serviceUrl/api/status"
Write-Host "==========================================================" -ForegroundColor Cyan
