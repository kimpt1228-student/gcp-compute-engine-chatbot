# 🤖 GCP 기반 Gemini Flash 챗봇 (Compute Engine & Cloud Run)

Google Cloud Platform(GCP)의 **Compute Engine (VM)** 및 **Cloud Run (서버리스 컨테이너)** 환경에 FastAPI 기반의 차세대 **Gemini Flash 챗봇**을 배포하고, **Secret Manager**를 통한 보안 키 관리와 공인 SSL(HTTPS)을 적용한 프로덕션 수준의 웹 서비스 프로젝트입니다.

---

## 🌟 주요 특징

- ⚡ **최신 Gemini 모델 탑재**: `Gemini 3.8 Flash`(기본) 및 `Gemini 3.7 Flash` 모델 지원
- ☁️ **멀티 플랫폼 배포 지원**:
  - **Compute Engine (`compute_engine/`)**: Nginx 리버스 프록시 + Let's Encrypt SSL + systemd 상시 구동
  - **Cloud Run (`cloud_run/`)**: 도커 컨테이너 기반 서버리스 배포, Scale to Zero, Google 관리형 SSL 자동 적용
- 🔒 **안전한 API 키 관리**: 로컬 파일이나 환경변수에 노출하지 않고 **GCP Secret Manager**에서 서비스 계정(IAM)을 통해 런타임에 직접 안전하게 호출
- 🚀 **실시간 스트리밍 대화**: Server-Sent Events(SSE) 방식으로 한 글자씩 실시간 타이핑되는 자연스러운 스트리밍 응답 제공
- 🔎 **Google Search Grounding**: 최신 정보 및 뉴스 실시간 웹 검색 연동

---

## 📁 프로젝트 파일 구조

```plaintext
chat_bot/
└── gcp-compute-engine-chatbot/
    ├── compute_engine_example.ipynb   # Compute Engine 생성 및 리전별 비용 분석 실습 노트북
    ├── deployment.log                 # 배포 작업 기록 로그 파일
    ├── run.bat                        # 루트 실행용 배치 파일 (compute_engine/app.py 연동)
    ├── README.md                      # 프로젝트 설명 및 배포 가이드 문서
    │
    ├── compute_engine/                # [VM 배포] Compute Engine 배포용 소스 & 인프라
    │   ├── app.py                     # FastAPI 백엔드 메인 서버 (포트 8000)
    │   ├── requirements.txt           # 파이썬 필수 패키지 목록
    │   ├── chatbot.conf               # Nginx 리버스 프록시 및 HTTPS/SSE 설정 파일
    │   ├── chatbot.service            # GCP VM systemd 데몬 등록 템플릿
    │   ├── startup-script.sh          # VM 인스턴스 최초 부팅 시 자동 설치 스크립트
    │   ├── deploy_to_vm.sh            # GCP VM 원클릭 SCP 배포 스크립트
    │   ├── run.bat                    # 로컬 실행 배치 파일
    │   └── static/                    # 웹 UI 정적 리소스 (HTML/CSS/JS)
    │
    └── cloud_run/                     # [서버리스 컨테이너] Cloud Run 배포용 소스 & Docker
        ├── app.py                     # Cloud Run 규격 FastAPI 메인 서버 (PORT 8080 대응)
        ├── Dockerfile                 # Python 3.11-slim 경량 프로덕션 이미지
        ├── .dockerignore              # 빌드 제외 파일 목록
        ├── requirements.txt           # 파이썬 의존성 패키지 목록
        ├── deploy_to_cloud_run.sh     # Cloud Run 원클릭 소스 배포 스크립트
        ├── run.bat                    # 로컬 Cloud Run 시뮬레이션 배치 파일 (포트 8080)
        ├── README.md                  # Cloud Run 상세 배포 가이드
        └── static/                    # 웹 UI 정적 리소스 (HTML/CSS/JS)
```

---

## 🧩 핵심 파일 상세 설명

