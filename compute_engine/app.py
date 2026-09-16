import os
import json
import base64
import webbrowser
from typing import List, Optional
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Gemini Flash Local Chatbot")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_gemini_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    # Fallback to GCP Secret Manager
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()

        # 프로젝트 ID 자동 감지 (환경변수 또는 GCP 기본 인증 정보)
        project_id = os.environ.get("GCP_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        if not project_id:
            try:
                import google.auth
                _, project_id = google.auth.default()
            except Exception:
                pass

        if not project_id:
            project_id = "YOUR_GCP_PROJECT_ID"

        name = f"projects/{project_id}/secrets/GEMINI_API_KEY/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_val = response.payload.data.decode("UTF-8").strip()
        if secret_val:
            print(f"[INFO] Successfully retrieved GEMINI_API_KEY from GCP Secret Manager (Project: {project_id}).")
            return secret_val
    except Exception as e:
        print(f"[WARN] Could not retrieve GEMINI_API_KEY from Secret Manager: {e}")
    return ""

GEMINI_API_KEY = get_gemini_api_key()

# Available Flash models
SUPPORTED_MODELS = [
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "shortName": "Flash 3.8",
        "description": "최신 차세대 고속 Flash 모델 (기본값)",
        "badge": "기본 모델"
    },
    {
        "id": "gemini-3.7-flash",
        "name": "Gemini 3.7 Flash",
        "shortName": "Flash 3.7",
        "description": "안정적이고 빠른 지능형 Flash 모델",
        "badge": "선택 가능"
    }
]

class ChatPart(BaseModel):
    text: Optional[str] = None
    mime_type: Optional[str] = None
    data: Optional[str] = None

class ChatMessage(BaseModel):
    role: str  # "user" or "model"
    content: str
    image: Optional[dict] = None  # { mime_type: str, data: str }

class ChatRequest(BaseModel):
    model: str = "gemini-3.8-flash"
    messages: List[ChatMessage]
    system_prompt: Optional[str] = None
    enable_search: bool = True
    thinking_level: Optional[str] = "medium"

@app.get("/api/status")
async def get_status():
    global GEMINI_API_KEY
    if not GEMINI_API_KEY:
        GEMINI_API_KEY = get_gemini_api_key()
    api_key_set = bool(GEMINI_API_KEY)
    masked_key = f"{GEMINI_API_KEY[:6]}...{GEMINI_API_KEY[-4:]}" if api_key_set and len(GEMINI_API_KEY) > 10 else ("설정됨" if api_key_set else "미설정")
    return {
        "status": "ready" if api_key_set else "need_api_key",
        "apiKeySet": api_key_set,
        "maskedKey": masked_key,
        "defaultModel": "gemini-3.8-flash",
        "models": SUPPORTED_MODELS,
        "webSearchSupported": True
    }

@app.post("/api/chat/stream")
async def chat_stream(request: ChatRequest):
    global GEMINI_API_KEY
    api_key = os.environ.get("GEMINI_API_KEY", "").strip() or GEMINI_API_KEY or get_gemini_api_key()
    if not api_key:
        raise HTTPException(
            status_code=400,
            detail="GEMINI_API_KEY 환경변수가 설정되지 않았습니다. Secret Manager 또는 시스템 환경변수를 확인해주세요."
        )

    model_id = request.model
    # Validate model
    valid_ids = [m["id"] for m in SUPPORTED_MODELS]
    if model_id not in valid_ids:
        model_id = "gemini-3.8-flash"

    # Build Gemini API contents payload
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

    gen_config = {
        "temperature": 0.7,
        "maxOutputTokens": 65536
    }
    if request.thinking_level:
        gen_config["thinkingConfig"] = {
            "thinkingLevel": request.thinking_level
        }

    payload = {
        "contents": contents,
        "generationConfig": gen_config
    }

    # Enable Google Search grounding (Internet connection)
    if request.enable_search:
        payload["tools"] = [{"googleSearch": {}}]

    if request.system_prompt:
        payload["system_instruction"] = {
            "parts": [{"text": request.system_prompt}]
        }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={api_key}"

    async def sse_generator():
        timeout = httpx.Timeout(120.0, connect=20.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                async with client.stream("POST", url, json=payload, headers={"Content-Type": "application/json"}) as response:
                    if response.status_code != 200:
                        err_body = await response.aread()
                        err_msg = f"Gemini API 오류 ({response.status_code}): {err_body.decode('utf-8', errors='ignore')}"
                        yield f"data: {json.dumps({'error': err_msg})}\n\n"
                        return

                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        if line.startswith("data: "):
                            raw_data = line[6:].strip()
                            try:
                                chunk = json.loads(raw_data)
                                candidates = chunk.get("candidates", [])
                                if candidates:
                                    cand = candidates[0]
                                    content = cand.get("content", {})
                                    parts = content.get("parts", [])
                                    text_piece = "".join(p.get("text", "") for p in parts)
                                    finish_reason = cand.get("finishReason")
                                    
                                    # Check for Google Search Grounding Metadata
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
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

# Static files directory
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
    return HTMLResponse("<h1>Gemini Chatbot UI loading...</h1>")

if __name__ == "__main__":
    import uvicorn
    print("==================================================")
    print(" Gemini Flash Local Web Service Starting...")
    print(" Default Model: gemini-3.8-flash (Option: gemini-3.7-flash)")
    print(f" API Key Loaded: {'Yes' if GEMINI_API_KEY else 'No (Set GEMINI_API_KEY env)'}")
    print(" URL: http://localhost:8000")
    print("==================================================")
    
    try:
        webbrowser.open("http://localhost:8000")
    except Exception:
        pass

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)
