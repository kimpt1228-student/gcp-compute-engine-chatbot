import os
import sys
import json
import base64
import time
from typing import List, Optional, Tuple
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import google.auth
from google.auth.transport.requests import Request as GoogleAuthRequest

app = FastAPI(
    title="Gemini Cloud Run Chatbot (ADC Mode)",
    description="Google Cloud Run Serverless Gemini Chatbot Service with Application Default Credentials (ADC)"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPPORTED_MODELS = [
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "shortName": "Flash 2.5",
        "description": "Vertex AI 초고속 차세대 Flash 모델 (초저지연, 기본값)",
        "badge": "기본 모델"
    },
    {
        "id": "gemini-2.5-pro",
        "name": "Gemini 2.5 Pro",
        "shortName": "Pro 2.5",
        "description": "복잡한 분석 및 정밀 추론에 특화된 고지능 모델",
        "badge": "선택 가능"
    }
]

# Vertex AI 지원 모델 매핑 (구버전 또는 프리뷰 모델명 요청 시 최신 모델로 자동 변환)
MODEL_ALIASES = {
    "gemini-3.8-flash": "gemini-2.5-flash",
    "gemini-3.7-flash": "gemini-2.5-flash",
    "gemini-2.0-flash": "gemini-2.5-flash",
    "gemini-1.5-flash": "gemini-2.5-flash",
    "gemini-1.5-pro": "gemini-2.5-pro",
}

class ADCTokenManager:
    """
    Application Default Credentials (ADC) 관리자
    - Google Cloud Run 환경: 컨테이너에 부여된 Compute Engine 기본 서비스 계정으로 자동 인증
    - 로컬 개발 환경: 'gcloud auth application-default login'으로 인증된 자격 증명 사용
    - 수동 API Key 관리나 Secret Manager 설정이 일체 불필요
    """
    def __init__(self):
        self.credentials = None
        self.project_id = None
        self._auth_request = GoogleAuthRequest()
        self.refresh_credentials()

    def refresh_credentials(self) -> bool:
        try:
            scopes = ["https://www.googleapis.com/auth/cloud-platform"]
            self.credentials, detected_proj = google.auth.default(scopes=scopes)
            self.project_id = (
                detected_proj
                or os.environ.get("GOOGLE_CLOUD_PROJECT")
                or os.environ.get("GCP_PROJECT_ID")
                or getattr(self.credentials, "project_id", None)
            )
            return True
        except Exception as e:
            self.credentials = None
            self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID")
            print(f"[WARN] ADC 초기화 실패: {e}")
            return False

    def get_token_and_project(self) -> Tuple[str, str]:
        if not self.credentials:
            if not self.refresh_credentials():
                raise RuntimeError(
                    "Application Default Credentials (ADC)를 찾을 수 없습니다.\n"
                    "로컬 환경: gcloud auth application-default login 실행\n"
                    "Cloud Run 환경: 서비스 계정에 'roles/aiplatform.user' 권한 필요"
                )

        if not self.credentials.valid or not self.credentials.token:
            try:
                self.credentials.refresh(self._auth_request)
            except Exception as e:
                self.refresh_credentials()
                if self.credentials:
                    self.credentials.refresh(self._auth_request)
                else:
                    raise RuntimeError(f"ADC 토큰 갱신 실패: {e}")

        project = self.project_id or "iceu-songpa23"
        return self.credentials.token, project

    def get_identity_info(self) -> dict:
        if not self.credentials:
            self.refresh_credentials()

        is_ready = bool(self.credentials)
        service_account_email = getattr(self.credentials, "service_account_email", None)
        signer_email = getattr(self.credentials, "signer_email", None)
        account = service_account_email or signer_email or "ADC Identity (Cloud Run SA / gcloud user)"
        
        return {
            "ready": is_ready,
            "auth_type": "Application Default Credentials (ADC)",
            "account": account if is_ready else "Unauthenticated",
            "project_id": self.project_id or "iceu-songpa23"
        }

adc_manager = ADCTokenManager()

class ChatMessage(BaseModel):
    role: str  # "user" or "model"
    content: str
    image: Optional[dict] = None

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = "gemini-2.5-flash"
    webSearch: Optional[bool] = None
    enable_search: Optional[bool] = None  # 프론트엔드 호환용
    system_prompt: Optional[str] = None
    thinking_level: Optional[str] = None

