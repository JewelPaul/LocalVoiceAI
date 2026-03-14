#!/bin/bash
# check_deps.sh – Verify system and Python dependencies for LocalVoiceAI

set -e
cd "$(dirname "$0")/.."

echo "=== LocalVoiceAI Dependency Checker ==="
echo ""

# Python version
echo -n "Python 3.9+: "
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "NOT FOUND")
if python3 -c "import sys; assert sys.version_info >= (3, 9)" 2>/dev/null; then
    echo "✓ ($PYVER)"
else
    echo "✗ Python 3.9+ required (found $PYVER)"
fi

# Ollama
echo -n "Ollama:      "
OLLAMA_URL="${OLLAMA_URL:-http://localhost:11434}"
if curl -sf "${OLLAMA_URL}/api/tags" > /dev/null 2>&1; then
    MODELS=$(curl -sf "${OLLAMA_URL}/api/tags" | python3 -c "import sys,json; d=json.load(sys.stdin); print(', '.join(m['name'] for m in d.get('models',[])) or 'no models pulled')" 2>/dev/null || echo "running")
    echo "✓ ($MODELS)"
else
    echo "✗ Not running at $OLLAMA_URL  →  run: ollama serve"
fi

# Python packages
echo ""
echo "Python packages:"
for pkg in fastapi uvicorn httpx aiofiles pydantic requests beautifulsoup4 openpyxl; do
    printf "  %-25s" "$pkg"
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "✓"
    else
        echo "✗ (install: pip install $pkg)"
    fi
done

# Optional packages
echo ""
echo "Optional packages:"
for pkg in faster_whisper pyttsx3 pytesseract PyPDF2; do
    printf "  %-25s" "$pkg"
    if python3 -c "import $pkg" 2>/dev/null; then
        echo "✓"
    else
        echo "- (not installed)"
    fi
done
# Pillow uses 'PIL' as import name but installs as 'pillow'
printf "  %-25s" "PIL (Pillow)"
if python3 -c "import PIL" 2>/dev/null; then
    echo "✓"
else
    echo "- (install: pip install pillow)"
fi

# Tesseract OCR
echo -n "  tesseract (system):      "
if command -v tesseract >/dev/null 2>&1; then
    echo "✓ ($(tesseract --version 2>&1 | head -1))"
else
    echo "- (optional for OCR; brew install tesseract / apt install tesseract-ocr)"
fi

echo ""
echo "=== Done ==="
