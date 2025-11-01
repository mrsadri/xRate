#!/bin/bash
# =====================================================
# XRate Bot - Server Deployment Script
# =====================================================
#
# This script helps deploy the XRate bot to a remote server.
# It sets up the service user, installs dependencies, and configures
# either systemd or supervisor for process management.
#
# Usage:
#   ./deploy/deploy.sh [systemd|supervisor]
#

set -euo pipefail

# Configuration
PROJECT_NAME="xrate"
INSTALL_DIR="/opt/${PROJECT_NAME}"
SERVICE_USER="${PROJECT_NAME}"
LOG_DIR="${INSTALL_DIR}/logs"
DATA_DIR="${INSTALL_DIR}/data"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (use sudo)"
    exit 1
fi

# Detect process manager
PROCESS_MANAGER="${1:-systemd}"
if [[ ! "$PROCESS_MANAGER" =~ ^(systemd|supervisor)$ ]]; then
    log_error "Invalid process manager: $PROCESS_MANAGER"
    log_info "Usage: $0 [systemd|supervisor]"
    exit 1
fi

log_info "Deploying XRate bot with $PROCESS_MANAGER..."

# Step 1: Create service user
log_info "Creating service user: $SERVICE_USER"
if ! id "$SERVICE_USER" &>/dev/null; then
    useradd -r -s /bin/bash -d "$INSTALL_DIR" "$SERVICE_USER"
    log_info "User $SERVICE_USER created"
else
    log_info "User $SERVICE_USER already exists"
fi

# Step 2: Create directories
log_info "Creating directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$LOG_DIR"
mkdir -p "$DATA_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"

# Step 3: Copy project files
log_info "Copying project files to $INSTALL_DIR..."
# This assumes you're running from project root
if [ ! -f "pyproject.toml" ]; then
    log_error "Please run this script from the project root directory"
    exit 1
fi

rsync -av --exclude='.git' --exclude='.venv' --exclude='__pycache__' \
      --exclude='*.pyc' --exclude='.pytest_cache' --exclude='bot.log' \
      --exclude='data/*.json' --exclude='.env' \
      ./ "$INSTALL_DIR/"

# Step 4: Create virtual environment
log_info "Setting up Python virtual environment..."
cd "$INSTALL_DIR"
sudo -u "$SERVICE_USER" python3 -m venv .venv
sudo -u "$SERVICE_USER" .venv/bin/pip install --upgrade pip setuptools wheel
sudo -u "$SERVICE_USER" .venv/bin/pip install -e ".[dev]"

# Step 5: Create .env file if it doesn't exist
if [ ! -f "$INSTALL_DIR/.env" ]; then
    log_warn ".env file not found. Please create it:"
    log_info "  cp $INSTALL_DIR/.env.example $INSTALL_DIR/.env"
    log_info "  nano $INSTALL_DIR/.env"
    log_info "  # Then edit with your API keys and settings"
    log_warn "You must create .env before starting the service!"
else
    log_info ".env file found"
    chown "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR/.env"
fi

# Step 6: Configure process manager
log_info "Configuring $PROCESS_MANAGER..."

if [ "$PROCESS_MANAGER" == "systemd" ]; then
    # Install systemd service
    SERVICE_FILE="/etc/systemd/system/${PROJECT_NAME}.service"
    log_info "Installing systemd service: $SERVICE_FILE"
    
    # Copy and customize service file
    cp "$INSTALL_DIR/deploy/xrate.service" "$SERVICE_FILE"
    sed -i "s|/opt/xrate|$INSTALL_DIR|g" "$SERVICE_FILE"
    sed -i "s|User=xrate|User=$SERVICE_USER|g" "$SERVICE_FILE"
    sed -i "s|Group=xrate|Group=$SERVICE_USER|g" "$SERVICE_FILE"
    
    systemctl daemon-reload
    systemctl enable "$PROJECT_NAME"
    log_info "Systemd service installed and enabled"
    
elif [ "$PROCESS_MANAGER" == "supervisor" ]; then
    # Install supervisor config
    if ! command -v supervisorctl &> /dev/null; then
        log_error "supervisor is not installed. Install it with:"
        log_info "  apt-get install supervisor  # Debian/Ubuntu"
        log_info "  yum install supervisor       # CentOS/RHEL"
        exit 1
    fi
    
    CONFIG_FILE="/etc/supervisor/conf.d/${PROJECT_NAME}.conf"
    log_info "Installing supervisor config: $CONFIG_FILE"
    
    # Copy and customize config file
    cp "$INSTALL_DIR/deploy/supervisor-xrate.conf" "$CONFIG_FILE"
    sed -i "s|/opt/xrate|$INSTALL_DIR|g" "$CONFIG_FILE"
    sed -i "s|user=xrate|user=$SERVICE_USER|g" "$CONFIG_FILE"
    
    supervisorctl reread
    supervisorctl update
    log_info "Supervisor config installed"
fi

# Step 7: Set permissions
log_info "Setting file permissions..."
chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/scripts/run.sh"

log_info ""
log_info "============================================"
log_info "Deployment completed successfully!"
log_info "============================================"
log_info ""
log_info "Next steps:"
log_info ""
if [ ! -f "$INSTALL_DIR/.env" ]; then
    log_warn "1. Create .env file with your configuration:"
    log_info "   sudo -u $SERVICE_USER nano $INSTALL_DIR/.env"
    log_info ""
fi

if [ "$PROCESS_MANAGER" == "systemd" ]; then
    log_info "2. Start the service:"
    log_info "   sudo systemctl start $PROJECT_NAME"
    log_info ""
    log_info "3. Check status:"
    log_info "   sudo systemctl status $PROJECT_NAME"
    log_info ""
    log_info "4. View logs:"
    log_info "   sudo journalctl -u $PROJECT_NAME -f"
elif [ "$PROCESS_MANAGER" == "supervisor" ]; then
    log_info "2. Start the service:"
    log_info "   sudo supervisorctl start $PROJECT_NAME"
    log_info ""
    log_info "3. Check status:"
    log_info "   sudo supervisorctl status $PROJECT_NAME"
    log_info ""
    log_info "4. View logs:"
    log_info "   tail -f $LOG_DIR/xrate.log"
fi
log_info ""
log_info "For more information, see:"
log_info "  $INSTALL_DIR/README.md"
log_info ""

