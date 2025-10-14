#!/bin/bash
# Restart all deakyne.me services
# Run with sudo

if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run with sudo: sudo bash restart-services.sh"
    exit 1
fi

ACTUAL_USER="${SUDO_USER:-$(whoami)}"

echo "🔄 Restarting deakyne.me services..."

echo "  - Cloudflare Tunnel..."
launchctl kickstart -k system/com.cloudflare.cloudflared

echo "  - Backend API..."
sudo -u $ACTUAL_USER launchctl kickstart -k gui/$(id -u $ACTUAL_USER)/com.deakyne.backend

echo "  - Frontend..."
sudo -u $ACTUAL_USER launchctl kickstart -k gui/$(id -u $ACTUAL_USER)/com.deakyne.frontend

echo "✅ All services restarted!"
