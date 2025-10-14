#!/bin/bash
# Check status of all deakyne.me services

ACTUAL_USER="${USER}"
if [ -n "$SUDO_USER" ]; then
    ACTUAL_USER="$SUDO_USER"
fi

echo "📊 Deakyne.me Service Status"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Cloudflare Tunnel
echo "☁️  Cloudflare Tunnel (system):"
if sudo launchctl print system/com.cloudflare.cloudflared 2>/dev/null | grep -q "state = running"; then
    echo "   ✅ Running"
    sudo launchctl print system/com.cloudflare.cloudflared | grep "pid ="
else
    echo "   ❌ Not running"
fi
echo ""

# Backend
echo "🐍 Backend API (user: $ACTUAL_USER):"
if launchctl print gui/$(id -u)/com.deakyne.backend 2>/dev/null | grep -q "state = running"; then
    echo "   ✅ Running"
    launchctl print gui/$(id -u)/com.deakyne.backend | grep "pid ="
    echo "   🌐 http://localhost:8000"
else
    echo "   ❌ Not running"
fi
echo ""

# Frontend
echo "⚛️  Frontend (user: $ACTUAL_USER):"
if launchctl print gui/$(id -u)/com.deakyne.frontend 2>/dev/null | grep -q "state = running"; then
    echo "   ✅ Running"
    launchctl print gui/$(id -u)/com.deakyne.frontend | grep "pid ="
    echo "   🌐 http://localhost:3000"
else
    echo "   ❌ Not running"
fi
echo ""

# Port checks
echo "🔌 Port Status:"
lsof -nP -iTCP:3000 -sTCP:LISTEN 2>/dev/null && echo "" || echo "   Port 3000: Not listening"
lsof -nP -iTCP:8000 -sTCP:LISTEN 2>/dev/null && echo "" || echo "   Port 8000: Not listening"
echo ""

# Recent log entries
echo "📝 Recent Logs:"
if [ -f "/Users/matt/Development/deakyne.me/logs/cloudflared.log" ]; then
    echo "   Cloudflare (last line):"
    tail -1 /Users/matt/Development/deakyne.me/logs/cloudflared.log | sed 's/^/     /'
fi
if [ -f "/Users/matt/Development/deakyne.me/logs/backend.log" ]; then
    echo "   Backend (last line):"
    tail -1 /Users/matt/Development/deakyne.me/logs/backend.log | sed 's/^/     /'
fi
if [ -f "/Users/matt/Development/deakyne.me/logs/frontend.log" ]; then
    echo "   Frontend (last line):"
    tail -1 /Users/matt/Development/deakyne.me/logs/frontend.log | sed 's/^/     /'
fi
