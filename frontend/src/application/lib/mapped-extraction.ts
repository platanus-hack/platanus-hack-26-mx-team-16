import type { CoordinateBox } from "@/src/domain/entities/textract";
import type {
  MappedBbox,
  MappedExtraction,
  MappedField,
} from "@/src/infrastructure/repositories/http-workflow-document";

/**
 * Convert one bbox polygon (4 points in normalized [0..1] coordinates)
 * into the rectangular `BoundingBox` shape `PDFViewer` overlays expect.
 *
 * The polygon is always axis-aligned in our extractions (extract_fields
 * lambda emits the bounding rect in clockwise order starting top-left)
 * but we still take min/max so a rotated polygon would still produce
 * the correct enclosing rectangle.
 */
function polygonToBoundingBox(polygon: { x: number; y: number }[]) {
  if (polygon.length === 0) {
    return { Left: 0, Top: 0, Width: 0, Height: 0 };
  }
  const xs = polygon.map((p) => p.x);
  const ys = polygon.map((p) => p.y);
  const left = Math.min(...xs);
  const right = Math.max(...xs);
  const top = Math.min(...ys);
  const bottom = Math.max(...ys);
  return {
    Left: left,
    Top: top,
    Width: right - left,
    Height: bottom - top,
  };
}

const FIELD_COLOR = "rgba(34, 197, 94, 0.12)"; // emerald @ 12%

/**
 * Flatten a `mapped_extraction` dict into a flat `CoordinateBox[]` so
 * the unified `PDFViewer` can render every field's bbox(es) on top of
 * the PDF. One field can produce multiple boxes (one per `bbox` entry,
 * potentially across pages) — the box id encodes both the field key
 * and the bbox index so the data-pane click can target a specific
 * occurrence later if needed.
 *
 * `id` is `"field:<key>"` for the FIRST bbox of a field — that's the
 * stable identifier the data-pane uses to drive `activeBoxId`.
 * Subsequent bboxes get `"field:<key>:<i>"`.
 *
 * `pageOffset` shifts every bbox's page number into the original PDF's
 * coordinate system. The `extract_fields` Lambda emits bboxes with
 * `page_number` *relative to the WorkflowDocument* (1 = first page of
 * the doc), but the viewer renders the **whole** PDF, so the offset
 * lifts logical → physical pages. For a doc whose `pageRange.from = 17`
 * the offset is 16, so logical page 1 lands on physical page 17.
 */
export function mappedExtractionToBoxes(
  mapped: MappedExtraction | null | undefined,
  pageOffset: number = 0
): CoordinateBox[] {
  if (!mapped) return [];
  const boxes: CoordinateBox[] = [];
  for (const [key, raw] of Object.entries(mapped)) {
    const field = raw as MappedField;
    if (!Array.isArray(field?.bbox)) continue;
    field.bbox.forEach((bb: MappedBbox, idx: number) => {
      const logicalPage = bb.page_number || field.page_number || 1;
      boxes.push({
        id: idx === 0 ? `field:${key}` : `field:${key}:${idx}`,
        text: bb.matched_text || String(field.value ?? ""),
        type: key,
        boundingBox: polygonToBoundingBox(bb.polygon),
        // Must stay in [0..1]: PDFViewer derives both the tier color and
        // the rendered percentage from it (×100 here shows e.g. "9998%").
        confidence: field.ocr_confidence ?? bb.confidence ?? 0,
        color: FIELD_COLOR,
        page: logicalPage + pageOffset,
      });
    });
  }
  return boxes;
}

/** Resolve the box id the data-pane should highlight for a given
 *  field key — always the first bbox of that field. */
export function fieldKeyToBoxId(key: string): string {
  return `field:${key}`;
}
