#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "╔══════════════════════════════════════╗"
echo "║        LocalVoiceAI  v1.0            ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ---------------------------------------------------------------------------
# 1. Check Python installation
# ---------------------------------------------------------------------------
echo "→ Checking Python installation..."
if ! command -v python3 &>/dev/null; then
    echo "  ✗ Python 3 is not installed or not on PATH."
    echo "    macOS:  brew install python"
    echo "    Ubuntu: sudo apt install python3 python3-pip"
    exit 1
fi

PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! python3 -c "import sys; assert sys.version_info >= (3, 10)" 2>/dev/null; then
    echo "  ✗ Python 3.10+ is required but was not found (found ${PYVER})."
    echo "    Please upgrade Python: https://www.python.org/downloads/"
    exit 1
fi
echo "  ✓ Python ${PYVER} detected."

# ---------------------------------------------------------------------------
# 2. Verify pip availability
# ---------------------------------------------------------------------------
echo ""
echo "→ Checking pip availability..."
if ! python3 -m pip --version &>/dev/null 2>&1; then
    echo "  ✗ pip is not available for the current python3."
    echo "    macOS:  python3 -m ensurepip --upgrade"
    echo "    Ubuntu: sudo apt install python3-pip"
    exit 1
fi
echo "  ✓ pip available (python3 -m pip)."

# ---------------------------------------------------------------------------
# 3. Create workspace and log directories
# ---------------------------------------------------------------------------
mkdir -p logs workspace/files workspace/spreadsheets workspace/downloads

# ---------------------------------------------------------------------------
# 4. Install Python dependencies
# ---------------------------------------------------------------------------
echo ""
echo "→ Installing Python dependencies..."
if ! python3 -m pip install --upgrade pip -q; then
    echo "  ✗ Failed to upgrade pip."
    echo "    Try running manually: python3 -m pip install --upgrade pip"
    exit 1
fi
if ! python3 -m pip install -r backend/requirements.txt -q; then
    echo "  ✗ Failed to install Python dependencies."
    echo "    Try running manually: python3 -m pip install -r backend/requirements.txt"
    exit 1
fi
echo "  ✓ Python dependencies installed."

# ---------------------------------------------------------------------------
# 5. Check Ollama connection
# ---------------------------------------------------------------------------
echo ""
echo "→ Checking Ollama connection..."
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
if curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    echo "  ✓ Ollama detected at ${OLLAMA_URL}"
else
    echo "  ⚠  Ollama not detected at ${OLLAMA_URL}."
    echo "     Please start Ollama before running LocalVoiceAI."
    echo "       ollama serve"
    echo "     Then pull a model:"
    echo "       ollama pull qwen2.5:7b"
    echo "     (The server will still start — Ollama can be connected later)"
fi

# ---------------------------------------------------------------------------
# 6. Resolve server port and check for conflicts
# ---------------------------------------------------------------------------
echo ""
echo "→ Starting backend server..."
PORT=$(python3 -c "import json; d=json.load(open('config/settings.json')); print(d['server']['port'])" 2>/dev/null || echo "8000")

if lsof -iTCP:"${PORT}" -sTCP:LISTEN &>/dev/null 2>&1 || \
   ss -tlnp "sport = :${PORT}" &>/dev/null 2>&1; then
    echo "  ⚠  Port ${PORT} is already in use. Another process may be running."
    echo "     Change the port in config/settings.json, or stop the existing process first."
    echo "     To find the blocking process: lsof -iTCP:${PORT} -sTCP:LISTEN"
    exit 1
fi

cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait for server to be ready (up to 10 seconds)
echo "  Waiting for server on port ${PORT}..."
for i in $(seq 1 20); do
    if curl -sf "http://localhost:${PORT}/api/status" > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

# ---------------------------------------------------------------------------
# 7. Display running URL
# ---------------------------------------------------------------------------
echo ""
echo "╔══════════════════════════════════════╗"
echo "║  LocalVoiceAI is running at:         ║"
echo "║                                      ║"
printf "║  http://localhost:%-18s  ║\n" "${PORT}"
echo "║                                      ║"
echo "║  Press Ctrl+C to stop                ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Wait for backend process (or Ctrl+C)
wait $BACKEND_PID
