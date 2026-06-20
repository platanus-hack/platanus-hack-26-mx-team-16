import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Auto-cleanup mounted React trees between tests to avoid cross-test bleed.
afterEach(() => {
  cleanup();
});
