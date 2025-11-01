#!/usr/bin/env bash
set -euo pipefail
echo "=== 0) Where am I? ==="
pwd

echo
echo "=== 1) Python in venv ==="
if [ -d ".venv" ]; then
  source .venv/bin/activate
  echo "python: $(which python)"
  python --version
else
  echo "No .venv dir found"
fi

echo
echo "=== 2) Project tree (top level) ==="
ls -la

echo
echo "=== 3) Project tree (packages) ==="
for d in tg providers services formatting; do
  if [ -d "$d" ]; then
    echo "--- $d ---"
    ls -la "$d"
  else
    echo "--- $d (missing) ---"
  fi
done

echo
echo "=== 4) app.py (first 80 lines) ==="
nl -ba app.py | sed -n '1,80p' || true

echo
echo "=== 5) Check for wrong imports in app.py ==="
echo "Looking for 'from tg import Update' (this is WRONG):"
grep -n "from tg import Update" app.py || true
echo "Looking for 'from telegram import Update' (this is RIGHT):"
grep -n "from telegram import Update" app.py || true
echo "Looking for handlers/jobs imports:"
grep -nE "from (telegram|tg)\.(handlers|jobs)" app.py || true

echo
echo "=== 6) Show tg/__init__.py, handlers.py, jobs.py headers ==="
if [ -d tg ]; then
  echo "--- tg/__init__.py ---"
  nl -ba tg/__init__.py | sed -n '1,60p' || true
  echo "--- tg/handlers.py ---"
  nl -ba tg/handlers.py | sed -n '1,80p' || true
  echo "--- tg/jobs.py ---"
  nl -ba tg/jobs.py | sed -n '1,80p' || true
fi

echo
echo "=== 7) Providers fastforex header (first 40 lines) ==="
if [ -f providers/fastforex.py ]; then
  nl -ba providers/fastforex.py | sed -n '1,40p' || true
fi

echo
echo "=== 8) Grep for any lingering imports ==="
echo "-- anything importing local 'telegram.' (should be none) --"
grep -R "from telegram\." -n . | grep -v "/site-packages/" || true
grep -R "import telegram\." -n . | grep -v "/site-packages/" || true
echo "-- anything importing 'from tg import Update' (should be none) --"
grep -R "from tg import Update" -n . || true

echo
echo "=== 9) Quick import test inside Python ==="
python - <<'PY'
print("Python quick import test:")
try:
    from telegram import Update
    print("OK: from telegram import Update")
except Exception as e:
    print("FAIL: from telegram import Update ->", e)

try:
    import tg
    print("OK: local package 'tg' imports")
except Exception as e:
    print("FAIL: import tg ->", e)

try:
    from tg.handlers import start_cmd
    print("OK: from tg.handlers import start_cmd")
except Exception as e:
    print("FAIL: from tg.handlers import start_cmd ->", e)
PY

echo
echo "=== 10) Done ==="
