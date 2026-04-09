#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# ONE-TIME EC2 Setup — Peoples Feedback Client (Amazon Linux 2023 & Ubuntu)
# ═══════════════════════════════════════════════════════════════

set -e

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
log() { echo -e "${GREEN}[SETUP]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }

# ── Config ──
DEPLOY_DIR="/var/www/peoples-feedback"
API_BACKEND="http://127.0.0.1:8005"

log "═══════════════════════════════════════"
log "  Peoples Feedback — EC2 Setup (Fixed)"
log "═══════════════════════════════════════"

# Detection
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS="unknown"
fi

log "Detected OS: $OS"

# ── Step 1: Remove old portalpro ──
log "Step 1: Removing old portalpro application..."
systemctl stop portalpro 2>/dev/null || true
systemctl disable portalpro 2>/dev/null || true
rm -f /etc/systemd/system/portalpro.service
rm -f /etc/nginx/sites-enabled/portalpro* /etc/nginx/sites-available/portalpro* /etc/nginx/conf.d/portalpro* 2>/dev/null || true
rm -rf /var/www/portalpro /opt/portalpro 2>/dev/null || true
pkill -f portalpro 2>/dev/null || true
log "  ✓ Portalpro removed"

# ── Step 2: Install Nginx ──
log "Step 2: Installing Nginx..."
if [ "$OS" == "amzn" ]; then
    # --allowerasing fixes the curl-minimal vs curl conflict in AL2023
    dnf install -y -q nginx --allowerasing
    WWW_USER="nginx"
    NGINX_CONF_DIR="/etc/nginx/conf.d"
else
    apt-get update -qq
    apt-get install -y -qq nginx curl
    WWW_USER="www-data"
    NGINX_CONF_DIR="/etc/nginx/sites-available"
fi
systemctl enable nginx
log "  ✓ Nginx installed"

# ── Step 3: Create deployment directory ──
log "Step 3: Setting up deployment directory..."
mkdir -p $DEPLOY_DIR
cat > $DEPLOY_DIR/index.html << 'HTML'
<!DOCTYPE html>
<html><head><title>Peoples Feedback</title>
<style>body{font-family:system-ui;display:flex;justify-content:center;align-items:center;min-height:100vh;margin:0;background:#0f172a;color:#fff}
.c{text-align:center}h1{font-size:2rem;margin-bottom:0.5rem}p{color:#94a3b8;font-size:1rem}</style>
</head><body><div class="c"><h1>🚀 Peoples Feedback</h1><p>Deploying... Push to GitHub to trigger auto-deploy.</p></div></body></html>
HTML
chown -R $WWW_USER:$WWW_USER $DEPLOY_DIR 2>/dev/null || true
log "  ✓ $DEPLOY_DIR created"

# ── Step 4: Configure Nginx ──
log "Step 4: Configuring Nginx..."

# Generate Nginx config
NGINX_CONFIG="
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root $DEPLOY_DIR;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    location /api/ {
        proxy_pass $API_BACKEND;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
}
"

if [ "$OS" == "amzn" ]; then
    echo "$NGINX_CONFIG" > /etc/nginx/conf.d/peoples-feedback.conf
    sed -i 's/listen       80 default_server;/listen       80;/g' /etc/nginx/nginx.conf 2>/dev/null || true
else
    echo "$NGINX_CONFIG" > /etc/nginx/sites-available/peoples-feedback
    rm -f /etc/nginx/sites-enabled/default
    ln -sf /etc/nginx/sites-available/peoples-feedback /etc/nginx/sites-enabled/
fi

nginx -t
systemctl restart nginx
log "  ✓ Nginx configured and restarted"

# ── Done ──
log "═══════════════════════════════════════════════════════"
log "  ✅ Setup complete for $OS!"
log "═══════════════════════════════════════════════════════"
