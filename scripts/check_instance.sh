#!/bin/bash
# scripts/check_instance.sh
# Quick script to check if only one bot instance is running

echo "=== XRate Bot Instance Check ==="
echo ""

# Method 1: Check systemd service
echo "1. Systemd Service Status:"
if systemctl is-active --quiet xrate 2>/dev/null; then
    STATUS=$(systemctl status xrate --no-pager | grep "Active:" | awk '{print $2, $3}')
    PID=$(systemctl status xrate --no-pager | grep "Main PID:" | awk '{print $3}')
    echo "   ✅ Service is active: $STATUS"
    echo "   📌 Main PID: $PID"
else
    echo "   ❌ Service is NOT running"
fi
echo ""

# Method 2: Check PID file
echo "2. PID File Check:"
PID_FILE="/opt/xrate/data/bot.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE" 2>/dev/null)
    if [ -n "$PID" ]; then
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "   ✅ PID file exists: $PID (process is running)"
        else
            echo "   ⚠️  PID file exists: $PID (but process NOT running - stale file)"
        fi
    else
        echo "   ⚠️  PID file is empty"
    fi
else
    echo "   ⚠️  PID file not found: $PID_FILE"
fi
echo ""

# Method 3: Count all Python processes
echo "3. Python Process Count:"
PROCESSES=$(ps aux | grep "python.*xrate" | grep -v grep | grep -v "check_instance")
COUNT=$(echo "$PROCESSES" | wc -l)
if [ -z "$PROCESSES" ]; then
    COUNT=0
fi

if [ "$COUNT" -eq 0 ]; then
    echo "   ❌ No xrate processes found"
elif [ "$COUNT" -eq 1 ]; then
    echo "   ✅ Exactly ONE process running (correct)"
    echo "   Details:"
    echo "$PROCESSES" | awk '{print "      PID: " $2 ", CMD: " $11 " " $12 " " $13}'
elif [ "$COUNT" -gt 1 ]; then
    echo "   ⚠️  WARNING: Multiple processes detected ($COUNT processes)"
    echo "   Details:"
    echo "$PROCESSES" | awk '{print "      PID: " $2 ", CMD: " $11 " " $12 " " $13}'
    echo ""
    echo "   ⚠️  ACTION REQUIRED: Multiple instances detected!"
    echo "   Run these commands to fix:"
    echo "      sudo systemctl stop xrate"
    echo "      pkill -f 'python.*xrate'"
    echo "      sudo systemctl start xrate"
fi
echo ""

# Method 4: Check for conflicts
echo "4. Conflict Detection:"
TELEGRAM_CONFLICT=$(journalctl -u xrate --no-pager -n 50 2>/dev/null | grep -i "conflict\|terminated by other" | tail -1)
if [ -n "$TELEGRAM_CONFLICT" ]; then
    echo "   ⚠️  Telegram conflict detected in logs!"
    echo "   $TELEGRAM_CONFLICT"
    echo "   This indicates multiple bot instances trying to use the same token."
else
    echo "   ✅ No conflicts detected in recent logs"
fi
echo ""

# Summary
echo "=== Summary ==="
if [ "$COUNT" -eq 1 ] && systemctl is-active --quiet xrate 2>/dev/null; then
    echo "✅ Bot is running correctly with ONE instance"
    exit 0
elif [ "$COUNT" -eq 0 ]; then
    echo "❌ Bot is NOT running"
    exit 1
else
    echo "⚠️  Multiple instances or inconsistencies detected"
    exit 2
fi