# 브라우저의 favicon.ico 자동 요청에 대해 204 No Content 반환 (404 WARNING 방지)
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.get("/health")
async def health_check():
    info = adc_manager.get_identity_info()
    return {
        "status": "healthy",
        "platform": "Google Cloud Run (ADC Mode)",
        "authType": "Application Default Credentials",
        "ready": info["ready"],
        "project": info["project_id"]
    }

@app.get("/api/status")
async def get_status():
    info = adc_manager.get_identity_info()
    return {
        "status": "ready" if info["ready"] else "need_adc_login",
        "platform": "Google Cloud Run (ADC Mode)",
        "authType": "Application Default Credentials (ADC)",
        "apiKeySet": True,
        "maskedKey": f"ADC Authenticated ({info['account']})",
        "defaultModel": "gemini-2.5-flash",
        "models": SUPPORTED_MODELS,
        "webSearchSupported": True,
        "adcInfo": info
    }

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    ADC 기반 Vertex AI Model API 초고속 SSE 스트리밍
    """
    try:
        token, project_id = adc_manager.get_token_and_project()
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))

    # 요청 모델명을 실제 Vertex AI 지원 모델로 변환
    requested_model = request.model or "gemini-2.5-flash"
    actual_model = MODEL_ALIASES.get(requested_model, requested_model)

    # 메시지 파싱
    contents = []
    for msg in request.messages:
        role = "user" if msg.role == "user" else "model"
        parts = []
        if msg.image and msg.image.get("data"):
            parts.append({
                "inline_data": {
                    "mime_type": msg.image.get("mime_type", "image/png"),
                    "data": msg.image.get("data")
                }
            })
        if msg.content:
            parts.append({"text": msg.content})

        if parts:
            contents.append({
                "role": role,
                "parts": parts
            })

    if not contents:
        raise HTTPException(status_code=400, detail="메시지 내용이 비어있습니다.")

    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192
        }
    }

    # 웹 검색 옵션 (webSearch 또는 enable_search)
    should_search = (request.webSearch is True) or (request.enable_search is True)
    if should_search:
        payload["tools"] = [{"googleSearch": {}}]

    if request.system_prompt:
        payload["systemInstruction"] = {
            "parts": [{"text": request.system_prompt}]
        }

    # Vertex AI 엔드포인트 (us-central1 기본 설정: 초저지연 및 쿼터 안정성 보장)
    location = os.environ.get("VERTEX_LOCATION", "us-central1")
    endpoint_url = (
        f"https://{location}-aiplatform.googleapis.com/v1/projects/{project_id}/"
        f"locations/{location}/publishers/google/models/{actual_model}:streamGenerateContent?alt=sse"
    )

    headers = {
        "Authorization": f"Bearer {token}",
        "X-Goog-User-Project": project_id,
        "Content-Type": "application/json"
    }

    async def sse_generator():
        timeout = httpx.Timeout(60.0, connect=10.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream("POST", endpoint_url, json=payload, headers=headers) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        err_msg = f"Gemini API 오류 ({response.status_code}): {err_body.decode('utf-8', errors='ignore')}"
                        yield f"data: {json.dumps({'error': err_msg})}\n\n"
                        yield "data: [DONE]\n\n"
                        return

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line or not line.startswith("data: "):
                            continue
                        raw_data = line[6:].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(raw_data)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                cand = candidates[0]
                                content = cand.get("content", {})
                                parts = content.get("parts", [])
                                text_piece = "".join(p.get("text", "") for p in parts if "text" in p)
                                finish_reason = cand.get("finishReason")

                                # Grounding metadata
                                if "groundingMetadata" in cand:
                                    gm = cand["groundingMetadata"]
                                    queries = gm.get("webSearchQueries", [])
                                    chunks = gm.get("groundingChunks", [])
                                    sources = []
                                    for c in chunks:
                                        web = c.get("web")
                                        if web and web.get("uri"):
                                            sources.append({
                                                "title": web.get("title") or web.get("uri"),
                                                "uri": web.get("uri")
                                            })
                                    if queries or sources:
                                        yield f"data: {json.dumps({'grounding': {'queries': queries, 'sources': sources}})}\n\n"

                                if text_piece:
                                    yield f"data: {json.dumps({'text': text_piece})}\n\n"
                                if finish_reason and finish_reason not in ["STOP", None]:
                                    yield f"data: {json.dumps({'finish_reason': finish_reason})}\n\n"
                        except Exception:
                            pass

                    yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': f'통신 타임아웃 또는 연결 오류: {str(e)}'})}\n\n"
                yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# 정적 파일 서빙
static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def read_index():
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        with open(index_file, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Gemini ADC Chatbot UI loading...</h1>")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
