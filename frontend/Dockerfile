# =============================================================================
# CYBERSLEUTH AI - Frontend Dockerfile
# =============================================================================
# Multi-stage build: Vite bundle -> nginx static server with SPA routing.
#
#   docker build -t cybersleuth-frontend -f frontend/Dockerfile .
#   docker run -p 8080:80 cybersleuth-frontend
#
# Note: for deployment, Netlify (or Vercel) builds the frontend directly from
# the repository using the root netlify.toml - no Docker required.
# =============================================================================

FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies first so the layer is cached across code changes.
COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine AS runtime

COPY --from=builder /app/dist /usr/share/nginx/html

# SPA routing configuration for React Router.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
