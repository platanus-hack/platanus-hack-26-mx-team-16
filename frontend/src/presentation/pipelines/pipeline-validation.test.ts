import { describe, expect, it } from "vitest";

import type {
  PhaseCatalogEntry,
  PipelinePhase,
} from "@/src/application/hooks/queries/pipelines";

import { validateRecipeStructure } from "./pipeline-validation";

const CATALOG: PhaseCatalogEntry[] = [
  { kind: "ingest", scope: "document", configSchema: {}, description: "" },
  { kind: "extract_text", scope: "document", configSchema: {}, description: "" },
  { kind: "await_documents", scope: "case", configSchema: {}, description: "" },
  { kind: "analyze", scope: "case", configSchema: {}, description: "" },
];

function phase(id: string, kind: string): PipelinePhase {
  return { id, kind, config: {} };
}

describe("validateRecipeStructure", () => {
  it("accepts document phases before case phases", () => {
    const phases = [
      phase("a", "ingest"),
      phase("b", "extract_text"),
      phase("c", "await_documents"),
      phase("d", "analyze"),
    ];
    expect(validateRecipeStructure(phases, CATALOG)).toEqual([]);
  });

  it("rejects a document phase after a case phase", () => {
    const phases = [
      phase("a", "ingest"),
      phase("c", "analyze"),
      phase("b", "extract_text"),
    ];
    const issues = validateRecipeStructure(phases, CATALOG);
    expect(issues).toContainEqual(
      expect.objectContaining({ phaseId: "b" }),
    );
  });

  it("requires await_documents to be the first case phase", () => {
    const phases = [
      phase("a", "ingest"),
      phase("d", "analyze"),
      phase("c", "await_documents"),
    ];
    const issues = validateRecipeStructure(phases, CATALOG);
    expect(issues.some((i) => i.phaseId === "c")).toBe(true);
  });
});
