# ─────────────────────────────────────────────────────────────────────
#  News Platform — Frontend Dockerfile
#
#  Serves the React admin UI via react-scripts dev server.
#  For production, build static files and serve via nginx instead.
# ─────────────────────────────────────────────────────────────────────

FROM node:18-alpine

WORKDIR /app

# Install dependencies (cached layer)
COPY package.json package-lock.json* ./
RUN npm ci --silent

# Copy source
COPY . .

# Build-time API URL — passed from docker-compose or build args
ARG REACT_APP_API_URL=http://127.0.0.1:8005
ENV REACT_APP_API_URL=${REACT_APP_API_URL}

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD wget -qO- http://localhost:3000 || exit 1

CMD ["npm", "start"]
