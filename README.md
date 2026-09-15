# 🤖 GCP Compute Engine 기반 Gemini Flash 챗봇

Google Cloud Platform(GCP)의 **Compute Engine (VM)** 환경에 FastAPI 기반의 차세대 **Gemini Flash 챗봇**을 배포하고, **Secret Manager**를 통한 보안 키 관리와 **Let's Encrypt 공인 SSL(HTTPS)**을 적용한 프로덕션 수준의 웹 서비스 프로젝트입니다.

---

## 🌟 주요 특징

- ⚡ **최신 Gemini 모델 탑재**: `Gemini 3.8 Flash`(기본) 및 `Gemini 3.7 Flash` 모델 지원
- 🔒 **안전한 API 키 관리**: 로컬 파일이나 환경변수에 노출하지 않고 **GCP Secret Manager**에서 서비스 계정(IAM)을 통해 런타임에 직접 안전하게 호출
- 🌐 **공인 SSL(HTTPS) 완벽 지원**: 도메인 구매 없이 `sslip.io`와 Let's Encrypt(Certbot)를 연동하여 브라우저 경고 없는 **녹색 자물쇠(HTTPS)** 보안 연결 구축
- 🚀 **실시간 스트리밍 대화**: Server-Sent Events(SSE) 방식으로 한 글자씩 실시간 타이핑되는 자연스러운 스트리밍 응답 제공
- 🔎 **Google Search Grounding**: 최신 정보 및 뉴스 실시간 웹 검색 연동
- 🛡️ **상시 무중단 구동**: Linux `systemd` 데몬 및 Nginx 리버스 프록시 연동으로 인스턴스 재부팅 시에도 자동 복구

---

## 📁 프로젝트 파일 구조

```plaintext
chat_bot/
├── deployment.log                     # 전체 배포 및 HTTPS 설정 실시간 작업 로그
└── gcp-compute-engine-chatbot/
    ├── app.py                         # FastAPI 백엔드 메인 서버 (Secret Manager & Gemini API)
    ├── chatbot.conf                   # Nginx 리버스 프록시 및 HTTPS/SSE 설정 파일
    ├── compute_engine_example.ipynb   # Compute Engine 생성 및 리전별 비용 분석 실습 노트북
    ├── deployment.log                 # 작업 과정 상세 기록 로그 파일
    ├── HOW_https.html                 # [가이드] HTTPS 동작 원리 및 구축 방법 시각화 웹 문서
    ├── requirements.txt               # 파이썬 필수 패키지 목록
    ├── run.bat                        # 로컬 윈도우 환경 실행용 배치 파일
    ├── startup-script.sh              # VM 인스턴스 최초 부팅 시 자동 설치 스크립트
    └── static/                        # 웹 UI 정적 리소스
        ├── index.html                 # 챗봇 웹 인터페이스 화면
        ├── style.css                  # 모던 다크/라이트 테마 CSS 스타일
        └── app.js                     # 클라이언트 대화 처리 및 SSE 스트리밍 JS 로직
```

---

## 🧩 핵심 파일 상세 설명

### 1. `app.py` (백엔드 서버)
- **FastAPI**로 구축된 경량 고성능 웹 서버입니다.
- **Secret Manager 자동 연동 (`get_gemini_api_key`)**:
  - 시스템 환경변수에 `GEMINI_API_KEY`가 없더라도, 인스턴스의 서비스 계정 권한을 활용하여 `projects/695113814332/secrets/GEMINI_API_KEY`에서 자동으로 키를 불러옵니다.
- **주요 엔드포인트**:
  - `GET /`: 정적 웹 UI 렌더링
  - `GET /api/status`: 챗봇 준비 상태, 모델 목록, 마스킹된 API 키 상태 반환
  - `POST /api/chat/stream`: Gemini API와의 SSE(Server-Sent Events) 실시간 대화 스트리밍 처리

### 2. `chatbot.conf` (Nginx 리버스 프록시 설정)
- 외부(사용자)의 HTTPS 요청을 받아 내부의 FastAPI(`127.0.0.1:8000`)로 안전하게 전달합니다.
- 포트 80(HTTP)으로 들어오는 모든 요청을 포트 443(HTTPS)으로 301 영구 리다이렉트합니다.
- `proxy_buffering off;` 옵션으로 실시간 스트리밍 답변이 중간에 멈추거나 지연되지 않도록 최적화되어 있습니다.

