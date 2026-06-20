import { describe, expect, it } from "vitest";
import type { CaseNoun } from "@/src/domain/entities/workflow";
import { caseNoun } from "./case-noun";

const NOUN: CaseNoun = {
  es: { one: "Pedido", other: "Pedidos" },
  en: { one: "Order", other: "Orders" },
};

describe("caseNoun", () => {
  it("returns the workflow noun in the active locale (singular/plural)", () => {
    expect(caseNoun({ caseNoun: NOUN }, "es", 1)).toBe("Pedido");
    expect(caseNoun({ caseNoun: NOUN }, "es", 2)).toBe("Pedidos");
    expect(caseNoun({ caseNoun: NOUN }, "en", 1)).toBe("Order");
    expect(caseNoun({ caseNoun: NOUN }, "en", 3)).toBe("Orders");
  });

  it("matches the locale by prefix (es-MX → es, en-US → en)", () => {
    expect(caseNoun({ caseNoun: NOUN }, "es-MX", 1)).toBe("Pedido");
    expect(caseNoun({ caseNoun: NOUN }, "en-US", 2)).toBe("Orders");
  });

  it("falls back to the i18n default when the workflow has no noun", () => {
    expect(caseNoun({ caseNoun: null }, "es", 1)).toBe("Caso");
    expect(caseNoun({ caseNoun: undefined }, "es", 2)).toBe("Casos");
    expect(caseNoun({}, "en", 1)).toBe("Case");
    expect(caseNoun({}, "en", 2)).toBe("Cases");
  });

  it("falls back when the workflow itself is null/undefined", () => {
    expect(caseNoun(null, "es", 2)).toBe("Casos");
    expect(caseNoun(undefined, "en", 1)).toBe("Case");
  });

  it("treats any non-1 count (incl. 0) as plural", () => {
    expect(caseNoun({ caseNoun: NOUN }, "es", 0)).toBe("Pedidos");
  });

  it("defaults unknown locales to es", () => {
    expect(caseNoun({ caseNoun: NOUN }, "fr", 1)).toBe("Pedido");
  });
});
