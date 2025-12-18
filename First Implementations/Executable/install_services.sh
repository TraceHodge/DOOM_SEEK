#!/bin/bash

echo "=== DOOMSEEK Service Installation ==="
echo ""

# Check if running on Raspberry Pi
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "WARNING: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Get current directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Check if start_all.sh exists
if [ ! -f "$SCRIPT_DIR/start_all.sh" ]; then
    echo "ERROR: start_all.sh not found in $SCRIPT_DIR"
    exit 1
fi

# Make start scripts executable
echo "Making scripts executable..."
chmod +x "$SCRIPT_DIR/start_all.sh"
chmod +x "$SCRIPT_DIR/stop_all.sh"

# Update the service file with actual path
echo "Updating service file with current directory: $SCRIPT_DIR"
sed -i "s|/home/pi/claude_ds|$SCRIPT_DIR|g" "$SCRIPT_DIR/doomseek.service"

# Update User in service file to current user
CURRENT_USER=$(whoami)
sed -i "s|User=pi|User=$CURRENT_USER|g" "$SCRIPT_DIR/doomseek.service"

# Copy service file to systemd
echo "Installing systemd service..."
sudo cp "$SCRIPT_DIR/doomseek.service" /etc/systemd/system/

# Reload systemd
echo "Reloading systemd daemon..."
sudo systemctl daemon-reload

# Enable the service
echo "Enabling DOOMSEEK service to start on boot..."
sudo systemctl enable doomseek.service

echo ""
echo "==================================="
echo "✓ Installation complete!"
echo "==================================="
echo ""
echo "Useful commands:"
echo "  Start service:   sudo systemctl start doomseek"
echo "  Stop service:    sudo systemctl stop doomseek"
echo "  Check status:    sudo systemctl status doomseek"
echo "  View logs:       sudo journalctl -u doomseek -f"
echo "  Disable auto-start: sudo systemctl disable doomseek"
echo ""
echo "The service will automatically start on next boot!"
echo ""
