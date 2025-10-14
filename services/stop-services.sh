#!/bin/bash
# Stop all deakyne.me services
# Run with sudo

if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run with sudo: sudo bash stop-services.sh"
    exit 1
fi

ACTUAL_USER="${SUDO_USER:-$(whoami)}"

echo "🛑 Stopping deakyne.me services..."

echo "  - Cloudflare Tunnel..."
launchctl bootout system/com.cloudflare.cloudflared 2>/dev/null || echo "    (not running)"

echo "  - Backend API..."
sudo -u $ACTUAL_USER launchctl bootout gui/$(id -u $ACTUAL_USER)/com.deakyne.backend 2>/dev/null || echo "    (not running)"

echo "  - Frontend..."
sudo -u $ACTUAL_USER launchctl bootout gui/$(id -u $ACTUAL_USER)/com.deakyne.frontend 2>/dev/null || echo "    (not running)"

echo "✅ All services stopped!"
