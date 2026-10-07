#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
if [[ ! -x .venv/bin/uvicorn ]]; then
  echo "Python environment missing. Follow the setup steps in README.md." >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  cp .env.example .env
fi
exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port "${PORT:-8000}" --env-file .env
