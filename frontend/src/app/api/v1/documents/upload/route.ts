/**
 * Streaming upload proxy.
 *
 * The default `next.config.ts` rewrite (`/api/v1/:path*` → backend) buffers
 * the request body before forwarding it. For multipart uploads of any
 * non-trivial size this surfaces as `ECONNRESET` / `socket hang up`
 * because the proxy and the upstream race against Next.js's internal
 * buffer + the dev backend's keep-alive timeout.
 *
 * Implementing the upload as an explicit route handler skips the rewrite
 * (file-system routes take precedence) and lets us pipe the request body
 * straight through to the backend with `fetch({ duplex: "half" })`. No
 * intermediate buffering, no body-size limit, and we can set our own
 * timeout if needed.
 */

import { type NextRequest, NextResponse } from "next/server";

import { Settings } from "@/src/settings";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const UPLOAD_TIMEOUT_MS = 5 * 60 * 1000; // 5 min

function buildUpstreamUrl(): string {
  const base = Settings.apiBaseUrl.replace(/\/+$/, "");
  return `${base}/v1/documents/upload`;
}

function pickHeaders(req: NextRequest): Headers {
  const out = new Headers();
  // Multipart boundary lives in Content-Type; preserve it verbatim.
  const ct = req.headers.get("content-type");
  if (ct) out.set("content-type", ct);
  const cl = req.headers.get("content-length");
  if (cl) out.set("content-length", cl);
  const auth = req.headers.get("authorization");
  if (auth) out.set("authorization", auth);
  const tenant = req.headers.get("x-tenant");
  if (tenant) out.set("x-tenant", tenant);
  return out;
}

export async function POST(request: NextRequest): Promise<Response> {
  const upstreamUrl = buildUpstreamUrl();
  const sizeHeader = request.headers.get("content-length");
  console.log(
    `[upload-proxy] forwarding to ${upstreamUrl} size=${sizeHeader ?? "?"}`
  );

  if (!request.body) {
    return NextResponse.json(
      { errors: [{ code: "upload.empty_body", message: "Empty body" }] },
      { status: 400 }
    );
  }

  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), UPLOAD_TIMEOUT_MS);

  try {
    const upstream = await fetch(upstreamUrl, {
      method: "POST",
      headers: pickHeaders(request),
      body: request.body,
      // Required when streaming a request body in Node.js fetch.
      // @ts-expect-error — `duplex` is Node-only and not in the lib.dom types.
      duplex: "half",
      signal: controller.signal,
    });
    console.log(`[upload-proxy] upstream responded status=${upstream.status}`);

    // Re-stream the upstream response to the client preserving status +
    // content-type so axios on the client side parses it the same way.
    const responseHeaders = new Headers();
    const upstreamCt = upstream.headers.get("content-type");
    if (upstreamCt) responseHeaders.set("content-type", upstreamCt);

    return new Response(upstream.body, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    const isAbort =
      error instanceof Error &&
      (error.name === "AbortError" || error.name === "TimeoutError");
    return NextResponse.json(
      {
        errors: [
          {
            code: isAbort ? "upload.timeout" : "upload.proxy_error",
            message:
              error instanceof Error ? error.message : "Upload proxy failure",
          },
        ],
      },
      { status: isAbort ? 504 : 502 }
    );
  } finally {
    clearTimeout(timeout);
  }
}
