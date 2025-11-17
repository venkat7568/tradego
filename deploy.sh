#!/bin/bash

# TradeGo Auto-Deploy Script for Ubuntu VPS
# This script sets up the complete trading system on Ubuntu

set -e  # Exit on error

echo "======================================"
echo "TradeGo Auto-Deploy Script"
echo "======================================"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
   echo "⚠️  Please do NOT run as root. Run as regular user."
   exit 1
fi

# 1. Update system
echo "Step 1: Updating system packages..."
sudo apt update && sudo apt upgrade -y

# 2. Install Python 3.11
echo ""
echo "Step 2: Installing Python 3.11..."
sudo apt install -y python3.11 python3.11-venv python3-pip

# 3. Install system dependencies
echo ""
echo "Step 3: Installing system dependencies..."
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev

# 4. Create virtual environment
echo ""
echo "Step 4: Creating virtual environment..."
python3.11 -m venv venv

# 5. Activate and install Python packages
echo ""
echo "Step 5: Installing Python packages..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 6. Create data directory
echo ""
echo "Step 6: Creating data directory..."
mkdir -p data

# 7. Test the system
echo ""
echo "Step 7: Testing P&L Engine..."
python pnl_engine.py

# 8. Create systemd service
echo ""
echo "Step 8: Creating systemd service..."

SERVICE_FILE="/etc/systemd/system/tradego.service"

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=TradeGo Auto Trading System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/venv/bin/python $(pwd)/orchestrator.py
Restart=always
RestartSec=10
StandardOutput=append:/var/log/tradego/output.log
StandardError=append:/var/log/tradego/error.log

# Environment variables (edit these)
# Environment="UPSTOX_API_KEY=your_key"
# Environment="UPSTOX_API_SECRET=your_secret"
# Environment="UPSTOX_ACCESS_TOKEN=your_token"

[Install]
WantedBy=multi-user.target
EOF

# 9. Create log directory
echo ""
echo "Step 9: Creating log directory..."
sudo mkdir -p /var/log/tradego
sudo chown $USER:$USER /var/log/tradego

# 10. Reload systemd and enable service
echo ""
echo "Step 10: Configuring systemd..."
sudo systemctl daemon-reload
sudo systemctl enable tradego

# 11. Configure firewall (if needed)
echo ""
echo "Step 11: Configuring firewall..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 5000/tcp  # For dashboard (if we add it)
    echo "  ✓ Firewall configured"
else
    echo "  ⓘ UFW not installed, skipping firewall configuration"
fi

# Done!
echo ""
echo "======================================"
echo "✅ Deployment Complete!"
echo "======================================"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the service:"
echo "   sudo systemctl start tradego"
echo ""
echo "2. Check status:"
echo "   sudo systemctl status tradego"
echo ""
echo "3. View logs:"
echo "   tail -f /var/log/tradego/output.log"
echo ""
echo "4. Stop the service:"
echo "   sudo systemctl stop tradego"
echo ""
echo "5. Restart the service:"
echo "   sudo systemctl restart tradego"
echo ""
echo "The system will:"
echo "  • Auto-start on server reboot"
echo "  • Auto-restart if it crashes"
echo "  • Trade during market hours (9:15 AM - 3:30 PM IST)"
echo "  • Log everything to /var/log/tradego/"
echo ""
echo "Database: $(pwd)/data/tradego.db"
echo "Logs: /var/log/tradego/"
echo ""
