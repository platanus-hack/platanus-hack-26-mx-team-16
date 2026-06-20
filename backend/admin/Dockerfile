FROM node:20-alpine AS builder

RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /build

ARG VITE_API_BASE_URL
ARG VITE_API_KEY
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_API_KEY=${VITE_API_KEY}

COPY ./extensions/payouts/package.json ./extensions/payouts/pnpm-lock.yaml ./extensions/payouts/
COPY ./extensions/payouts/vite.config.js ./extensions/payouts/
COPY ./extensions/payouts/tailwind.config.js ./extensions/payouts/
COPY ./extensions/payouts/postcss.config.js ./extensions/payouts/
COPY ./extensions/payouts/src ./extensions/payouts/src

WORKDIR /build/extensions/payouts
RUN pnpm install --frozen-lockfile

RUN pnpm build

# Verify build output
RUN ls -la dist/ && \
    test -f dist/index.js || (echo "ERROR: dist/index.js not found after build" && exit 1)


FROM directus/directus:11.14.0

ENV EXTENSIONS_PATH=/directus/extensions
ENV EXTENSIONS_MUST_LOAD=true

COPY --from=builder /build/extensions/payouts/package.json /directus/extensions/payouts/
COPY --from=builder /build/extensions/payouts/dist /directus/extensions/payouts/dist
