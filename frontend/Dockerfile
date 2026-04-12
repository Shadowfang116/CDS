# Multi-stage production Dockerfile. Build with context = frontend directory.

# -----------------------------------------------------------------------------
# Stage 1: build Next.js app (standalone output)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Pass API URL at build time so next.config.mjs rewrites bake in the correct destination
ARG API_INTERNAL_BASE_URL=http://api:8000
ENV API_INTERNAL_BASE_URL=$API_INTERNAL_BASE_URL

RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: runtime (standalone server, non-root)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS runtime

ENV NODE_ENV=production \
    HOSTNAME=0.0.0.0 \
    PORT=3000
# Non-root user
RUN addgroup -g 10001 -S nodegroup \
    && adduser -u 10001 -S nodeuser -G nodegroup

WORKDIR /app

# Copy standalone output + static + public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

RUN chown -R nodeuser:nodegroup /app
USER nodeuser

EXPOSE 3000

# Healthcheck: GET /dashboard (or root)
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/dashboard || exit 1

CMD ["node", "server.js"]