### 1. `compute_engine/app.py` (백엔드 서버)
- **FastAPI**로 구축된 경량 고성능 웹 서버입니다.
- **Secret Manager 자동 연동 (`get_gemini_api_key`)**:
  - 시스템 환경변수에 `GEMINI_API_KEY`가 없더라도, 인스턴스의 서비스 계정 권한을 활용하여 `projects/<YOUR_PROJECT_ID>/secrets/GEMINI_API_KEY`에서 자동으로 키를 불러옵니다. (프로젝트 ID 미지정 시 기본 자격증명에서 자동 탐색)
- **주요 엔드포인트**:
  - `GET /`: 정적 웹 UI 렌더링 (`compute_engine/static/index.html` 자동 연동)
  - `GET /api/status`: 챗봇 준비 상태, 모델 목록, 마스킹된 API 키 상태 반환
  - `POST /api/chat/stream`: Gemini API와의 SSE(Server-Sent Events) 실시간 대화 스트리밍 처리

### 2. `compute_engine/chatbot.conf` (Nginx 리버스 프록시 설정)
- 외부(사용자)의 HTTPS 요청을 받아 내부의 FastAPI(`127.0.0.1:8000`)로 안전하게 전달합니다.
- 포트 80(HTTP)으로 들어오는 모든 요청을 포트 443(HTTPS)으로 301 영구 리다이렉트합니다.
- `proxy_buffering off;` 옵션으로 실시간 스트리밍 답변이 중간에 멈추거나 지연되지 않도록 최적화되어 있습니다.

### 3. `compute_engine/chatbot.service` (systemd 데몬 설정)
- GCP Linux VM에서 백엔드 앱을 상시 무중단으로 구동하기 위한 서비스 파일입니다.
- `WorkingDirectory=/opt/chatbot/compute_engine` 지정 및 인스턴스 재부팅 시 자동 기동을 지원합니다.

### 4. `compute_engine/startup-script.sh` (초기화 스크립트)
- Compute Engine 인스턴스가 생성될 때 OS 초기화 과정에서 `python3`, `python3-pip`, `python3-venv`, `git`, `curl` 및 기본 폴더(`/opt/chatbot/compute_engine`)를 자동으로 구성합니다.

### 5. `compute_engine/deploy_to_vm.sh` (원클릭 배포 자동화)
- 로컬 또는 Cloud Shell에서 `./compute_engine/deploy_to_vm.sh [인스턴스명] [존] [프로젝트ID]` 한 줄로 소스 SCP 전송, 가상환경 패키지 설치, systemd 재시작까지 자동으로 수행합니다.

---

## 🔐 HTTP에서 HTTPS로의 전환: 왜 필요했고 어떻게 구현했는가?

프로젝트 초기에는 FastAPI 내장 서버를 외부 IP의 포트 `8000`에 직접 노출하는 **HTTP** 방식으로 배포하였습니다. 그러나 프로덕션 수준의 안정성과 보안을 확보하기 위해 **HTTPS** 환경으로 전면 마이그레이션하였습니다.

### 1. 전환 배경 (왜 HTTP로는 부족했는가?)
* **브라우저의 강력한 경고 ("주의 요함 / Not Secure")**: 도메인이나 IP로 HTTP 접속 시 브라우저 주소창에 빨간색 경고나 경고 아이콘이 노출되어 사용자의 불안감을 유발합니다.
* **대화 데이터 도청 및 변조 위험 (중간자 공격, MITM)**: 사용자가 챗봇에 입력하는 질문(개인정보, 업무 질의 등)과 Gemini 모델의 응답이 평문(Plaintext)으로 오고 가기 때문에 공용 Wi-Fi나 통신망 중간에서 패킷 스니핑(도청) 및 조작이 가능합니다.
* **최신 웹 API 제약**: 최신 브라우저 기능(Clipboard API, Service Worker 등)은 보안 컨텍스트(HTTPS)에서만 정상 동작합니다.

---

### 2. HTTP vs HTTPS 핵심 프로토콜 차이

