import { test, expect } from "@playwright/test";
import { login, cleanupRoles } from "./auth.setup";

// Helper: navigate to /roles via sidebar click (preserves in-memory auth token)
async function goToRoles(page: import("@playwright/test").Page) {
  await page.click('a[href="/roles"]');
  await page.waitForURL("**/roles");
}

test.describe("Roles CRUD", () => {
  test.beforeEach(async ({ page, request }) => {
    await cleanupRoles(request);
    await login(page);
    await goToRoles(page);
    // Wait for the roles view to load
    await page.waitForTimeout(1000);
  });

  test("shows empty state when no roles exist", async ({ page }) => {
    await expect(page.getByText("Sin roles")).toBeVisible();
    await expect(
      page.getByText(
        "Los roles permiten controlar los permisos de acceso de los usuarios de tu equipo."
      )
    ).toBeVisible();
    await expect(page.getByRole("button", { name: "Crear Rol" })).toBeVisible();
  });

  test("creates a new role with permissions", async ({ page }) => {
    // Open create dialog
    await page.getByRole("button", { name: "Crear Rol" }).click();
    await expect(page.getByRole("heading", { name: "Crear" })).toBeVisible();

    // Fill name
    await page.getByPlaceholder("Ingrese el nombre del rol").fill("Editor");

    // Open permission selector
    await page.getByRole("button", { name: "Seleccionar permisos" }).click();
    await expect(
      page.getByRole("heading", { name: "Seleccionar Permisos" })
    ).toBeVisible();

    // Select Dashboard category
    await page.getByRole("checkbox", { name: "Dashboard (1)" }).click();
    await expect(page.getByText("1 permisos seleccionados")).toBeVisible();

    // Click Listo
    await page.getByRole("button", { name: "Listo" }).click();

    // Wait for permission selector to close, then verify badges
    await page.waitForTimeout(500);
    await expect(page.getByText("Ver dashboard").first()).toBeVisible();

    // Submit form
    await page.getByRole("button", { name: "Crear rol" }).click();

    // Verify role card appears
    await expect(page.getByRole("heading", { name: "Editor" })).toBeVisible({
      timeout: 10000,
    });
    await expect(page.getByText("1 permisos")).toBeVisible();
    await expect(page.getByText("Activo")).toBeVisible();
  });

  test("edits an existing role", async ({ page }) => {
    // First create a role
    await page.getByRole("button", { name: "Crear Rol" }).click();
    await page.getByPlaceholder("Ingrese el nombre del rol").fill("Viewer");
    await page.getByRole("button", { name: "Crear rol" }).click();

    // Wait for role to appear
    await expect(page.getByRole("heading", { name: "Viewer" })).toBeVisible({
      timeout: 10000,
    });

    // Click edit button (first icon button in card)
    const roleCard = page.locator("div.rounded-lg.border").first();
    await roleCard.locator("button").first().click();

    // Verify edit dialog opens with pre-filled data
    await expect(page.getByRole("heading", { name: "Editar" })).toBeVisible();

    const nameInput = page.locator("#edit-role-name");
    await expect(nameInput).toHaveValue("Viewer", { timeout: 5000 });

    // Change name
    await nameInput.clear();
    await nameInput.fill("Viewer Updated");

    // Add permissions
    await page.getByRole("button", { name: "Seleccionar permisos" }).click();
    await page.getByRole("checkbox", { name: "Dashboard (1)" }).click();
    await page.getByRole("button", { name: "Listo" }).click();

    // Save
    await page.getByRole("button", { name: "Guardar" }).click();

    // Verify updated role
    await expect(
      page.getByRole("heading", { name: "Viewer Updated" })
    ).toBeVisible({ timeout: 10000 });
  });

  test("deletes a role", async ({ page }) => {
    // Create a role first
    await page.getByRole("button", { name: "Crear Rol" }).click();
    await page.getByPlaceholder("Ingrese el nombre del rol").fill("ToDelete");
    await page.getByRole("button", { name: "Crear rol" }).click();

    // Wait for role to appear
    await expect(page.getByRole("heading", { name: "ToDelete" })).toBeVisible({
      timeout: 10000,
    });

    // Click delete button (second icon button in card)
    const roleCard = page.locator("div.rounded-lg.border").first();
    await roleCard.locator("button").nth(1).click();

    // Confirm deletion in modal
    await expect(page.getByText("Eliminar rol")).toBeVisible();
    await expect(
      page.getByText('¿Estás seguro de que deseas eliminar el rol "ToDelete"?')
    ).toBeVisible();
    await page.getByRole("button", { name: "Eliminar" }).click();

    // Verify role is removed and empty state shows
    await expect(page.getByText("Sin roles")).toBeVisible({ timeout: 10000 });
  });

  test("permission selector search filters permissions", async ({ page }) => {
    await page.getByRole("button", { name: "Crear Rol" }).click();
    await page.getByRole("button", { name: "Seleccionar permisos" }).click();

    // Search for "workflow"
    await page.getByPlaceholder("Buscar permisos...").fill("workflow");

    // Only Workflows category should be visible
    await expect(page.getByText("Workflows (6)")).toBeVisible();
    await expect(page.getByText("Dashboard (1)")).not.toBeVisible();
    await expect(page.getByText("Roles (5)")).not.toBeVisible();

    // Clear search
    await page.getByPlaceholder("Buscar permisos...").clear();

    // All categories visible again
    await expect(page.getByText("Dashboard (1)")).toBeVisible();
    await expect(page.getByText("Roles (5)")).toBeVisible();
    await expect(page.getByText("Workflows (6)")).toBeVisible();
  });

  test("category checkbox selects all permissions in category", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Crear Rol" }).click();
    await page.getByRole("button", { name: "Seleccionar permisos" }).click();

    // Select Roles category (5 permissions)
    await page.getByRole("checkbox", { name: "Roles (5)" }).click();
    await expect(page.getByText("5 permisos seleccionados")).toBeVisible();

    // Uncheck category deselects all
    await page.getByRole("checkbox", { name: "Roles (5)" }).click();
    await expect(page.getByText("0 permisos seleccionados")).toBeVisible();
  });
});
