FROM node:22-slim AS deps

WORKDIR /app

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV COREPACK_ENABLE_STRICT=1
RUN corepack enable && corepack prepare pnpm@11.1.2 --activate

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm install --frozen-lockfile


FROM node:22-slim AS builder

WORKDIR /app

ENV COREPACK_ENABLE_DOWNLOAD_PROMPT=0
ENV COREPACK_ENABLE_STRICT=1
RUN corepack enable && corepack prepare pnpm@11.1.2 --activate

COPY --from=deps /app/node_modules ./node_modules
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./

COPY . .

ENV NEXT_TELEMETRY_DISABLED=1
ENV NODE_ENV=production
RUN pnpm build

RUN --mount=type=cache,id=pnpm,target=/root/.local/share/pnpm/store \
    pnpm install --prod --frozen-lockfile


FROM node:22-slim AS production

WORKDIR /app

RUN groupadd -r -g 1001 nodejs && \
    useradd -r -u 1001 -g nodejs -m -s /bin/bash -d /home/nodejs nodejs

SHELL ["/bin/bash", "-o", "pipefail", "-c"]
RUN apt-get update && \
    apt-get install -y --no-install-recommends bash tzdata curl ca-certificates gnupg && \
    curl -fsSL 'https://artifacts-cli.infisical.com/setup.deb.sh' -o /tmp/setup.deb.sh && \
    grep -q "infisical" /tmp/setup.deb.sh && \
    grep -q "gpg" /tmp/setup.deb.sh && \
    chmod +x /tmp/setup.deb.sh && \
    /tmp/setup.deb.sh && \
    apt-get update && \
    apt-get install -y --no-install-recommends infisical && \
    command -v infisical && \
    infisical --version && \
    rm -f /tmp/setup.deb.sh && \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false && \
    rm -rf /var/lib/apt/lists/*

SHELL ["/bin/sh", "-c"]

COPY --from=builder --chown=nodejs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nodejs:nodejs /app/.next/static ./.next/static
COPY --from=builder --chown=nodejs:nodejs /app/public ./public

COPY --chown=nodejs:nodejs docker/commands.sh /commands
COPY --chown=nodejs:nodejs docker/start.sh /start

RUN sed -i 's/\r$//g' /commands /start && \
    chmod 550 /commands /start

USER nodejs

ENV NODE_ENV=production
ENV PORT=3200
ENV HOSTNAME=0.0.0.0

# NOTE: Only use in development/staging with self-signed certs
# For production, ensure your backend has valid SSL certificates
# ENV NODE_TLS_REJECT_UNAUTHORIZED=0

EXPOSE 3200

CMD ["/start"]
