#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Nginx Config Update — Peoples Feedback Platform
# Run this ONCE on EC2 to configure Nginx for both sites:
#   - Public site:  http://<ip>/          → /var/www/peoples-feedback
#   - Admin UI:     http://<ip>/admin/    → /var/www/peoples-feedback-admin
#   - API proxy:    http://<ip>/api/      → localhost:8005
#
# Usage (on EC2):
#   sudo bash update-nginx.sh
# ═══════════════════════════════════════════════════════════════
set -e

PUBLIC_DIR="/var/www/peoples-feedback"
ADMIN_DIR="/var/www/peoples-feedback-admin"
API_BACKEND="http://127.0.0.1:8005"

echo "[Nginx] Creating directories..."
mkdir -p $PUBLIC_DIR $ADMIN_DIR

cat > /etc/nginx/sites-available/peoples-feedback << NGINX
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # ── Public Client (SPA) ─────────────────────────────────────────────
    root $PUBLIC_DIR;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # ── Admin UI (at /admin/) ────────────────────────────────────────────
    location /admin {
        alias $ADMIN_DIR;
        index index.html;
        try_files \$uri \$uri/ /admin/index.html;
    }

    # ── API Reverse Proxy ────────────────────────────────────────────────
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

    # ── Static Asset Caching ─────────────────────────────────────────────
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff2|woff|ttf)$ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # ── Gzip ─────────────────────────────────────────────────────────────
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml image/svg+xml;
}
NGINX

ln -sf /etc/nginx/sites-available/peoples-feedback /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true

nginx -t && systemctl reload nginx
echo "[Nginx] Done! Config updated and reloaded."
echo "  Public site: http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || hostname -I | awk '{print $1}')/"
echo "  Admin UI:    http://$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || hostname -I | awk '{print $1}')/admin/"