| 비교 항목 | HTTP (HyperText Transfer Protocol) | HTTPS (HTTP Secure / TLS) |
| :--- | :--- | :--- |
| **기본 포트** | `80` (또는 커스텀 `8000`) | `443` |
| **데이터 전송 상태** | **평문 (Plaintext)** 전송 | **대칭키 암호화 (AES/ChaCha20 등)** 전송 |
| **보안 메커니즘** | 없음 (암호화 계층 부재) | **TLS/SSL 핸드셰이크** (비대칭키 교환 + 대칭키 통신) |
| **신원 검증 (인증)** | 서버가 진짜인지 증명 불가 (피싱 위험) | 공인 CA(인증기관)의 전자서명 인증서로 서버 신원 보증 |
| **데이터 무결성** | 전송 중 패킷이 위·변조되어도 감지 불가 | MAC(메시지 인증 코드) 해시 검증으로 변조 시 즉시 차단 |
| **브라우저 표시** | ⚠️ `주의 요함` (연결이 안전하지 않음) | 🔒 `안전한 연결` (녹색 자물쇠) |
| **성능 및 프로토콜** | HTTP/1.1 중심 | HTTP/2, HTTP/3 (ALPN 협상 기반 멀티플렉싱 고속화 지원) |

---

### 3. HTTPS 구축을 위해 적용된 핵심 기술 및 구현 방식

외부 상용 도메인 구매 비용 없이 완전한 공인 인증서를 발급받아 적용하기 위해 다음의 4가지 기술을 결합하여 구현했습니다:

```
[ 사용자 브라우저 ]
       │
       ▼ (1) 도메인 질의 : <YOUR_EXTERNAL_IP>.sslip.io ──▶ IP 자동 반환 (sslip.io DNS 매직)
       │
       ▼ (2) HTTPS 접속 (포트 443, TLS 암호화 터널)
[ GCP VPC 방화벽 : 443, 80 포트 인바운드 허용 ]
       │
       ▼
[ Nginx 리버스 프록시 (SSL Termination) ]
   ├── Let's Encrypt 공인 SSL 인증서 (Certbot이 90일 주기 자동 갱신)
   ├── 80번 포트(HTTP) 접속 시 443번(HTTPS)으로 301 영구 리다이렉트
   └── SSE 스트리밍 버퍼링 해제 (proxy_buffering off)
       │
       ▼ (3) 로컬 백엔드 프록시 (127.0.0.1:8000, 내부 루프백 통신)
[ FastAPI 백엔드 (Python/Uvicorn) ]
```

1. **`sslip.io` (와일드카드 무료 DNS 서비스)**
   - Let's Encrypt와 같은 공인 CA는 일반 공개 IP 주소(예: `34.xxx.xxx.xxx`)에 대해 직접 무료 인증서를 발급해 주지 않고 FQDN(도메인 이름)을 요구합니다.
   - 유료 도메인을 구매하거나 DNS 네임서버를 복잡하게 설정하지 않고, IP 주소 뒤에 `.sslip.io`를 붙이면 해당 IP로 즉시 해석해 주는 DNS 매핑 도메인(`<YOUR_EXTERNAL_IP>.sslip.io`)을 생성하여 인증서 발급 요건을 해결했습니다.

2. **`Let's Encrypt` & `Certbot` (공인 SSL 인증서 자동 발급 및 갱신)**
   - 비영리 글로벌 인증기관인 Let's Encrypt의 공인 인증서를 무료로 발급받았습니다.
   - `certbot` 명령어를 통해 **HTTP-01 챌린지**(Nginx를 통해 임시 토큰을 호스팅하여 도메인 소유권을 자동 검증)를 수행하였고, 인증서가 만료(90일)되기 전 `systemd timer`를 통해 무중단으로 자동 갱신되도록 구성했습니다.

3. **`Nginx` 리버스 프록시 & SSL 오프로딩 (SSL Offloading)**
   - Python FastAPI 앱 자체에 인증서를 물리지 않고, 고성능 웹 서버인 Nginx를 앞단(Reverse Proxy)에 배치하여 TLS 암·복호화 부하를 전담(SSL Termination)하게 했습니다.
   - **HTTP 강제 리다이렉트**: 사용자가 `http://`로 들어와도 `301 Moved Permanently`를 통해 자동으로 `https://`로 전환되도록 설정했습니다.
   - **SSE(Server-Sent Events) 최적화**: 챗봇 답변이 한 글자씩 타이핑되는 실시간 스트리밍이 프록시 버퍼링에 걸려 지연되지 않도록 `proxy_buffering off;` 설정을 적용했습니다.

