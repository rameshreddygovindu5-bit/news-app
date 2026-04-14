# ─────────────────────────────────────────────────────────────────────
#  News Platform — Admin Frontend Dockerfile
#
#  Multi-stage build:
#    Stage 1: Build React app
#    Stage 2: Serve with nginx (SPA routing support)
#
#  Works for both local Docker and AWS EC2 deployment.
# ─────────────────────────────────────────────────────────────────────

# ── Stage 1: Build ──
FROM node:18-alpine AS build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci --silent

COPY . .

# Build-time API URL — override via docker-compose or --build-arg
ARG REACT_APP_API_URL=http://127.0.0.1:8005
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

RUN npm run build

# ── Stage 2: Serve with nginx ──
FROM nginx:alpine

# Remove default config
RUN rm /etc/nginx/conf.d/default.conf

# Add SPA-aware nginx config (supports BrowserRouter)
COPY --from=build /app/build /usr/share/nginx/html

RUN cat > /etc/nginx/conf.d/admin.conf << 'NGINX'
server {
    listen 3000;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    # SPA fallback — all routes serve index.html
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy — forward /api/* to backend
    location /api/ {
        proxy_pass http://backend:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # Cache static assets
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Health check
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;
    gzip_min_length 256;
}
NGINX

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost:3000/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
