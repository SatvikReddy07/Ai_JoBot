#!/bin/bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$PROJECT_ROOT/backend/venv/bin/python"
if [[ ! -x "$PYTHON" ]]; then
  echo 'Mac virtual environment missing. Run SETUP_HSE_AGENT.command first.'
  exit 1
fi
exec "$PYTHON" "$PROJECT_ROOT/scripts/manage_local_app.py" start "$@"
