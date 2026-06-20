"use client";

import {
  ChevronDown,
  ChevronUp,
  Download,
  Eye,
  EyeOff,
  MoreHorizontal,
  RotateCw,
  Search,
  Upload,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react";
import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import {
  type ConfidenceBand,
  confidenceBand,
  formatConfidencePct,
} from "@/src/application/lib/format-confidence";
import type {
  BoundingBox,
  CoordinateBox,
} from "@/src/domain/entities/textract";
import { Button } from "./button";
import { Input } from "./input";
import { PdfViewerLoading } from "./pdf-viewer-loading";
import "react-pdf/dist/Page/AnnotationLayer.css";
import "react-pdf/dist/Page/TextLayer.css";

// The worker is copied to /public on postinstall (see package.json).
// Loading it from the same origin removes the previous unpkg dependency,
// which broke under offline or restricted-network conditions.
if (typeof window !== "undefined") {
  pdfjs.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
}

interface PDFViewerProps {
  /** URL string or file object with optional auth headers. */
  file: string | { url: string; httpHeaders?: Record<string, string> };
  fileName?: string;
  className?: string;
  /** Show top control bar (default: true). */
  showControls?: boolean;
  /** Show zoom in/out buttons (default: true). */
  showZoom?: boolean;
  /** Initial zoom factor (default: 1.0). */
  initialScale?: number;
  /** 1-based page to scroll into view on first render. Snapped to
   *  `[1, numPages]` once the document has loaded. */
  initialPage?: number;
  onLoadSuccess?: (numPages: number) => void;
  onLoadError?: (error: Error) => void;
  onUploadClick?: () => void;
  /** Pre-computed bounding boxes (e.g. from `mapped_extraction`).
   *  Each entry is rendered as an absolutely-positioned overlay over
   *  its `page` and identified by `id`. */
  overlayBoxes?: CoordinateBox[];
  /** When this id changes the viewer scrolls to the matching box's
   *  page and highlights it. Lets a sibling panel drive the viewer
   *  imperatively without coupling refs. */
  activeBoxId?: string | null;
  /** Fired when the user clicks an overlay box. Parents typically
   *  mirror this into `activeBoxId` (and into their own data-pane
   *  highlight) so click works from both sides. */
  onBoxClick?: (boxId: string) => void;
}

// Confidence color tiers. The fields panel already exposes the score
// numerically; mapping it to color here lets the user spot suspect
// extractions at a glance without reading the panel.
const TIER_STYLES: Record<
  ConfidenceBand,
  { bg: string; bgHover: string; border: string; ring: string }
> = {
  high: {
    bg: "rgba(16, 185, 129, 0.28)",
    bgHover: "rgba(16, 185, 129, 0.42)",
    border: "rgba(5, 150, 105, 0.7)",
    ring: "rgba(16, 185, 129, 0.45)",
  },
  medium: {
    bg: "rgba(245, 158, 11, 0.30)",
    bgHover: "rgba(245, 158, 11, 0.46)",
    border: "rgba(217, 119, 6, 0.8)",
    ring: "rgba(245, 158, 11, 0.5)",
  },
  low: {
    bg: "rgba(239, 68, 68, 0.30)",
    bgHover: "rgba(239, 68, 68, 0.46)",
    border: "rgba(220, 38, 38, 0.85)",
    ring: "rgba(239, 68, 68, 0.55)",
  },
};

const ACTIVE_BG = "rgba(37, 99, 235, 0.42)";
const ACTIVE_BORDER = "rgba(29, 78, 216, 0.85)";
const ACTIVE_RING = "rgba(37, 99, 235, 0.55)";

type Rotation = 0 | 90 | 180 | 270;

// Pages within ±RENDER_WINDOW of the visible page stay fully rendered.
// Pages beyond CACHE_WINDOW are dropped to reclaim canvas memory; the
// extra cache ring keeps fast back-scrolls from flashing placeholders.
const RENDER_WINDOW = 2;
const CACHE_WINDOW = 4;

// Rotates a normalized bounding box (0–1 of the original page) to
// match a rotated render. Without this, overlays would point at the
// wrong region after the user rotates a page.
function rotateBoundingBox(b: BoundingBox, r: Rotation): BoundingBox {
  switch (r) {
    case 0:
      return b;
    case 90:
      return {
        Left: 1 - b.Top - b.Height,
        Top: b.Left,
        Width: b.Height,
        Height: b.Width,
      };
    case 180:
      return {
        Left: 1 - b.Left - b.Width,
        Top: 1 - b.Top - b.Height,
        Width: b.Width,
        Height: b.Height,
      };
    case 270:
      return {
        Left: b.Top,
        Top: 1 - b.Left - b.Width,
        Width: b.Height,
        Height: b.Width,
      };
  }
}

export function PDFViewer({
  file,
  fileName,
  className = "",
  showControls = true,
  showZoom = true,
  initialScale = 1.0,
  initialPage,
  onLoadSuccess,
  onLoadError,
  onUploadClick,
  overlayBoxes,
  activeBoxId,
  onBoxClick,
}: PDFViewerProps) {
  const t = useTranslations("PdfViewer");
  const [numPages, setNumPages] = useState<number>(0);
  const [pageNumber, setPageNumber] = useState<number>(1);
  const [pageInput, setPageInput] = useState<string>("1");
  const [scale, setScale] = useState<number>(initialScale);
  const [rotation, setRotation] = useState<Rotation>(0);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [containerWidth, setContainerWidth] = useState<number>(0);
  const [showOverlays, setShowOverlays] = useState(true);
  const [hoveredBoxId, setHoveredBoxId] = useState<string | null>(null);
  const [pageDims, setPageDims] = useState<
    Map<number, { w: number; h: number }>
  >(new Map());
  const [dpr, setDpr] = useState<number>(1);
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const containerRef = useRef<HTMLDivElement>(null);
  const pageRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const searchInputRef = useRef<HTMLInputElement>(null);
  const didJumpToInitialPageRef = useRef(false);

  // Device pixel ratio is read on mount. react-pdf passes this to
  // pdf.js so the canvas is rendered at backing-pixel density instead
  // of being upscaled by the browser, which produced the retina blur.
  useEffect(() => {
    setDpr(window.devicePixelRatio || 1);
  }, []);

  const jumpToInitialPage = useCallback((page: number): void => {
    if (didJumpToInitialPageRef.current) return;
    const node = pageRefs.current.get(page);
    if (!node) return;
    node.scrollIntoView({ behavior: "auto", block: "start" });
    setPageNumber(page);
    setPageInput(String(page));
    didJumpToInitialPageRef.current = true;
  }, []);

  const setPageRef = useCallback(
    (idx: number) => (el: HTMLDivElement | null) => {
      const map = pageRefs.current;
      if (el) map.set(idx, el);
      else map.delete(idx);
    },
    []
  );

  const memoizedFile = useMemo(
    () => file,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [
      typeof file === "string" ? file : file?.url,
      typeof file === "string" ? "" : JSON.stringify(file?.httpHeaders ?? {}),
    ]
  );

  // ── Container width ────────────────────────────────────────────────
  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.offsetWidth * 0.9);
      }
    };
    updateWidth();
    window.addEventListener("resize", updateWidth);
    return () => window.removeEventListener("resize", updateWidth);
  }, []);

  // ── Visible-page tracking via IntersectionObserver ─────────────────
  useEffect(() => {
    const container = containerRef.current;
    if (!container || numPages === 0) return;

    const updateCurrentPage = () => {
      const cRect = container.getBoundingClientRect();
      let bestIdx = 1;
      let bestOverlap = -1;
      for (const [idx, node] of pageRefs.current.entries()) {
        const r = node.getBoundingClientRect();
        const overlap = Math.max(
          0,
          Math.min(r.bottom, cRect.bottom) - Math.max(r.top, cRect.top)
        );
        if (overlap > bestOverlap) {
          bestOverlap = overlap;
          bestIdx = idx;
        }
      }
      setPageNumber(bestIdx);
      setPageInput(String(bestIdx));
    };

    container.addEventListener("scroll", updateCurrentPage, { passive: true });
    updateCurrentPage();
    return () => container.removeEventListener("scroll", updateCurrentPage);
  }, [numPages]);

  // ── Per-page rendered size for overlay placement ───────────────────
  const hasOverlays = (overlayBoxes?.length ?? 0) > 0;
  useEffect(() => {
    if (numPages === 0) return;
    const observers: ResizeObserver[] = [];
    for (const [idx, node] of pageRefs.current.entries()) {
      const observer = new ResizeObserver(() => {
        const canvas = node.querySelector("canvas");
        if (canvas && canvas.clientWidth > 0 && canvas.clientHeight > 0) {
          setPageDims((prev) => {
            const next = new Map(prev);
            next.set(idx, { w: canvas.clientWidth, h: canvas.clientHeight });
            return next;
          });
        }
      });
      observer.observe(node);
      observers.push(observer);
    }
    return () => {
      for (const o of observers) o.disconnect();
    };
  }, [numPages, scale, containerWidth, rotation]);

  // ── Render-window membership ───────────────────────────────────────
  // Tracks which pages are currently rendered as real canvases. Pages
  // outside the window collapse to a placeholder so a 40-page doc
  // doesn't allocate 40 canvases on mount.
  const renderedPages = useMemo(() => {
    const lo = Math.max(1, pageNumber - RENDER_WINDOW);
    const hi = Math.min(numPages || 1, pageNumber + RENDER_WINDOW);
    const set = new Set<number>();
    for (let i = lo; i <= hi; i++) set.add(i);
    return set;
  }, [pageNumber, numPages]);

  // Drop dims for pages that left the cache window so stale overlay
  // positions don't linger if the user scrolls far away then back.
  useEffect(() => {
    if (numPages === 0) return;
    setPageDims((prev) => {
      const cacheLo = Math.max(1, pageNumber - CACHE_WINDOW);
      const cacheHi = Math.min(numPages, pageNumber + CACHE_WINDOW);
      let mutated = false;
      const next = new Map(prev);
      for (const p of next.keys()) {
        if (p < cacheLo || p > cacheHi) {
          next.delete(p);
          mutated = true;
        }
      }
      return mutated ? next : prev;
    });
  }, [pageNumber, numPages]);

  // ── Doc / page load handlers ───────────────────────────────────────
  function onDocumentLoadSuccess({ numPages }: { numPages: number }): void {
    setNumPages(numPages);
    setPageNumber(1);
    setPageInput("1");
    setIsLoading(false);
    onLoadSuccess?.(numPages);
  }

  function onDocumentLoadError(err: Error): void {
    setError(err);
    setIsLoading(false);
    onLoadError?.(err);
  }

  // ── Page input → scroll into view ──────────────────────────────────
  function handlePageInputBlur(): void {
    const page = parseInt(pageInput, 10);
    if (!isNaN(page) && page >= 1 && page <= numPages) {
      setPageNumber(page);
      pageRefs.current.get(page)?.scrollIntoView({
        behavior: "smooth",
        block: "start",
      });
    } else {
      setPageInput(pageNumber.toString());
    }
  }

  function handlePageInputKeyDown(
    e: React.KeyboardEvent<HTMLInputElement>
  ): void {
    if (e.key === "Enter") handlePageInputBlur();
  }

  // Zoom + rotate invalidate cached page dims. Without this, the
  // canvas re-renders to a new size while overlays keep painting at
  // the old dims for one frame, producing visible drift.
  const zoomIn = () => {
    setScale((s) => Math.min(s + 0.1, 3.0));
    setPageDims(new Map());
  };
  const zoomOut = () => {
    setScale((s) => Math.max(s - 0.1, 0.5));
    setPageDims(new Map());
  };
  const rotateClockwise = () => {
    setRotation((r) => ((r + 90) % 360) as Rotation);
    setPageDims(new Map());
  };

  const [isDownloading, setIsDownloading] = useState(false);
  const handleDownload = useCallback(async () => {
    if (isDownloading) return;
    const url = typeof file === "string" ? file : file?.url;
    if (!url) return;
    const headers =
      typeof file === "string" ? undefined : (file?.httpHeaders ?? undefined);
    setIsDownloading(true);
    try {
      const res = await fetch(url, { headers, credentials: "include" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = fileName ?? "document.pdf";
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      console.error("pdf-viewer.download_failed", err);
    } finally {
      setIsDownloading(false);
    }
  }, [file, fileName, isDownloading]);

  // ⌘F / Ctrl+F → open search; Esc closes.
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "f") {
        if (!containerRef.current) return;
        e.preventDefault();
        setSearchOpen(true);
        queueMicrotask(() => searchInputRef.current?.focus());
      } else if (e.key === "Escape" && searchOpen) {
        setSearchOpen(false);
        setSearchTerm("");
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [searchOpen]);

  // Compile the search term to a global, case-insensitive regex.
  // Escaping is required because the user can type characters with
  // regex meaning (parens, brackets, dots).
  const searchRegex = useMemo(() => {
    const term = searchTerm.trim();
    if (!term) return null;
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    return new RegExp(`(${escaped})`, "gi");
  }, [searchTerm]);

  // react-pdf renders the text layer span by span. The customTextRenderer
  // returns a string that becomes the span's innerHTML, so wrapping
  // matches in <mark> highlights them through the transparent layer.
  const textRenderer = useCallback(
    ({ str }: { str: string }): string => {
      if (!searchRegex) return str;
      return str.replace(searchRegex, '<mark class="pdf-search-hit">$1</mark>');
    },
    [searchRegex]
  );

  const navigateSearch = useCallback(
    (direction: 1 | -1) => {
      if (!searchRegex || !containerRef.current) return;
      const marks = Array.from(
        containerRef.current.querySelectorAll<HTMLElement>(".pdf-search-hit")
      );
      if (marks.length === 0) return;
      // Find the first mark below the container's current scroll line.
      // From that anchor, step forward or backward by one match.
      const containerTop = containerRef.current.getBoundingClientRect().top;
      const currentIdx = marks.findIndex(
        (m) => m.getBoundingClientRect().top >= containerTop - 1
      );
      const baseIdx = currentIdx === -1 ? 0 : currentIdx;
      const targetIdx = (baseIdx + direction + marks.length) % marks.length;
      marks[targetIdx]?.scrollIntoView({ behavior: "smooth", block: "center" });
    },
    [searchRegex]
  );

  // ── Box index by page + by id ──────────────────────────────────────
  const boxesByPage = useMemo(() => {
    const map = new Map<number, CoordinateBox[]>();
    for (const box of overlayBoxes ?? []) {
      const p = box.page ?? 1;
      const list = map.get(p);
      if (list) list.push(box);
      else map.set(p, [box]);
    }
    return map;
  }, [overlayBoxes]);

  const boxesById = useMemo(() => {
    const map = new Map<string, CoordinateBox>();
    for (const box of overlayBoxes ?? []) map.set(box.id, box);
    return map;
  }, [overlayBoxes]);

  // ── Imperative scroll triggered by parent via `activeBoxId` ────────
  useEffect(() => {
    if (!activeBoxId) return;
    const box = boxesById.get(activeBoxId);
    if (!box) return;
    const page = box.page ?? 1;
    const pageNode = pageRefs.current.get(page);
    const container = containerRef.current;
    if (!pageNode || !container) return;

    setPageNumber(page);
    setPageInput(String(page));

    const dims =
      pageDims.get(page) ??
      (() => {
        const canvas = pageNode.querySelector("canvas");
        return canvas
          ? { w: canvas.clientWidth, h: canvas.clientHeight }
          : null;
      })();

    if (!dims) {
      pageNode.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }

    const pageRect = pageNode.getBoundingClientRect();
    const containerRect = container.getBoundingClientRect();
    const pageYInScrollContent =
      pageRect.top - containerRect.top + container.scrollTop;
    // Bounding box is in the original document orientation, so it must
    // be rotated to match the rendered canvas before placement math.
    const rotatedBox = rotateBoundingBox(box.boundingBox, rotation);
    const bboxTopInPage = rotatedBox.Top * dims.h;
    const bboxHeight = rotatedBox.Height * dims.h;

    const viewportH = container.clientHeight;
    const bboxCenterY = pageYInScrollContent + bboxTopInPage + bboxHeight / 2;
    const TOP_PADDING = 24;
    const targetY =
      bboxHeight >= viewportH - TOP_PADDING * 2
        ? pageYInScrollContent + bboxTopInPage - TOP_PADDING
        : bboxCenterY - viewportH / 2;

    container.scrollTo({
      top: Math.max(0, targetY),
      behavior: "smooth",
    });
  }, [activeBoxId, boxesById, pageDims, rotation]);

  const fileUrl = typeof file === "string" ? file : file.url;
  const displayFileName =
    fileName || fileUrl.split("/").pop() || "document.pdf";

  // Placeholder dims for non-rendered pages. We anchor to the first
  // measured page so windowed placeholders match the document's actual
  // proportions; before any page renders we fall back to A4.
  const firstMeasured = pageDims.values().next().value as
    | { w: number; h: number }
    | undefined;
  const placeholderWidth = firstMeasured?.w ?? containerWidth * scale;
  const placeholderHeight =
    firstMeasured?.h ?? Math.round((containerWidth || 600) * scale * 1.414);

  return (
    <div className={`flex flex-col h-full bg-[#1a1a1a] ${className}`}>
      {showControls && (
        <div className="flex items-center justify-between px-6 py-3.5 bg-[#2a2a2a] border-b border-[#3a3a3a]">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-200 font-medium">
              {displayFileName}
            </span>
            {hasOverlays ? (
              <span className="text-xs text-gray-400">
                ({overlayBoxes?.length ?? 0} fields detected)
              </span>
            ) : null}
          </div>

          <div className="flex items-center gap-2">
            {onUploadClick ? (
              <Button
                variant="ghost"
                size="sm"
                onClick={onUploadClick}
                className="text-gray-200 hover:text-gray-100 hover:bg-[#3a3a3a] h-9 px-3 mr-2"
              >
                <Upload className="h-5 w-5 mr-1.5" />
                Upload
              </Button>
            ) : null}

            {hasOverlays ? (
              <Button
                variant={showOverlays ? "default" : "ghost"}
                size="sm"
                onClick={() => setShowOverlays((v) => !v)}
                className="h-9 px-3 mr-2"
              >
                {showOverlays ? (
                  <>
                    <Eye className="h-4 w-4 mr-1.5" />
                    Hide Fields
                  </>
                ) : (
                  <>
                    <EyeOff className="h-4 w-4 mr-1.5" />
                    Show Fields
                  </>
                )}
              </Button>
            ) : null}

            <div className="flex items-center gap-2 mr-3">
              <span className="text-sm text-gray-400">Page</span>
              <Input
                type="text"
                value={pageInput}
                onChange={(e) => setPageInput(e.target.value)}
                onBlur={handlePageInputBlur}
                onKeyDown={handlePageInputKeyDown}
                disabled={isLoading}
                className="w-14 h-9 text-center text-sm bg-[#1a1a1a] border-[#3a3a3a] text-gray-200"
              />
              <span className="text-sm text-gray-400">/ {numPages || "-"}</span>
            </div>

            {showZoom ? (
              <>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={zoomOut}
                  disabled={scale <= 0.5 || isLoading}
                  className="text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
                  title="Zoom out"
                >
                  <ZoomOut className="h-6 w-6" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={zoomIn}
                  disabled={scale >= 3.0 || isLoading}
                  className="text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
                  title="Zoom in"
                >
                  <ZoomIn className="h-6 w-6" />
                </Button>
              </>
            ) : null}

            <Button
              variant="ghost"
              size="icon"
              onClick={() => setSearchOpen((v) => !v)}
              disabled={isLoading}
              className="text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
              title="Search (⌘F)"
            >
              <Search className="h-6 w-6" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={rotateClockwise}
              disabled={isLoading}
              className="text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
              title="Rotate"
            >
              <RotateCw className="h-6 w-6" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              onClick={handleDownload}
              disabled={isLoading || isDownloading}
              className="text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
              title="Descargar"
            >
              <Download className="h-6 w-6" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              disabled={isLoading}
              className="text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
              title="More options"
            >
              <MoreHorizontal className="h-6 w-6" />
            </Button>
          </div>
        </div>
      )}

      {searchOpen ? (
        <div className="flex items-center gap-2 px-6 py-2 bg-[#222] border-b border-[#3a3a3a]">
          <Search className="h-4 w-4 text-gray-400" />
          <Input
            ref={searchInputRef}
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") navigateSearch(e.shiftKey ? -1 : 1);
            }}
            placeholder="Buscar en el documento…"
            className="flex-1 h-8 text-sm bg-[#1a1a1a] border-[#3a3a3a] text-gray-200"
          />
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigateSearch(-1)}
            disabled={!searchTerm}
            className="h-8 w-8 text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
            title="Anterior (Shift+Enter)"
          >
            <ChevronUp className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => navigateSearch(1)}
            disabled={!searchTerm}
            className="h-8 w-8 text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
            title="Siguiente (Enter)"
          >
            <ChevronDown className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              setSearchOpen(false);
              setSearchTerm("");
            }}
            className="h-8 w-8 text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
            title="Cerrar (Esc)"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      ) : null}

      <div
        ref={containerRef}
        className="relative flex-1 overflow-auto bg-[#525659] py-6 scrollbar-subtle"
      >
        {isLoading && !error ? <PdfViewerLoading variant="overlay" /> : null}
        {error ? (
          <div className="flex flex-col items-center justify-center gap-2 text-center p-8">
            <p className="text-sm text-red-400 font-medium">{t("loadError")}</p>
            <p className="text-xs text-gray-400">{error.message}</p>
          </div>
        ) : (
          <div className="min-w-min mx-auto w-fit flex flex-col gap-4">
            <Document
              file={memoizedFile}
              onLoadSuccess={onDocumentLoadSuccess}
              onLoadError={onDocumentLoadError}
              loading={null}
              error={
                <div className="flex items-center justify-center p-8">
                  <div className="text-sm text-red-400">{t("loadError")}</div>
                </div>
              }
              className="pdf-document flex flex-col gap-4"
            >
              {Array.from({ length: numPages }, (_, i) => i + 1).map((p) => {
                const dims = pageDims.get(p);
                const pageBoxes = boxesByPage.get(p) ?? [];
                const targetPage =
                  initialPage && initialPage >= 1 && initialPage <= numPages
                    ? initialPage
                    : 1;
                const isInitialTarget =
                  p === targetPage &&
                  targetPage > 1 &&
                  !didJumpToInitialPageRef.current;
                const shouldRender = renderedPages.has(p);
                return (
                  <div
                    key={p}
                    ref={setPageRef(p)}
                    data-page-idx={p}
                    className="relative"
                  >
                    {shouldRender ? (
                      <Page
                        pageNumber={p}
                        width={
                          containerWidth ? containerWidth * scale : undefined
                        }
                        rotate={rotation}
                        devicePixelRatio={dpr}
                        className="shadow-2xl"
                        loading={
                          <div
                            className="flex items-center justify-center bg-white"
                            style={{
                              width: `${placeholderWidth}px`,
                              height: `${placeholderHeight}px`,
                            }}
                          >
                            <div className="text-sm text-gray-600">
                              Loading page {p}…
                            </div>
                          </div>
                        }
                        onRenderSuccess={
                          isInitialTarget
                            ? () => jumpToInitialPage(targetPage)
                            : undefined
                        }
                        customTextRenderer={textRenderer}
                        renderTextLayer={true}
                        renderAnnotationLayer={true}
                      />
                    ) : (
                      <div
                        className="flex items-center justify-center bg-[#3f4144] text-gray-400 shadow-2xl select-none"
                        style={{
                          width: `${placeholderWidth}px`,
                          height: `${placeholderHeight}px`,
                        }}
                      >
                        <span className="text-sm tabular-nums">Page {p}</span>
                      </div>
                    )}

                    <span
                      className="absolute right-2 top-2 rounded px-2 py-0.5 text-[10px] font-medium text-white tabular-nums"
                      style={{
                        background: shouldRender
                          ? "rgba(22, 163, 74, 0.85)"
                          : "rgba(0, 0, 0, 0.6)",
                      }}
                    >
                      {shouldRender ? "● " : "○ "}
                      {p} / {numPages}
                    </span>

                    {hasOverlays && showOverlays && dims && shouldRender ? (
                      <div
                        className="absolute top-0 left-0 pointer-events-none"
                        style={{ width: `${dims.w}px`, height: `${dims.h}px` }}
                      >
                        {pageBoxes.map((box) => (
                          <BoundingBoxOverlay
                            key={box.id}
                            box={box}
                            pageWidth={dims.w}
                            pageHeight={dims.h}
                            rotation={rotation}
                            isHovered={hoveredBoxId === box.id}
                            isActive={activeBoxId === box.id}
                            onHover={setHoveredBoxId}
                            onClick={onBoxClick}
                          />
                        ))}
                      </div>
                    ) : null}
                  </div>
                );
              })}
            </Document>
          </div>
        )}
      </div>
    </div>
  );
}

