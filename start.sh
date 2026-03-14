#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "╔══════════════════════════════════════╗"
echo "║        LocalVoiceAI  v1.0            ║"
echo "╚══════════════════════════════════════╝"

# Create workspace and log directories if they don't exist
mkdir -p logs workspace/files workspace/spreadsheets workspace/downloads

echo "→ Installing Python dependencies..."
cd backend
pip install -r requirements.txt -q
cd ..

echo ""
echo "→ Checking Ollama connection..."
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
if curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    echo "  ✓ Ollama detected at ${OLLAMA_URL}"
else
    echo "  ⚠  Ollama not running at ${OLLAMA_URL}"
    echo "     Start Ollama with: ollama serve"
    echo "     Then pull a model: ollama pull qwen2.5:7b"
    echo "     (The server will still start — Ollama can be started later)"
fi

echo ""
echo "→ Starting backend server..."
PORT=$(python3 -c "import json; d=json.load(open('config/settings.json')); print(d['server']['port'])" 2>/dev/null || echo "8000")

cd backend
python3 main.py &
BACKEND_PID=$!
cd ..

# Wait for server to be ready
echo "  Waiting for server on port ${PORT}..."
for i in $(seq 1 20); do
    if curl -sf "http://localhost:${PORT}/api/status" > /dev/null 2>&1; then
        break
    fi
    sleep 0.5
done

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  LocalVoiceAI running at:            ║"
echo "║                                      ║"
printf "║  http://localhost:%-18s  ║\n" "${PORT}"
echo "║                                      ║"
echo "║  Press Ctrl+C to stop                ║"
echo "╚══════════════════════════════════════╝"
echo ""

# Wait for backend process (or Ctrl+C)
wait $BACKEND_PID
