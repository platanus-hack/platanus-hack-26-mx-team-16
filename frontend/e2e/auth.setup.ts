import { type Page, type APIRequestContext } from "@playwright/test";

const TEST_EMAIL = "team@llamitai.com";
const TEST_PASSWORD = "12345678x";
const TENANT_SLUG = "llamitai-dev";
const BASE_URL = "http://localhost:3000";

export async function login(page: Page) {
  // Go to root, clear everything
  await page.goto("/");
  await page.context().clearCookies();
  await page.evaluate(() => localStorage.clear());

  // Navigate to login
  await page.goto("/login");
  await page.waitForSelector('button:has-text("Iniciar Sesión")', {
    timeout: 10000,
  });

  // Fill and submit
  await page.fill('input[placeholder="tu@email.com"]', TEST_EMAIL);
  await page.fill('input[placeholder="••••••••"]', TEST_PASSWORD);
  await page.click('button:has-text("Iniciar Sesión")');
  await page.waitForURL("**/dashboard", { timeout: 10000 });
}

export async function cleanupRoles(request: APIRequestContext) {
  const loginResp = await request.post(`${BASE_URL}/api/v1/auth/login`, {
    data: { email: TEST_EMAIL, password: TEST_PASSWORD },
    headers: {
      "x-tenant": TENANT_SLUG,
      "Content-Type": "application/json",
    },
  });

  const loginData = await loginResp.json();
  const token = loginData?.data?.session?.accessToken;
  if (!token) return;

  const rolesResp = await request.get(`${BASE_URL}/api/v1/tenants/roles`, {
    headers: {
      "x-tenant": TENANT_SLUG,
      Authorization: `Bearer ${token}`,
    },
  });

  const rolesData = await rolesResp.json();
  const roles = rolesData?.data || [];

  for (const role of roles) {
    await request.delete(`${BASE_URL}/api/v1/tenants/roles/${role.uuid}`, {
      headers: {
        "x-tenant": TENANT_SLUG,
        Authorization: `Bearer ${token}`,
      },
    });
  }
}
