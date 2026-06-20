import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NarrativeRenderer } from "./narrative-renderer";

const TEXT_SCHEMA = {
  type: "object",
  properties: {
    summary_text: { type: "string" },
    key_findings: { type: "array", items: { type: "string" } },
  },
};

describe("NarrativeRenderer", () => {
  it("hides the verdict field (already shown in hero)", () => {
    render(
      <NarrativeRenderer
        output={{ verdict: "PASS", summary_text: "All good." }}
        schema={{ type: "object", properties: { verdict: {}, summary_text: {} } }}
      />
    );
    expect(screen.queryByText("Verdict")).toBeNull();
  });

  it("renders summary_text in serif prose", () => {
    render(
      <NarrativeRenderer
        output={{ summary_text: "Run completed without findings." }}
        schema={TEXT_SCHEMA}
      />
    );
    const para = screen.getByText("Run completed without findings.");
    expect(para.className).toMatch(/font-serif/);
  });

  it("renders key_findings as a vertical list", () => {
    render(
      <NarrativeRenderer
        output={{ key_findings: ["First", "Second"] }}
        schema={TEXT_SCHEMA}
      />
    );
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("renders citations as chips", () => {
    render(
      <NarrativeRenderer
        output={{
          citations: [
            {
              document_id: "00000000-0000-0000-0000-000000000001",
              document_type_slug: "cedula",
              field_path: "rut",
              value: "12.345.678-5",
            },
          ],
        }}
        schema={null}
      />
    );
    expect(screen.getByText(/@cedula\.rut/)).toBeInTheDocument();
  });

  it("renders an array of records as a table", () => {
    render(
      <NarrativeRenderer
        output={{
          rule_results: [
            { rule: "RUT", severity: "MAJOR" },
            { rule: "Date", severity: "INFO" },
          ],
        }}
        schema={null}
      />
    );
    expect(screen.getByText("Rule results")).toBeInTheDocument();
    expect(screen.getByText("RUT")).toBeInTheDocument();
    expect(screen.getByText("MAJOR")).toBeInTheDocument();
    expect(screen.getByText("Date")).toBeInTheDocument();
  });

  it("falls back to a friendly message when output is null", () => {
    render(<NarrativeRenderer output={null} schema={null} />);
    expect(screen.getByText(/No output disponible/)).toBeInTheDocument();
  });
});
