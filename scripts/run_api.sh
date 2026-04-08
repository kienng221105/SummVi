#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=apps/backend:.
export HF_HOME="${HF_HOME:-./data/models/cache}"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
