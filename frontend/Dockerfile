# =============================================================================
# CYBERSLEUTH AI - Frontend Dockerfile
# =============================================================================
# Multi-stage build: Vite bundle -> nginx static server with SPA routing.
#
# The build context is the REPOSITORY ROOT (the same context the backend
# image uses), so every COPY source path below is prefixed with `frontend/`:
#
#   docker build -t cybersleuth-frontend -f frontend/Dockerfile .
#   docker run -p 8080:80 cybersleuth-frontend
#
# The API base URL can be baked into the bundle at build time:
#
#   docker build -t cybersleuth-frontend \
#       --build-arg VITE_API_BASE_URL=https://cybersleuth-api.onrender.com/api \
#       -f frontend/Dockerfile .
#
# Note: for deployment, Netlify (or Vercel) builds the frontend directly from
# the repository using the root netlify.toml - no Docker required.
# =============================================================================

FROM node:20-alpine AS builder

WORKDIR /app

# The bundle talks to the API through VITE_API_BASE_URL. It defaults to the
# relative `/api`, which the nginx configuration below proxies to the
# `backend` service on the compose network.
ARG VITE_API_BASE_URL=/api
ARG VITE_SUPABASE_URL=
ARG VITE_SUPABASE_ANON_KEY=

ENV VITE_API_BASE_URL=${VITE_API_BASE_URL} \
    VITE_SUPABASE_URL=${VITE_SUPABASE_URL} \
    VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}

# Install dependencies first so the layer is cached across code changes.
# The lock file lives in frontend/, and the context is the repository root.
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build

FROM nginx:alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA routing configuration for React Router.
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# The container health check covers nginx itself (the SPA). The backend is
# verified through the /health proxy rule in nginx.conf, which the API
# container exposes as /api/health.
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
