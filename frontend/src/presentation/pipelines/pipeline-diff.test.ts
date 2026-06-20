import { describe, expect, it } from "vitest";

import type { PipelinePhase } from "@/src/application/hooks/queries/pipelines";

import { computePipelineDiff, diffPhases } from "./pipeline-diff";

function phase(
  id: string,
  kind: string,
  config: Record<string, unknown> = {}
): PipelinePhase {
  return { id, kind, config };
}

describe("diffPhases", () => {
  it("detects added and removed phases by id", () => {
    const before = [phase("a", "ingest"), phase("b", "extract_text")];
    const after = [phase("a", "ingest"), phase("c", "analyze")];
    const changes = diffPhases(before, after);
    expect(changes).toContainEqual(
      expect.objectContaining({ id: "b", change: "removed" })
    );
    expect(changes).toContainEqual(
      expect.objectContaining({ id: "c", change: "added" })
    );
  });

  it("flags a reordered phase as moved", () => {
    const before = [phase("a", "ingest"), phase("b", "extract_text")];
    const after = [phase("b", "extract_text"), phase("a", "ingest")];
    const changes = diffPhases(before, after);
    const moved = changes.find((c) => c.id === "a");
    expect(moved?.change).toBe("moved");
    expect(moved?.fromIndex).toBe(0);
    expect(moved?.toIndex).toBe(1);
  });

  it("reports config changes as modified, not moved", () => {
    const before = [
      phase("x", "extract_text", { extractor: "textract_layout" }),
    ];
    const after = [phase("x", "extract_text", { extractor: "asr" })];
    const changes = diffPhases(before, after);
    const mod = changes.find((c) => c.id === "x");
    expect(mod?.change).toBe("modified");
    expect(mod?.details).toEqual(
      expect.arrayContaining(["extractor: textract_layout → asr"])
    );
  });
});

describe("computePipelineDiff", () => {
  it("is empty when nothing changed", () => {
    const recipe = { phases: [phase("a", "ingest")] };
    expect(computePipelineDiff(recipe, recipe).empty).toBe(true);
  });

  it("surfaces an activation change as an extraction_gate phase-config diff", () => {
    // La activación va plegada en extraction_gate.config.activation (D-A): su
    // cambio aparece como diff de config de esa fase, no como fila de policy.
    const diff = computePipelineDiff(
      {
        phases: [
          phase("g", "extraction_gate", { activation: { qa_sample_rate: 0 } }),
        ],
      },
      {
        phases: [
          phase("g", "extraction_gate", { activation: { qa_sample_rate: 1 } }),
        ],
      }
    );
    expect(diff.empty).toBe(false);
    const mod = diff.phases.find((c) => c.id === "g");
    expect(mod?.change).toBe("modified");
  });
});
