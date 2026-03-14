import asyncio
import json
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

import aiofiles
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Ensure project root is on the path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(Path(__file__).parent))

from llm.ollama_client import OllamaClient
from voice.stt import WhisperSTT
from voice.tts import TTSEngine
from tool_router.router import ToolRouter
from tool_router.permissions import PermissionManager
from logger import ActionLogger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_AGENTIC_ITERATIONS = 10
CONFIRMATION_TIMEOUT_SECONDS = 60

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(title="LocalVoiceAI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load settings
SETTINGS_PATH = ROOT_DIR / "config" / "settings.json"
with open(SETTINGS_PATH) as f:
    SETTINGS = json.load(f)

# Singletons
ollama = OllamaClient(base_url=SETTINGS["ollama"]["base_url"])
stt = WhisperSTT(model_name=SETTINGS["voice"]["whisper_model"])
tts = TTSEngine()
permissions = PermissionManager(config_path=str(ROOT_DIR / "config" / "permissions.json"))
logger = ActionLogger(log_dir=str(ROOT_DIR / "logs"))
router = ToolRouter(permissions=permissions, logger=logger)

# Serve frontend
FRONTEND_DIR = ROOT_DIR / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")


@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@app.get("/api/status")
async def get_status():
    connected = await ollama.check_connection()
    models = await ollama.list_models() if connected else []
    return {"ollama_connected": connected, "models": models}


@app.get("/api/models")
async def get_models():
    models = await ollama.list_models()
    return {"models": models}


class ChatRequest(BaseModel):
    message: str
    model: str = None
    history: list = []


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    model = req.model or SETTINGS["ollama"]["default_model"]
    messages = req.history + [{"role": "user", "content": req.message}]
    response = await ollama.chat(model, messages)
    return {"response": response}


@app.post("/api/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    audio_bytes = await file.read()
    text = await asyncio.to_thread(stt.transcribe, audio_bytes)
    return {"text": text}


class SynthesizeRequest(BaseModel):
    text: str


@app.post("/api/voice/synthesize")
async def synthesize_voice(req: SynthesizeRequest):
    import tempfile, base64
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
    await asyncio.to_thread(tts.synthesize_to_file, req.text, tmp_path)
    async with aiofiles.open(tmp_path, "rb") as f:
        audio_bytes = await f.read()
    os.unlink(tmp_path)
    audio_b64 = base64.b64encode(audio_bytes).decode()
    return {"audio": audio_b64, "format": "wav"}


@app.get("/api/permissions")
async def get_permissions():
    return permissions.get_all()


class PermissionsUpdate(BaseModel):
    permissions: dict


@app.post("/api/permissions")
async def update_permissions(req: PermissionsUpdate):
    for key, value in req.permissions.items():
        if value:
            permissions.grant(key)
        else:
            permissions.revoke(key)
    return {"status": "ok", "permissions": permissions.get_all()}


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    return {"logs": logger.get_logs(limit=limit)}


@app.delete("/api/logs")
async def clear_logs():
    logger.clear_logs()
    return {"status": "ok"}


@app.get("/api/tools")
async def list_tools():
    return {"tools": router.list_tools()}


# ---------------------------------------------------------------------------
# WebSocket
# ---------------------------------------------------------------------------

# Pending confirmation requests: id -> asyncio.Future
_pending_confirmations: dict[str, asyncio.Future] = {}


async def _ws_send(ws: WebSocket, data: dict):
    try:
        await ws.send_text(json.dumps(data))
    except Exception:
        pass


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    # Send initial status
    connected = await ollama.check_connection()
    models = await ollama.list_models() if connected else []
    await _ws_send(ws, {"type": "status", "ollama_connected": connected, "models": models})

    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _ws_send(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type")

            if msg_type == "chat":
                await handle_chat(ws, msg)

            elif msg_type == "confirm":
                confirm_id = msg.get("id")
                allowed = msg.get("allowed", False)
                always = msg.get("always", False)
                future = _pending_confirmations.pop(confirm_id, None)
                if future and not future.done():
                    future.set_result({"allowed": allowed, "always": always})

            elif msg_type == "cancel":
                confirm_id = msg.get("id")
                future = _pending_confirmations.pop(confirm_id, None)
                if future and not future.done():
                    future.set_result({"allowed": False, "always": False})

            else:
                await _ws_send(ws, {"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await _ws_send(ws, {"type": "error", "message": str(e)})
        except Exception:
            pass


async def handle_chat(ws: WebSocket, msg: dict):
    """Full chat loop with tool execution."""
    model = msg.get("model") or SETTINGS["ollama"]["default_model"]
    user_message = msg.get("message", "")
    history = msg.get("history", [])

    messages = history + [{"role": "user", "content": user_message}]

    # Agentic loop: up to MAX_AGENTIC_ITERATIONS tool calls
    for _ in range(MAX_AGENTIC_ITERATIONS):
        try:
            response_text = await ollama.chat(model, messages)
        except Exception as e:
            await _ws_send(ws, {"type": "error", "message": f"LLM error: {e}"})
            return

        # Check for tool call
        tool_call = _extract_tool_call(response_text)

        if tool_call is None:
            # Final answer — stream it to the client
            await _ws_send(ws, {"type": "chat", "message": response_text, "role": "assistant"})
            return

        tool_name = tool_call.get("tool")
        tool_args = tool_call.get("args", {})

        # Notify client tool is starting
        await _ws_send(ws, {"type": "tool_start", "tool": tool_name, "args": tool_args})

        # Build a confirmation callback that sends a confirm request over WS
        async def confirmation_callback(t_name: str, t_args: dict, description: str) -> bool:
            confirm_id = str(uuid.uuid4())
            future: asyncio.Future = asyncio.get_event_loop().create_future()
            _pending_confirmations[confirm_id] = future
            await _ws_send(ws, {
                "type": "tool_confirm",
                "id": confirm_id,
                "tool": t_name,
                "args": t_args,
                "description": description,
            })
            try:
                result = await asyncio.wait_for(future, timeout=CONFIRMATION_TIMEOUT_SECONDS)
                return result.get("allowed", False)
            except asyncio.TimeoutError:
                _pending_confirmations.pop(confirm_id, None)
                return False

        start_time = time.time()
        exec_result = await router.execute(tool_name, tool_args, confirmation_callback)
        duration_ms = int((time.time() - start_time) * 1000)

        status = exec_result.get("status", "error")

        if status == "blocked":
            await _ws_send(ws, {
                "type": "tool_blocked",
                "tool": tool_name,
                "reason": exec_result.get("error", "Permission denied"),
            })
        else:
            result_data = exec_result.get("result", "")
            result_summary = str(result_data)[:200] if result_data else exec_result.get("error", "")
            await _ws_send(ws, {
                "type": "tool_end",
                "tool": tool_name,
                "status": status,
                "duration_ms": duration_ms,
                "result_summary": result_summary,
            })

        # Add assistant tool call + tool result to messages
        messages.append({"role": "assistant", "content": response_text})
        messages.append({
            "role": "user",
            "content": f"Tool result for {tool_name}: {json.dumps(exec_result)}",
        })

    # If we exit the loop, give a final response
    await _ws_send(ws, {
        "type": "chat",
        "message": "I've completed the requested operations.",
        "role": "assistant",
    })


def _extract_tool_call(text: str) -> dict | None:
    """Extract tool_call JSON from LLM response text by scanning for balanced JSON objects."""
    import re
    try:
        for match in re.finditer(r'\{', text):
            start = match.start()
            depth = 0
            for i, ch in enumerate(text[start:], start):
                if ch == '{':
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        candidate = text[start:i + 1]
                        try:
                            parsed = json.loads(candidate)
                            if "tool_call" in parsed:
                                return parsed["tool_call"]
                        except json.JSONDecodeError:
                            pass
                        break
    except Exception:
        pass
    return None


if __name__ == "__main__":
    host = SETTINGS["server"]["host"]
    port = SETTINGS["server"]["port"]
    uvicorn.run("main:app", host=host, port=port, reload=False)
