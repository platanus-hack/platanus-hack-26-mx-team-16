/**
 * BFF: GET/PUT /api/owliver/me/alerts → backend /v1/me/alerts (§F11, protected).
 * Account-level alert prefs (email always-on display + optional Slack webhook).
 *  - GET → current prefs. Fixture fallback so the panel renders offline.
 *  - PUT → persist { emailEnabled, slackWebhookUrl }; writes forward errors
 *    verbatim (they need a real session).
 */
import { type NextRequest, NextResponse } from "next/server";

import { alertPrefsFixture } from "@/src/application/owliver/fixtures";
import { asData } from "@/src/application/owliver/lib/envelope";
import { backendGet, backendRequest } from "@/src/application/owliver/lib/bff";

export async function GET() {
  const result = await backendGet("/me/alerts");
  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  return NextResponse.json(asData(alertPrefsFixture));
}

export async function PUT(request: NextRequest) {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    body = {};
  }
  const result = await backendRequest({
    method: "PUT",
    url: "/me/alerts",
    data: body,
  });
  if (result.ok) {
    return NextResponse.json(result.data, { status: result.status });
  }
  return NextResponse.json(result.error, { status: result.status });
}
