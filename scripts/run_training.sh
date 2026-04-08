#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=apps/backend:.
export HF_HOME="${HF_HOME:-./data/models/cache}"
python -m ml.training.train
