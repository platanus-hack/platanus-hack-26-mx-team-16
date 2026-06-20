import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { VerdictBadge } from "./verdict-badge";

describe("VerdictBadge", () => {
  it("renders the PASS glyph with emerald tone", () => {
    render(<VerdictBadge verdict="PASS" size="lg" />);
    const badge = screen.getByLabelText(/Verdict Pass/i);
    expect(badge).toHaveTextContent("PASS");
    expect(badge.className).toMatch(/emerald/);
  });

  it("renders FAIL with rose tone", () => {
    render(<VerdictBadge verdict="FAIL" />);
    const badge = screen.getByLabelText(/Verdict Fail/i);
    expect(badge).toHaveTextContent("FAIL");
    expect(badge.className).toMatch(/rose/);
  });

  it("renders REVIEW with amber tone", () => {
    render(<VerdictBadge verdict="REVIEW" />);
    expect(screen.getByLabelText(/Verdict Review/i).className).toMatch(/amber/);
  });

  it("uses serif typography on the lg size", () => {
    render(<VerdictBadge verdict="PASS" size="lg" />);
    expect(screen.getByLabelText(/Verdict Pass/i).className).toMatch(/font-serif/);
  });
});