interface BoundingBoxOverlayProps {
  box: CoordinateBox;
  pageWidth: number;
  pageHeight: number;
  rotation: Rotation;
  isHovered: boolean;
  isActive: boolean;
  onHover: (id: string | null) => void;
  onClick?: (id: string) => void;
}

function BoundingBoxOverlay({
  box,
  pageWidth,
  pageHeight,
  rotation,
  isHovered,
  isActive,
  onHover,
  onClick,
}: BoundingBoxOverlayProps) {
  // Coordinates from extraction are in the original page orientation;
  // they must be rotated to match the rendered canvas so the overlay
  // lands on the right region.
  const b = rotateBoundingBox(box.boundingBox, rotation);
  const left = b.Left * pageWidth;
  const top = b.Top * pageHeight;
  const width = b.Width * pageWidth;
  const height = b.Height * pageHeight;

  const tier = confidenceBand(box.confidence);
  const tierStyle = TIER_STYLES[tier];
  const bgColor = isActive
    ? ACTIVE_BG
    : isHovered
      ? tierStyle.bgHover
      : tierStyle.bg;
  const borderColor = isActive ? ACTIVE_BORDER : tierStyle.border;
  // Low-confidence boxes get a dashed border so they pop visually
  // beyond just the red fill — color alone is not accessible.
  const borderStyle = tier === "low" ? "dashed" : "solid";
  const ringShadow = isActive
    ? `0 0 0 2px ${ACTIVE_RING}, 0 4px 16px rgba(0,0,0,0.25)`
    : isHovered
      ? `0 0 0 2px ${tierStyle.ring}, 0 2px 10px rgba(0,0,0,0.18)`
      : "0 1px 2px rgba(0, 0, 0, 0.18)";

  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      aria-label={`${box.type}: ${box.text}`}
      className="absolute pointer-events-auto cursor-pointer transition-all duration-150"
      style={{
        left: `${left}px`,
        top: `${top}px`,
        width: `${width}px`,
        height: `${height}px`,
        backgroundColor: bgColor,
        border: `1px ${borderStyle} ${borderColor}`,
        borderRadius: "3px",
        boxShadow: ringShadow,
        zIndex: isActive ? 25 : isHovered ? 20 : 10,
      }}
      onMouseEnter={() => onHover(box.id)}
      onMouseLeave={() => onHover(null)}
      onClick={(e) => {
        e.stopPropagation();
        onClick?.(box.id);
      }}
      onKeyDown={(e) => {
        if (!onClick) return;
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onClick(box.id);
        }
      }}
      title={`${box.type}: ${box.text} (${formatConfidencePct(box.confidence)}%)`}
    >
      {(isHovered || isActive) && box.text ? (
        <div
          className="absolute bottom-full left-0 mb-2 px-3 py-2 bg-gray-900/95 backdrop-blur-sm text-white text-xs rounded-md shadow-xl whitespace-nowrap z-30 border border-gray-700"
          style={{ pointerEvents: "none" }}
        >
          <div className="font-semibold text-sm mb-1">{box.type}</div>
          <div className="text-gray-200 max-w-xs truncate">{box.text}</div>
          <div className="text-gray-400 text-[10px] mt-1 tabular-nums">
            {formatConfidencePct(box.confidence)}% confidence
          </div>
        </div>
      ) : null}
    </div>
  );
}