4. **`GCP VPC 방화벽 (Firewall Rule)` 포트 제어**
   - 기존의 커스텀 포트 `8000` 직접 접근을 배제하고, 표준 웹 포트인 `tcp:80`(HTTP 및 인증서 챌린지 검증용)과 `tcp:443`(HTTPS 보안 통신용)을 인바운드 허용 규칙에 추가하여 네트워크 레벨의 보안을 완성했습니다.

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
pip install -r compute_engine/requirements.txt

# 방법 A: compute_engine 폴더에서 실행 (GEMINI_API_KEY 환경변수 설정 후)
cd compute_engine
python app.py

# 방법 B: 루트 또는 compute_engine 폴더 내 run.bat 더블클릭
```

### 2. GCP Compute Engine 배포 단계 요약

#### 옵션 A: 자동 배포 스크립트 이용 (`deploy_to_vm.sh`)
```bash
# 로컬 터미널 / Cloud Shell에서 실행 (인스턴스가 생성되어 있는 상태)
chmod +x compute_engine/deploy_to_vm.sh
./compute_engine/deploy_to_vm.sh chatbot-instance us-central1-a <YOUR_PROJECT_ID>
```

#### 옵션 B: 단계별 수동 배포

1. **Secret Manager 접근 권한 부여**:
   ```bash
   gcloud secrets add-iam-policy-binding GEMINI_API_KEY \
     --project=<YOUR_PROJECT_ID> \
     --member="serviceAccount:<YOUR_PROJECT_NUMBER>-compute@developer.gserviceaccount.com" \
     --role="roles/secretmanager.secretAccessor"
   ```

2. **Compute Engine 인스턴스 생성**:
   ```bash
   gcloud compute instances create chatbot-instance \
     --project=<YOUR_PROJECT_ID> \
     --zone=us-central1-a \
     --machine-type=e2-medium \
     --tags=chatbot-server,http-server \
     --scopes=https://www.googleapis.com/auth/cloud-platform \
     --metadata-from-file=startup-script=compute_engine/startup-script.sh
   ```

3. **VPC 방화벽 포트 오픈 (8000, 80, 443)**:
   ```bash
   gcloud compute firewall-rules create allow-chatbot-8000 \
     --allow="tcp:8000,tcp:80,tcp:443" \
     --target-tags=chatbot-server
   ```

4. **소스 배포 (SCP 전송)**:
   ```bash
   # VM 내 디렉터리 준비
   gcloud compute ssh chatbot-instance --zone=us-central1-a --command="sudo mkdir -p /opt/chatbot/compute_engine && sudo chown -R \$USER:\$USER /opt/chatbot"

   # compute_engine 소스 전송
   gcloud compute scp --recurse compute_engine/* chatbot-instance:/opt/chatbot/compute_engine/ --zone=us-central1-a
   ```

5. **Python 가상환경 및 systemd 서비스 등록**:
   ```bash
   gcloud compute ssh chatbot-instance --zone=us-central1-a
   
   # VM 내부 접속 후:
   python3 -m venv /opt/chatbot/.venv
   /opt/chatbot/.venv/bin/pip install -r /opt/chatbot/compute_engine/requirements.txt
   sudo cp /opt/chatbot/compute_engine/chatbot.service /etc/systemd/system/chatbot.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now chatbot.service
   ```

6. **Let's Encrypt 공인 SSL 적용 (HTTPS 구축)**:
   ```bash
   sudo apt-get install -y nginx certbot python3-certbot-nginx
   sudo cp /opt/chatbot/compute_engine/chatbot.conf /etc/nginx/sites-available/chatbot
   sudo ln -sf /etc/nginx/sites-available/chatbot /etc/nginx/sites-enabled/
   sudo certbot --nginx -d <외부IP>.sslip.io --non-interactive --agree-tos -m <이메일> --redirect
   ```

---

## 🛠️ 인스턴스 유지보수 명령어

- **인스턴스 SSH 원격 접속**:
  ```bash
  gcloud compute ssh chatbot-instance --zone=us-central1-a --project=<YOUR_PROJECT_ID>
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
  gcloud compute instances delete chatbot-instance --zone=us-central1-a --project=<YOUR_PROJECT_ID> --quiet
  ```
