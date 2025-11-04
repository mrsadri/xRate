# 🚀 How to Run XRate Project

## Method 1: Using Python Module (Recommended)

```bash
# 1. Navigate to project directory
cd /Users/masih/Downloads/xrate

# 2. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -e .

# 4. Setup environment file
cp .env.example .env
# Edit .env with your actual API keys

# 5. Run the bot
python -m xrate
```

## Method 2: Using Run Script

```bash
# Make script executable (first time only)
chmod +x scripts/run.sh

# Run the script
./scripts/run.sh
```

The script will:
- Automatically create virtual environment if needed
- Install dependencies
- Check for .env file
- Start the bot

## Method 3: Run in Background (Production)

```bash
# Run in background with logging
nohup python -m xrate > bot.log 2>&1 &

# View logs
tail -f bot.log

# Stop the bot
pkill -f "python -m xrate"
```

## Required Environment Variables

Before running, make sure your `.env` file has:

```bash
# Required
BOT_TOKEN=your_telegram_bot_token
CHANNEL_ID=@your_channel
ADMIN_USERNAME=YourUsername

# Optional (for fallback)
NAVASAN_API_KEY=your_navasan_key

# Optional (for AI analysis)
AVALAI_KEY=your_avalai_key

# Optional (for test channel)
TEST_CHANNEL_ID=@your_test_channel
```

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate
pip install -e .
```

### Missing .env file
```bash
cp .env.example .env
# Edit .env with your keys
```

### Port Already in Use
```bash
# Check if bot is already running
ps aux | grep "python -m xrate"
# Kill existing process
pkill -f "python -m xrate"
```

## Verify Installation

```bash
# Check Python version (should be 3.9+)
python3 --version

# Check if package is installed
pip show xrate

# Test imports
python3 -c "from xrate.config import settings; print('✅ Setup OK')"
```

