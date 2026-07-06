#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# Compresso — Launch Script
# ─────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="${SCRIPT_DIR}/venv"

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "🔨 Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"
    echo "📦 Installing dependencies..."
    pip install --upgrade pip -q
    pip install -r "$SCRIPT_DIR/requirements.txt" -q
    echo "✅ Installation complete!"
else
    source "$VENV_DIR/bin/activate"
fi

# Ensure project root is on PYTHONPATH
export PYTHONPATH="${SCRIPT_DIR}:${PYTHONPATH:-}"

# Run the application
echo "Starting Compresso..."
python "$SCRIPT_DIR/main.py" "$@"