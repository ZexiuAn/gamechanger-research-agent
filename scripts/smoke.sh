#!/usr/bin/env bash
# 轻量冒烟：依赖已安装的 .venv
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
python - <<'PY'
from app.branding import COMPANY_FULL, PRODUCT_NAME
assert "易动纷享" in COMPANY_FULL
assert PRODUCT_NAME == "易动调研助手"
print("branding ok:", PRODUCT_NAME)
PY
pytest tests/ -q
echo "smoke ok"
