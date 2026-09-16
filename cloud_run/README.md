# ☁️ Google Cloud Run 기반 Gemini Flash 챗봇

Google Cloud Platform(GCP)의 완전 관리형 서버리스 컨테이너 서비스인 **Cloud Run**에 FastAPI 기반의 **Gemini Flash 챗봇**을 배포하는 프로젝트입니다.

---

## 🌟 Cloud Run 배포의 주요 장점

1. **자동 HTTPS 및 커스텀 도메인**: 복잡한 Nginx 설정이나 Let's Encrypt 갱신 없이 Google 관리형 SSL 인증서가 기본 적용되어 즉시 보안 접속(`https://...run.app`)이 가능합니다.
2. **Scale to Zero (비용 0원 최적화)**: 대화 요청이 없을 때는 인스턴스가 0으로 자동 축소되어 유휴 비용이 발생하지 않습니다.
3. **간편한 Secret Manager 연동**: Cloud Run의 `--set-secrets` 플래그로 코드 수정 없이 안전하게 `GEMINI_API_KEY`를 환경변수로 마운트합니다.
4. **SSE 실시간 스트리밍 지원**: HTTP/2 기반으로 Gemini의 빠른 스트리밍 답변을 끊김 없이 전송합니다.
5. **무중단 배포 및 롤백**: 트래픽 분할, 리비전 관리, 자동 롤백 기능을 기본 제공합니다.

---

## 📁 디렉터리 구성

```plaintext
cloud_run/
├── app.py                   # Cloud Run 규격 FastAPI 메인 서버 (PORT 8080 및 /health 헬스체크)
├── Dockerfile               # Python 3.11-slim 기반 경량 프로덕션 컨테이너 이미지 정의
├── .dockerignore            # 불필요한 파일 빌드 제외 설정
├── requirements.txt         # 파이썬 의존성 패키지 목록
├── deploy_to_cloud_run.sh   # 원클릭 Cloud Run 배포 스크립트
├── run.bat                  # 로컬 환경 Cloud Run 시뮬레이션 실행 배치 파일 (포트 8080)
├── README.md                # Cloud Run 배포 안내 문서
└── static/                  # 웹 UI 정적 리소스 (index.html, style.css, app.js)
```

---

## 🚀 빠른 시작 및 배포 방법

### 1. 로컬 환경에서 테스트
```bash
cd cloud_run

# 패키지 설치
pip install -r requirements.txt

# GEMINI_API_KEY 설정 및 실행 (포트 8080)
python app.py
# 또는 run.bat 더블클릭
```
브라우저에서 `http://localhost:8080` 접속

---

### 2. Docker 로컬 빌드 및 실행 테스트
```bash
cd cloud_run

# 도커 이미지 빌드
docker build -t gemini-chatbot-run .

# 컨테이너 실행 (로컬 환경변수 GEMINI_API_KEY 전달)
docker run -p 8080:8080 -e GEMINI_API_KEY="your-gemini-api-key" gemini-chatbot-run
```

---

### 3. Google Cloud Run으로 배포

#### 방법 A: 자동 배포 스크립트 실행 (권장)
```bash
chmod +x deploy_to_cloud_run.sh
./deploy_to_cloud_run.sh gemini-chatbot-run us-central1 <YOUR_PROJECT_ID>
```

#### 방법 B: gcloud CLI 직접 실행
```bash
cd cloud_run

gcloud run deploy gemini-chatbot-run \
  --source . \
  --region us-central1 \
  --project <YOUR_PROJECT_ID> \
  --platform managed \
  --allow-unauthenticated \
  --set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --min-instances 0 \
  --max-instances 5 \
  --memory 512Mi \
  --cpu 1 \
  --timeout 300
```

---

## 🔍 상태 확인 및 모니터링
- **헬스체크 엔드포인트**: `https://<SERVICE_URL>/health`
- **상태 및 모델 정보**: `https://<SERVICE_URL>/api/status`
- **Cloud Run 로그 확인**:
  ```bash
  gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gemini-chatbot-run" --limit 20
  ```
