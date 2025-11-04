#!/bin/bash
# =====================================================
# XRate Bot Stop Script
# =====================================================

# Move to project root
cd "$(dirname "$0")/.."

echo "🛑 Stopping XRate bot..."

# Method 1: Try using PID file (most reliable)
if [ -f "data/bot.pid" ]; then
    PID=$(cat data/bot.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Found PID file: $PID"
        kill $PID
        rm data/bot.pid
        echo "✅ Bot stopped (PID: $PID)"
        exit 0
    else
        echo "⚠️ PID file exists but process not running. Removing stale PID file..."
        rm data/bot.pid
    fi
fi

# Method 2: Find and kill by process name
PIDS=$(ps aux | grep -i "python.*xrate" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "ℹ️ No running bot process found"
    exit 0
fi

for PID in $PIDS; do
    echo "Stopping process: $PID"
    kill $PID 2>/dev/null
done

echo "✅ Bot stopped"
exit 0

