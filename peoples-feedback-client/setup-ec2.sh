#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ONE-TIME EC2 Setup — Peoples Feedback Client
#
# Instance: i-0e448dd106cf9aeed (AWS 023036697290)
#
# What this does:
#   1. Removes old portalpro application
#   2. Installs Nginx (if not present)
#   3. Configures Nginx to serve the peoples-feedback client
#   4. Sets up /var/www/peoples-feedback directory
#   5. Configures API reverse proxy to backend
#
# Usage: SSH into EC2, then:
#   curl -sL https://raw.githubusercontent.com/rameshreddygovindu5-bit/news-app/main/peoples-feedback-client/setup-ec2.sh | sudo bash
#   OR:
#   chmod +x setup-ec2.sh && sudo ./setup-ec2.sh
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[SETUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# ── Config ──
DEPLOY_DIR="/var/www/peoples-feedback"
API_BACKEND="http://127.0.0.1:8005"  # Change if backend is on different server/port

log "═══════════════════════════════════════"
log "  Peoples Feedback — EC2 Setup"
log "  Instance: i-0e448dd106cf9aeed"
log "═══════════════════════════════════════"

# ── Step 1: Remove old portalpro ──
log "Step 1: Removing old portalpro application..."
# Stop any portalpro services
systemctl stop portalpro 2>/dev/null || true
systemctl disable portalpro 2>/dev/null || true
rm -f /etc/systemd/system/portalpro.service

# Remove portalpro nginx config
rm -f /etc/nginx/sites-enabled/portalpro* 2>/dev/null || true
rm -f /etc/nginx/sites-available/portalpro* 2>/dev/null || true
rm -f /etc/nginx/conf.d/portalpro* 2>/dev/null || true

# Remove portalpro files
rm -rf /var/www/portalpro 2>/dev/null || true
rm -rf /opt/portalpro 2>/dev/null || true
rm -rf /home/*/portalpro 2>/dev/null || true

# Kill any portalpro processes
pkill -f portalpro 2>/dev/null || true

log "  ✓ Portalpro removed"

# ── Step 2: Install Nginx ──
log "Step 2: Installing/updating Nginx..."
apt-get update -qq
apt-get install -y -qq nginx curl
systemctl enable nginx
log "  ✓ Nginx installed"

# ── Step 3: Create deployment directory ──
log "Step 3: Setting up deployment directory..."
mkdir -p $DEPLOY_DIR
# Create a placeholder index.html
cat > $DEPLOY_DIR/index.html << 'HTML'
<!DOCTYPE html>
<html><head><title>Peoples Feedback</title>
<style>body{font-family:system-ui;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#0f172a;color:#fff}
.c{text-align:center}h1{font-size:2rem;margin-bottom:0.5rem}p{color:#94a3b8;font-size:1rem}</style>
</head><body><div class="c"><h1>🚀 Peoples Feedback</h1><p>Deploying... Push to GitHub to trigger auto-deploy.</p></div></body></html>
HTML
chown -R www-data:www-data $DEPLOY_DIR 2>/dev/null || true
log "  ✓ $DEPLOY_DIR created"

# ── Step 4: Configure Nginx ──
log "Step 4: Configuring Nginx..."

# Remove default site
rm -f /etc/nginx/sites-enabled/default

cat > /etc/nginx/sites-available/peoples-feedback << NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root $DEPLOY_DIR;
    index index.html;

    # SPA client-side routing — all paths serve index.html
    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # API reverse proxy to backend (same instance or remote)
    location /api/ {
        proxy_pass $API_BACKEND;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
    }

    # Static asset caching (JS/CSS have hashed names — cache forever)
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2|woff|ttf)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
}
NGINX

ln -sf /etc/nginx/sites-available/peoples-feedback /etc/nginx/sites-enabled/

# Test and reload
nginx -t
systemctl reload nginx
log "  ✓ Nginx configured"

# ── Step 5: Open firewall ──
log "Step 5: Configuring firewall..."
ufw allow 80/tcp 2>/dev/null || true
ufw allow 443/tcp 2>/dev/null || true
ufw allow 22/tcp 2>/dev/null || true
log "  ✓ Ports 80, 443, 22 open"

# ── Done ──
PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "YOUR_EC2_IP")

echo ""
log "═══════════════════════════════════════════════════════"
log "  ✅ Setup complete!"
log ""
log "  Website: http://$PUBLIC_IP"
log "  Files:   $DEPLOY_DIR"
log "  Nginx:   /etc/nginx/sites-available/peoples-feedback"
log ""
log "  Next: Add these GitHub Secrets:"
log "    EC2_HOST     = $PUBLIC_IP"
log "    EC2_USER     = $(whoami)"
log "    EC2_SSH_KEY  = (paste your private .pem key)"
log "    VITE_API_URL = $API_BACKEND"
log ""
log "  Then push to main branch → auto-deploys!"
log "═══════════════════════════════════════════════════════"
