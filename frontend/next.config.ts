import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const withNextIntl = createNextIntlPlugin("./src/i18n/request.ts");

const backendUrl =
  process.env.NEXT_PUBLIC_BACKEND_API_HOST ||
  process.env.BACKEND_API_HOST ||
  "http://localhost:8000";

const nextConfig: NextConfig = {
  output: "standalone",
  // Pin the workspace root to this directory (where next.config.ts lives).
  // Next infers the root by scanning up for lockfiles; if a dev machine has a
  // stray lockfile in a parent (e.g. ~/package-lock.json), it warns and may
  // pick the wrong root — which also breaks `output: "standalone"` file
  // tracing for a local build. `__dirname` is portable (it resolves to each
  // checkout's frontend dir), so no machine-specific path is hardcoded.
  outputFileTracingRoot: __dirname,
  transpilePackages: ["react-icons"],
  turbopack: {
    root: __dirname,
  },
  // Bump the proxy timeout for any rewrite-proxied request that legitimately
  // streams (default is ~30s). Multipart uploads no longer go through the
  // rewrite — they hit the explicit route handler at
  // `app/api/v1/documents/upload/route.ts` — but other long-lived calls
  // (SSE streams, slow extractions) benefit from the larger budget.
  experimental: {
    proxyTimeout: 5 * 60 * 1000,
  },
  webpack: (config) => {
    config.resolve.alias.canvas = false;
    return config;
  },
  async rewrites() {
    return {
      // `beforeFiles` cannot be used here because file-system routes must
      // win for the upload handler. The default array placement (afterFiles)
      // already lets file-system routes take precedence, but Next.js' dev
      // server has been observed to fall through to the rewrite when a
      // freshly added route hasn't been picked up yet — so we additionally
      // exclude `documents/upload` from the source pattern as a belt.
      afterFiles: [
        {
          source: "/api/v1/:path((?!documents/upload$).*)",
          destination: `${backendUrl}/v1/:path*`,
        },
      ],
      beforeFiles: [],
      fallback: [],
    };
  },
};

export default withNextIntl(nextConfig);
