# =============================================================================
# PROJECT NEXUS AI - Frontend Dockerfile
# =============================================================================
# Multi-stage Dockerfile for React frontend.
# =============================================================================

FROM node:20-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine as runtime

COPY --from=builder /app/dist /usr/share/nginx/html

# Copy nginx configuration for SPA routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
