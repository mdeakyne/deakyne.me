#!/bin/bash
# Setup script for deakyne.me services
# Run this script with sudo

set -e

echo "🚀 Setting up deakyne.me services..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run with sudo: sudo bash setup-services.sh"
    exit 1
fi

PROJECT_DIR="/Users/matt/Development/deakyne.me"
SERVICES_DIR="$PROJECT_DIR/services"

# Get the actual user (not root when using sudo)
ACTUAL_USER="${SUDO_USER:-$(whoami)}"
echo "📝 Setting up services for user: $ACTUAL_USER"

# Stop any running services first
echo "🛑 Stopping any existing services..."
launchctl bootout system/com.cloudflare.cloudflared 2>/dev/null || true
launchctl bootout gui/$(id -u $ACTUAL_USER)/com.deakyne.backend 2>/dev/null || true
launchctl bootout gui/$(id -u $ACTUAL_USER)/com.deakyne.frontend 2>/dev/null || true

# Build Next.js for production
echo "🔨 Building Next.js frontend..."
cd "$PROJECT_DIR"
sudo -u $ACTUAL_USER npm run build

# Install cloudflared service (runs as root/system)
echo "☁️  Installing Cloudflare Tunnel service..."
cp "$SERVICES_DIR/com.cloudflare.cloudflared.plist" /Library/LaunchDaemons/
chown root:wheel /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
chmod 644 /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
launchctl bootstrap system /Library/LaunchDaemons/com.cloudflare.cloudflared.plist
launchctl enable system/com.cloudflare.cloudflared

# Install backend service (runs as user)
echo "🐍 Installing FastAPI backend service..."
cp "$SERVICES_DIR/com.deakyne.backend.plist" /Library/LaunchAgents/
chown root:wheel /Library/LaunchAgents/com.deakyne.backend.plist
chmod 644 /Library/LaunchAgents/com.deakyne.backend.plist
sudo -u $ACTUAL_USER launchctl bootstrap gui/$(id -u $ACTUAL_USER) /Library/LaunchAgents/com.deakyne.backend.plist
sudo -u $ACTUAL_USER launchctl enable gui/$(id -u $ACTUAL_USER)/com.deakyne.backend

# Install frontend service (runs as user)
echo "⚛️  Installing Next.js frontend service..."
cp "$SERVICES_DIR/com.deakyne.frontend.plist" /Library/LaunchAgents/
chown root:wheel /Library/LaunchAgents/com.deakyne.frontend.plist
chmod 644 /Library/LaunchAgents/com.deakyne.frontend.plist
sudo -u $ACTUAL_USER launchctl bootstrap gui/$(id -u $ACTUAL_USER) /Library/LaunchAgents/com.deakyne.frontend.plist
sudo -u $ACTUAL_USER launchctl enable gui/$(id -u $ACTUAL_USER)/com.deakyne.frontend

# Start services
echo "▶️  Starting services..."
launchctl kickstart system/com.cloudflare.cloudflared
sudo -u $ACTUAL_USER launchctl kickstart gui/$(id -u $ACTUAL_USER)/com.deakyne.backend
sudo -u $ACTUAL_USER launchctl kickstart gui/$(id -u $ACTUAL_USER)/com.deakyne.frontend

echo ""
echo "✅ Services installed and started!"
echo ""
echo "📊 Service Status:"
launchctl print system/com.cloudflare.cloudflared | grep -A 2 "state ="
sudo -u $ACTUAL_USER launchctl print gui/$(id -u $ACTUAL_USER)/com.deakyne.backend | grep -A 2 "state ="
sudo -u $ACTUAL_USER launchctl print gui/$(id -u $ACTUAL_USER)/com.deakyne.frontend | grep -A 2 "state ="
echo ""
echo "📝 Logs are available at:"
echo "  - Cloudflared: $PROJECT_DIR/logs/cloudflared.log"
echo "  - Backend: $PROJECT_DIR/logs/backend.log"
echo "  - Frontend: $PROJECT_DIR/logs/frontend.log"
echo ""
echo "🔧 Useful commands:"
echo "  - Check status: sudo launchctl list | grep -E 'cloudflare|deakyne'"
echo "  - View logs: tail -f $PROJECT_DIR/logs/*.log"
echo "  - Restart services: sudo bash $SERVICES_DIR/restart-services.sh"
