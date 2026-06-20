FROM node:22-alpine AS base
WORKDIR /app
RUN apk add --no-cache libc6-compat
ENV PNPM_HOME="/pnpm"
ENV PATH="$PNPM_HOME:$PATH"
RUN corepack enable

# ─── deps ───────────────────────────────────────────────
FROM base AS deps
COPY package.json pnpm-lock.yaml* .npmrc ./
RUN pnpm install --frozen-lockfile

# ─── build ──────────────────────────────────────────────
FROM base AS build
COPY --from=deps /app/node_modules ./node_modules
COPY . .
ENV NODE_ENV=production
ENV ASTRO_TELEMETRY_DISABLED=1
RUN pnpm build

# ─── runtime ────────────────────────────────────────────
FROM base AS runtime
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=4321
ENV HOST=0.0.0.0
ENV ASTRO_TELEMETRY_DISABLED=1

# Install a tiny static server (we serve pre-built static assets)
RUN npm install -g serve@^14.2.4 && npm cache clean --force

COPY --from=build /app/dist ./dist
COPY --from=build /app/package.json ./package.json

# Run as non-root
RUN addgroup --system --gid 1001 doxiq && \
    adduser --system --uid 1001 --ingroup doxiq doxiq && \
    chown -R doxiq:doxiq /app
USER doxiq

EXPOSE 4321
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD wget --quiet --tries=1 --spider http://localhost:4321/ || exit 1

CMD ["sh", "-c", "serve -s dist -l ${PORT:-4321}"]
