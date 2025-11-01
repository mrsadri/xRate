#!/bin/bash
# =====================================================
# Telegram EUR→USD Bot Runner
# Location: /Users/masih/Downloads/xrate/run.sh
# Author: Masih Sadri
# =====================================================

# Move to project root (one level up from scripts/)
cd "$(dirname "$0")/.."

# 1️⃣ Activate virtual environment
if [ -d ".venv" ]; then
  echo "🔹 Activating virtual environment..."
  source .venv/bin/activate
else
  echo "⚠️ No virtual environment found. Creating one..."
  python3 -m venv .venv
  source .venv/bin/activate
  echo "📦 Upgrading pip, setuptools, and wheel..."
  python3 -m pip install --upgrade pip setuptools wheel >/dev/null 2>&1
  echo "📦 Installing dependencies..."
  pip3 install -e ".[dev]"
fi

# 2️⃣ Upgrade pip quietly (recommended)
python3 -m pip install --upgrade pip >/dev/null 2>&1

# 3️⃣ Check if .env exists
if [ ! -f ".env" ]; then
  echo "🚫 Missing .env file! Please create one with:"
  echo "BOT_TOKEN=..."
  echo "FASTFOREX_KEY=..."
  echo "CHANNEL_ID=@yourchannel"
  exit 1
fi

# 4️⃣ Run your Telegram bot
echo "🚀 Starting Telegram bot..."
python3 -m xrate

# 5️⃣ When finished
echo "🛑 Bot stopped."

# If you want the bot to keep running after you close the terminal:
# nohup ./run.sh > bot.log 2>&1 &
# Check logs:
# tail -f bot.log
# Stop it:
# pkill -f app.py
