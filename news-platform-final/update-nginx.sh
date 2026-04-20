#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Nginx Config — Peoples Feedback + Admin UI
#
# Serves:
#   - Peoples Feedback client at / (port 80)
#   - Admin UI at /admin (port 80)
#   - API proxy at /api/* → backend:8005
#
# Usage: sudo bash update-nginx.sh
# ═══════════════════════════════════════════════════════════════

set -e

API_BACKEND="${API_BACKEND:-http://127.0.0.1:8005}"
DEPLOY_DIR="/var/www/peoples-feedback"
ADMIN_DIR="/var/www/peoples-feedback-admin"

echo "Creating nginx config..."

sudo mkdir -p "$DEPLOY_DIR" "$ADMIN_DIR"

cat > /tmp/peoples-feedback.conf << NGINX
server {
    listen 80 default_server;
    server_name _;

    # ── Peoples Feedback Client (main site) ──
    root $DEPLOY_DIR;
    index index.html;

    location / {
        try_files \$uri \$uri/ /index.html;
    }

    # ── Admin UI ──
    location /admin/ {
        alias $ADMIN_DIR/;
        index index.html;
        try_files \$uri \$uri/ /admin/index.html;
    }
    # Admin without trailing slash redirect
    location = /admin {
        return 301 /admin/;
    }

    # ── Uploaded Images ──
    location /uploads/ {
        alias \$HOME/news-platform-final/backend/uploads/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        add_header Access-Control-Allow-Origin * always;
    }

    # ── API Proxy ──
    location /api/ {
        proxy_pass $API_BACKEND/api/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 30s;

        # CORS headers
        add_header Access-Control-Allow-Origin * always;
        add_header Access-Control-Allow-Methods "GET, POST, PUT, DELETE, OPTIONS" always;
        add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;

        if (\$request_method = 'OPTIONS') {
            return 204;
        }
    }

    # ── API docs ──
    location /docs {
        proxy_pass $API_BACKEND/docs;
        proxy_set_header Host \$host;
    }
    location /redoc {
        proxy_pass $API_BACKEND/redoc;
        proxy_set_header Host \$host;
    }

    # ── SEO ──
    location = /sitemap.xml {
        proxy_pass $API_BACKEND/sitemap.xml;
        proxy_set_header Host \$host;
    }
    location = /robots.txt {
        proxy_pass $API_BACKEND/robots.txt;
        proxy_set_header Host \$host;
    }

    # ── Static asset caching ──
    location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 256;
}
NGINX

sudo cp /tmp/peoples-feedback.conf /etc/nginx/sites-available/peoples-feedback
sudo ln -sf /etc/nginx/sites-available/peoples-feedback /etc/nginx/sites-enabled/peoples-feedback
sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null

echo "Testing nginx config..."
sudo nginx -t && sudo systemctl reload nginx

echo "✅ Nginx configured successfully"
echo "   Main site: http://$(hostname -I | awk '{print $1}')"
echo "   Admin UI:  http://$(hostname -I | awk '{print $1}')/admin"
echo "   API docs:  http://$(hostname -I | awk '{print $1}')/docs"
