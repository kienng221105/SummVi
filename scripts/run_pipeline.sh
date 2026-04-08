#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=apps/backend:.
python -m ml.pipelines.data_pipeline
python -m warehouse.etl
