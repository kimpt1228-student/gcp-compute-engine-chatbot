# Gemini Flash Cloud Run 챗봇 (ADC 모드)

Google Cloud의 **Application Default Credentials (ADC)** 방식을 적용한 Gemini Flash 챗봇 서비스입니다.

수동 API 키(GEMINI_API_KEY) 발급이나 Secret Manager 관리 없이, 환경의 서비스 계정(IAM Identity)을 자동으로 활용하여 엔터프라이즈급 보안을 제공합니다.

---

## 1. ADC (Application Default Credentials) 방식이란?

Google AI Studio 및 Google Cloud에서 권장하는 **표준 보안 인증 방식**입니다.

- **기존 방식 (`cloud_run/`)**:
  - `GEMINI_API_KEY`를 환경변수로 직접 주입하거나 Secret Manager에서 API 키 문자열을 읽어옴.
  - 키 유출 위험 및 주기적인 키 교체(Rotation) 관리 부담이 존재함.
- **ADC 방식 (`cloud_run2/`)**:
  - API 키를 전혀 사용하지 않음.
  - **Cloud Run 환경**: 컨테이너가 배포된 인스턴스의 서비스 계정(예: `...-compute@developer.gserviceaccount.com`)을 통해 GCP 내부 메타데이터 서버에서 자동으로 단기 액세스 토큰(OAuth2 Bearer Token)을 발급받아 Model API(`aiplatform.googleapis.com`)와 통신.
  - **로컬 개발 환경**: `gcloud auth application-default login` 명령어를 통해 개발자 본인의 GCP 계정 자격 증명으로 즉시 통신.

---

## 2. 기존 방식 vs ADC 방식 비교

| 비교 항목 | 기존 방식 (`cloud_run/`) | **ADC 방식 (`cloud_run2/`)** |
| :--- | :--- | :--- |
| **인증 수단** | `GEMINI_API_KEY` 문자열 | **서비스 계정 IAM 토큰 (자동 발급 & 갱신)** |
| **키 관리 필요성** | Secret Manager 또는 환경변수 필요 | **완전 불필요 (No Secret Key)** |
| **키 유출 위험** | 코드/환경변수 노출 시 위험 | **토큰이 일시적(1시간)이므로 유출 위험 없음** |
| **GCP 권한 제어** | API 키 단위 제어 | **IAM 역할 (`roles/aiplatform.user`) 단위 정밀 제어** |
| **배포 명령어** | `--set-secrets=GEMINI_API_KEY=...` 필요 | **별도 시크릿 플래그 없이 바로 배포** |
| **API 엔드포인트** | `generativelanguage.googleapis.com` | `aiplatform.googleapis.com` (Model API / Vertex AI) |

---

## 3. 사전 요구사항 (GCP 설정)

### ① 필수 API 활성화
```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  --project="YOUR_PROJECT_ID"
```

### ② Cloud Run 서비스 계정에 Vertex AI 권한 부여
Cloud Run이 실행될 기본 Compute Engine 서비스 계정에 `roles/aiplatform.user` 권한을 부여합니다:
```bash
PROJECT_NUMBER=$(gcloud projects describe YOUR_PROJECT_ID --format="value(projectNumber)")

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/aiplatform.user"
```

---

## 4. 로컬 환경에서 실행하기

로컬 PC에서 테스트할 때는 구글 권장 스크립트 또는 gcloud 명령어로 로컬 ADC 자격 증명을 1회 등록합니다.

```bash
# 방법 1: Google 공식 원클릭 스크립트 실행
bash <(curl -sSL https://storage.googleapis.com/cloud-samples-data/adc/setup_adc.sh)

# 방법 2: gcloud 명령어로 직접 로그인
gcloud auth application-default login
gcloud auth application-default set-quota-project YOUR_PROJECT_ID
```

로컬 서버 실행:
```bash
# 종속성 설치
pip install -r requirements.txt

# 서버 실행
python app.py
# 또는 Windows: run.bat 더블 클릭
```
브라우저에서 `http://localhost:8080` 접속.

---

## 5. Cloud Run 원클릭 배포

### Bash (Linux / macOS / Git Bash)
```bash
chmod +x deploy_to_cloud_run.sh
./deploy_to_cloud_run.sh gemini-chatbot-adc us-central1 YOUR_PROJECT_ID
```

### PowerShell (Windows)
```powershell
.\deploy_to_cloud_run.ps1 -ServiceName "gemini-chatbot-adc" -Region "us-central1" -ProjectId "YOUR_PROJECT_ID"
```

---

## 6. 주요 API 엔드포인트

- `GET /` : 챗봇 웹 UI 메인 화면
- `GET /health` : 서버 헬스체크 및 ADC 인증 상태 확인
- `GET /api/status` : ADC 자격 증명 정보, 연결된 서비스 계정, 지원 모델 목록
- `POST /api/chat/stream` : 실시간 SSE(Server-Sent Events) 스트리밍 대화 API
- `GET /favicon.ico` : 204 No Content 반환 (Cloud Run 404 WARNING 방지)