### 3. `startup-script.sh` (초기화 스크립트)
- Compute Engine 인스턴스가 생성될 때 OS 초기화 과정에서 `python3`, `python3-pip`, `python3-venv`, `git`, `curl`을 자동으로 설치합니다.

### 4. `HOW_https.html` (HTTPS 시각화 가이드)
- 왜 HTTP 접속 시 "주의 요함" 경고가 발생하며, 이를 어떻게 공인 무료 도메인(`sslip.io`)과 Let's Encrypt를 통해 해결했는지 다이어그램과 쉬운 설명으로 풀어낸 대화형 웹 문서입니다. 브라우저로 열어서 바로 확인할 수 있습니다.

---

## 🏗️ 서비스 아키텍처

```
[ 사용자 웹 브라우저 ]
        │  HTTPS (포트 443) 보안 통신
        ▼
[ GCP VPC 방화벽 (allow-chatbot-8000) ]
        │
        ▼
[ Nginx 1.22.1 리버스 프록시 ]
   - Let's Encrypt SSL 인증서 검증 및 복호화
   - HTTP -> HTTPS 자동 리다이렉트
   - SSE 스트리밍 버퍼링 해제
        │
        ▼  내부 로컬 통신 (127.0.0.1:8000)
[ FastAPI 챗봇 백엔드 (chatbot.service) ]
        │
        ├─▶ [ GCP Secret Manager ] : GEMINI_API_KEY 조회 (IAM 인증)
        └─▶ [ Google Generative Language API ] : 실시간 대화 추론
```

---

## 🚀 빠른 시작 및 배포 방법

### 1. 로컬 환경에서 실행
```bash
# 의존성 패키지 설치
pip install -r requirements.txt

# 실행 (GEMINI_API_KEY 환경변수 설정 후)
python app.py
# 또는 run.bat 더블클릭
```

### 2. GCP Compute Engine 배포 단계 요약

1. **Secret Manager 접근 권한 부여**:
   ```bash
   gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
     --project=iceu-songpa23 \
     --member="serviceAccount:695113814332-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

2. **Compute Engine 인스턴스 생성**:
   ```bash
   gcloud compute instances create chatbot-instance \
     --project=iceu-songpa23 \
     --zone=us-central1-a \
     --machine-type=e2-medium \
     --tags=chatbot-server,http-server \
     --scopes=https://www.googleapis.com/auth/cloud-platform
   ```

3. **VPC 방화벽 포트 오픈 (8000, 80, 443)**:
   ```bash
   gcloud compute firewall-rules create allow-chatbot-8000 \
     --allow="tcp:8000,tcp:80,tcp:443" \
     --target-tags=chatbot-server
   ```

4. **소스 배포 및 systemd 서비스 등록**:
   - VM에 소스 코드 전송 후 Python 가상환경 생성
   - `/etc/systemd/system/chatbot.service` 등록 후 `systemctl enable --now chatbot`

5. **Let's Encrypt 공인 SSL 적용 (HTTPS 구축)**:
   ```bash
   sudo apt-get install -y nginx certbot python3-certbot-nginx
   sudo certbot --nginx -d <외부IP>.sslip.io --non-interactive --agree-tos -m <이메일> --redirect
   ```

---

## 🛠️ 인스턴스 유지보수 명령어

- **인스턴스 SSH 원격 접속**:
  ```bash
  gcloud compute ssh chatbot-instance --zone=us-central1-a --project=iceu-songpa23
  ```
- **챗봇 서비스 상태 확인**:
  ```bash
  sudo systemctl status chatbot.service
  ```
- **챗봇 실시간 로그 확인**:
  ```bash
  sudo journalctl -u chatbot.service -f
  ```
- **Nginx 서비스 재시작**:
  ```bash
  sudo systemctl restart nginx
  ```
- **실습 종료 후 리소스 삭제 (과금 방지)**:
  ```bash
  gcloud compute instances delete chatbot-instance --zone=us-central1-a --project=iceu-songpa23 --quiet
  ```
