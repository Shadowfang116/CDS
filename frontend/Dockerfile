# Multi-stage production Dockerfile. Build with context = frontend directory.

# -----------------------------------------------------------------------------
# Stage 1: build Next.js app (standalone output)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

# -----------------------------------------------------------------------------
# Stage 2: runtime (standalone server, non-root)
# -----------------------------------------------------------------------------
FROM node:20-alpine AS runtime

ENV NODE_ENV=production
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
