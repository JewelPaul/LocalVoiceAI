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

echo "→ Starting server on http://localhost:8000"
python main.py
