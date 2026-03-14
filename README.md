# LocalVoiceAI 🎙️

A modular, **fully local** Voice AI Agent Platform. Talk to an LLM running on your machine, let it search the web, manage files, generate spreadsheets, run OCR, and more — all without any cloud services.

---

## Features

| Feature | Detail |
|---|---|
| 🎤 Voice input | Whisper STT (faster-whisper or openai-whisper) |
| 🔊 Voice output | pyttsx3 / espeak / macOS `say` |
| 🧠 Local LLM | Ollama (default: `qwen2.5:7b`) |
| 🌐 Web search | DuckDuckGo (no API key needed) |
| 📁 File management | Sandboxed to `workspace/files/` |
| 📊 Spreadsheets | Generate `.xlsx` and `.csv` |
| ⬇️ Downloads | Single & batch file downloads |
| 🔍 OCR | Tesseract via pytesseract |
| 🖼️ Image search | DuckDuckGo image search |
| 🎬 Video search | YouTube / DuckDuckGo |
| 🔒 Permissions | Per-category toggles in the UI |

---

## Prerequisites

- **Python 3.9+**
- **[Ollama](https://ollama.ai)** installed and running (`ollama serve`)
  - Pull a model: `ollama pull qwen2.5:7b`
- (Optional) **Tesseract OCR** for image text extraction:
  - macOS: `brew install tesseract`
  - Ubuntu: `sudo apt install tesseract-ocr`

---

## Quick Start

```bash
git clone https://github.com/JewelPaul/LocalVoiceAI.git
cd LocalVoiceAI
bash start.sh
```

Then open **http://localhost:8000** in your browser.

> `start.sh` installs Python dependencies, creates workspace directories, and starts the FastAPI server.

---

## Folder Structure

```
project-root/
├── backend/
│   ├── main.py                 # FastAPI app + WebSocket
│   ├── llm/
│   │   └── ollama_client.py    # Ollama integration
│   ├── voice/
│   │   ├── stt.py              # Whisper STT
│   │   └── tts.py              # TTS engine
│   ├── tool_router/
│   │   ├── router.py           # Tool execution + permissions
│   │   └── permissions.py      # Permission manager
│   ├── tools/
│   │   ├── web_tools.py        # web_search, scrape_page, summarize_webpage
│   │   ├── file_tools.py       # File CRUD operations
│   │   ├── spreadsheet_tools.py# XLSX + CSV generation
│   │   ├── download_tools.py   # File downloads
│   │   ├── ocr_tools.py        # OCR + PDF text extraction
│   │   ├── image_tools.py      # Image search + download
│   │   └── video_tools.py      # Video search
│   ├── logger.py               # JSONL action logger
│   └── requirements.txt
├── frontend/
│   ├── index.html              # Single-page UI
│   └── static/
│       ├── css/style.css
│       └── js/
│           ├── app.js          # Main app logic + WebSocket
│           ├── voice.js        # MediaRecorder + waveform
│           └── tools.js        # Tool activity display
├── config/
│   ├── settings.json           # Ollama URL, model, server port
│   └── permissions.json        # Default tool permissions
├── logs/                       # actions.jsonl (runtime)
├── workspace/                  # AI sandbox
│   ├── files/
│   ├── spreadsheets/
│   └── downloads/
└── start.sh
```

---

## Available Tools

| Tool | Permission | Sensitive? | Description |
|---|---|---|---|
| `web_search` | browser | No | DuckDuckGo search |
| `scrape_page` | browser | No | Fetch and parse webpage |
| `summarize_webpage` | browser | No | First 2000 chars of page |
| `create_file` | files | No | Create file in workspace |
| `read_file` | files | No | Read file from workspace |
| `write_file` | files | No | Write/overwrite file |
| `delete_file` | files | **Yes** | Delete file (requires confirmation) |
| `create_folder` | files | No | Create folder |
| `list_directory` | files | No | List directory contents |
| `generate_xlsx` | spreadsheets | No | Generate Excel file |
| `generate_csv` | spreadsheets | No | Generate CSV file |
| `download_file` | downloads | No | Download single file |
| `batch_download` | downloads | **Yes** | Download multiple files |
| `extract_text_from_image` | ocr | No | Tesseract OCR on image |
| `extract_text_from_pdf` | ocr | No | Extract text from PDF |
| `image_search` | images | No | DuckDuckGo image search |
| `image_download` | images | No | Download image |
| `video_search` | video | No | YouTube / DDG video search |

---

## Permission System

Each tool category has a toggle switch in the **Permissions** panel (right side of UI). Permissions are saved to `config/permissions.json`.

| Key | Covers |
|---|---|
| `files` | All file read/write/delete operations |
| `downloads` | Downloading files from the internet |
| `browser` | Web search and page scraping |
| `email` | Email access (disabled by default) |
| `ocr` | OCR and PDF text extraction |
| `images` | Image search and download |
| `video` | Video search |
| `spreadsheets` | XLSX / CSV generation |

**Sensitive tools** (marked above) also require an explicit confirmation dialog before execution.

---

## Voice Usage

1. Click the **🎙️** microphone button to start recording.
2. Speak your request; a waveform shows audio input.
3. Click again (or wait) to stop — audio is sent to the Whisper STT endpoint.
4. The transcribed text is automatically sent as a chat message.
5. The AI responds via text and (optionally) synthesized speech.

---

## Configuration

Edit `config/settings.json`:

```json
{
  "ollama": {
    "base_url": "http://localhost:11434",
    "default_model": "qwen2.5:7b",
    "timeout": 60
  },
  "voice": {
    "whisper_model": "base",
    "language": "en",
    "tts_engine": "auto"
  },
  "server": {
    "host": "0.0.0.0",
    "port": 8000
  }
}
```

- **`whisper_model`**: `tiny`, `base`, `small`, `medium`, `large` — larger = more accurate but slower.
- **`default_model`**: Any model you have pulled with `ollama pull <model>`.
- **`port`**: Change if 8000 is occupied.

---

## Architecture

```
Browser (HTML/CSS/JS)
        │  WebSocket  │  REST
        ▼             ▼
   FastAPI (main.py)
   ┌──────────────────────────────┐
   │  OllamaClient  ←→  Ollama    │
   │  WhisperSTT   (transcription)│
   │  TTSEngine    (synthesis)    │
   │  ToolRouter                  │
   │    └── PermissionManager     │
   │    └── Tools:                │
   │         web / file / xlsx    │
   │         download / ocr       │
   │         image / video        │
   │  ActionLogger (JSONL)        │
   └──────────────────────────────┘
```

The **agentic loop** in `main.py`:
1. User message → Ollama LLM
2. LLM outputs `{"tool_call": {"tool": "...", "args": {...}}}` → ToolRouter executes it
3. Result fed back to LLM as context
4. Repeat up to 10 iterations, then return final answer

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Serve frontend |
| `WS` | `/ws` | WebSocket (chat + tools) |
| `GET` | `/api/status` | Ollama connectivity + models |
| `GET` | `/api/models` | List Ollama models |
| `POST` | `/api/chat` | Single-turn REST chat |
| `POST` | `/api/voice/transcribe` | Upload audio → text |
| `POST` | `/api/voice/synthesize` | Text → WAV audio (base64) |
| `GET/POST` | `/api/permissions` | Read / update permissions |
| `GET/DELETE` | `/api/logs` | Read / clear action logs |
| `GET` | `/api/tools` | List registered tools |

---

## License

MIT
