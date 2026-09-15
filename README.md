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
       ▼ (1) 도메인 질의 : 136.113.50.82.sslip.io ──▶ IP 자동 반환 (sslip.io DNS 매직)
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
   - Let's Encrypt와 같은 공인 CA는 일반 공개 IP 주소(예: `136.113.50.82`)에 대해 직접 무료 인증서를 발급해 주지 않고 FQDN(도메인 이름)을 요구합니다.
   - 유료 도메인을 구매하거나 DNS 네임서버를 복잡하게 설정하지 않고, IP 주소 뒤에 `.sslip.io`를 붙이면 해당 IP로 즉시 해석해 주는 DNS 매핑 도메인(`136.113.50.82.sslip.io`)을 생성하여 인증서 발급 요건을 해결했습니다.

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
