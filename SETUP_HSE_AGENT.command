#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -x backend/venv/bin/python ]]; then
  if command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv backend/venv
  else
    echo 'Install Python 3.12, or create backend/venv with your supported Python installation first.'
    exit 1
  fi
fi
command -v node >/dev/null 2>&1 || { echo 'Node.js is required.'; exit 1; }
command -v npm >/dev/null 2>&1 || { echo 'npm is required.'; exit 1; }
backend/venv/bin/python -m pip install -r backend/requirements.txt
cd frontend
npm ci --no-audit --no-fund
NEXT_TELEMETRY_DISABLED=1 npm run build
echo 'Mac setup complete. Run START_HSE_AGENT.command. Existing data is preserved.'
