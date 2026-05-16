#!/bin/bash
# Raspberry Pi Installation Script
# Run this on your Raspberry Pi to set up the network monitor

set -e

echo "=========================================="
echo "Network Monitor - Raspberry Pi Setup"
echo "=========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    echo "Warning: This script is designed for Raspberry Pi (Linux)"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo apt-get update

# Install dependencies
echo "Installing dependencies..."
sudo apt-get install -y python3-pip awscli

# Install Python packages
echo "Installing Python packages..."
pip3 install boto3 speedtest-cli

# Create data directory
DATA_DIR="/home/$USER/network_monitor_data"
echo "Creating data directory: $DATA_DIR"
mkdir -p "$DATA_DIR"

# Copy files to home directory
INSTALL_DIR="/home/$USER/network_monitor"
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

if [ -f "network_monitor.py" ]; then
    cp network_monitor.py "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/network_monitor.py"
    echo "Copied network_monitor.py"
fi

if [ -f "config.json" ]; then
    cp config.json "$INSTALL_DIR/"
    echo "Copied config.json"
fi

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Configure AWS credentials:"
echo "   aws configure"
echo "   (Enter the Access Key and Secret Key from AWS setup)"
echo ""
echo "2. Edit configuration:"
echo "   nano $INSTALL_DIR/config.json"
echo "   (Update s3_bucket, ping_targets, etc.)"
echo ""
echo "3. Test the monitor:"
echo "   cd $INSTALL_DIR"
echo "   ./network_monitor.py"
echo ""
echo "4. Set up cron job for automatic monitoring:"
echo "   crontab -e"
echo "   Add this line:"
echo "   */5 * * * * /usr/bin/python3 $INSTALL_DIR/network_monitor.py >> /home/$USER/monitor.log 2>&1"
echo ""
echo "5. View logs:"
echo "   tail -f /home/$USER/monitor.log"
echo ""
echo "=========================================="
