"use client";

import { Download, Eye, EyeOff, ZoomIn, ZoomOut } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { CoordinateBox } from "@/src/domain/entities/textract";
import { Button } from "./button";

const HIGHLIGHT_BG = "rgba(16, 185, 129, 0.28)";
const HIGHLIGHT_BG_HOVER = "rgba(16, 185, 129, 0.42)";
const HIGHLIGHT_BORDER = "rgba(5, 150, 105, 0.7)";
const ACTIVE_BG = "rgba(37, 99, 235, 0.42)";
const ACTIVE_BORDER = "rgba(29, 78, 216, 0.85)";

export interface ImageViewerProps {
  url: string;
  httpHeaders?: Record<string, string>;
  fileName?: string;
  className?: string;
  showControls?: boolean;
  showZoom?: boolean;
  initialScale?: number;
  onLoadSuccess?: () => void;
  onLoadError?: (error: Error) => void;
  overlayBoxes?: CoordinateBox[];
  activeBoxId?: string | null;
  onBoxClick?: (boxId: string) => void;
}

export function ImageViewer({
  url,
  httpHeaders,
  fileName,
  className = "",
  showControls = true,
  showZoom = true,
  initialScale = 1.0,
  onLoadSuccess,
  onLoadError,
  overlayBoxes,
  activeBoxId,
  onBoxClick,
}: ImageViewerProps) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [scale, setScale] = useState(initialScale);
  const [showOverlays, setShowOverlays] = useState(true);
  const [hoveredBoxId, setHoveredBoxId] = useState<string | null>(null);
  const [imgDims, setImgDims] = useState<{ w: number; h: number } | null>(null);

  const imgRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    let created: string | null = null;

    setIsLoading(true);
    setError(null);
    setBlobUrl(null);

    fetch(url, { headers: httpHeaders })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.blob();
      })
      .then((blob) => {
        if (!active) return;
        created = URL.createObjectURL(blob);
        setBlobUrl(created);
        setIsLoading(false);
        onLoadSuccess?.();
      })
      .catch((err: Error) => {
        if (!active) return;
        setError(err);
        setIsLoading(false);
        onLoadError?.(err);
      });

    return () => {
      active = false;
      if (created) URL.revokeObjectURL(created);
    };
  }, [url, httpHeaders, onLoadSuccess, onLoadError]);

  useEffect(() => {
    const img = imgRef.current;
    if (!img || !blobUrl) return;
    const observer = new ResizeObserver(() => {
      setImgDims({ w: img.clientWidth, h: img.clientHeight });
    });
    observer.observe(img);
    return () => observer.disconnect();
  }, [blobUrl]);

  useEffect(() => {
    if (!activeBoxId || !imgDims) return;
    const box = (overlayBoxes ?? []).find((b) => b.id === activeBoxId);
    if (!box || !containerRef.current) return;
    const container = containerRef.current;
    const bboxTopInImg = box.boundingBox.Top * imgDims.h * scale;
    const bboxHeight = box.boundingBox.Height * imgDims.h * scale;
    const viewportH = container.clientHeight;
    const bboxCenter = bboxTopInImg + bboxHeight / 2;
    container.scrollTo({
      top: Math.max(0, bboxCenter - viewportH / 2),
      behavior: "smooth",
    });
  }, [activeBoxId, overlayBoxes, imgDims, scale]);

  const handleDownload = useCallback(() => {
    if (!blobUrl) return;
    const a = document.createElement("a");
    a.href = blobUrl;
    a.download = fileName ?? "image";
    a.click();
  }, [blobUrl, fileName]);

  const zoomIn = () => setScale((s) => Math.min(s + 0.1, 3.0));
  const zoomOut = () => setScale((s) => Math.max(s - 0.1, 0.5));

  const hasOverlays = (overlayBoxes?.length ?? 0) > 0;
  const displayFileName = fileName ?? url.split("/").pop() ?? "image";

  return (
    <div className={`flex flex-col h-full bg-[#1a1a1a] ${className}`}>
      {showControls && (
        <div className="flex items-center justify-between px-6 py-3.5 bg-[#2a2a2a] border-b border-[#3a3a3a]">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-200 font-medium">
              {displayFileName}
            </span>
            {hasOverlays && (
              <span className="text-xs text-gray-400">
                ({overlayBoxes?.length ?? 0} fields detected)
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            {hasOverlays && (
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
            )}

            {showZoom && (
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
            )}

            <Button
              variant="ghost"
              size="icon"
              onClick={handleDownload}
              disabled={!blobUrl}
              className="text-gray-400 hover:text-gray-200 hover:bg-[#3a3a3a]"
              title="Download"
            >
              <Download className="h-6 w-6" />
            </Button>
          </div>
        </div>
      )}

      <div
        ref={containerRef}
        className="flex-1 overflow-auto bg-[#525659] flex items-start justify-center py-6"
      >
        {error ? (
          <div className="flex flex-col items-center justify-center gap-2 text-center p-8">
            <p className="text-sm text-red-400 font-medium">
              Failed to load image
            </p>
            <p className="text-xs text-gray-400">{error.message}</p>
          </div>
        ) : isLoading ? (
          <div className="flex items-center justify-center p-8">
            <p className="text-sm text-gray-400">Loading image…</p>
          </div>
        ) : blobUrl ? (
          <div
            className="relative shadow-2xl"
            style={{
              transform: `scale(${scale})`,
              transformOrigin: "top center",
              marginBottom: `${(scale - 1) * (imgDims?.h ?? 0)}px`,
            }}
          >
            <img
              ref={imgRef}
              src={blobUrl}
              alt={displayFileName}
              className="block max-w-full"
              onLoad={() => {
                const img = imgRef.current;
                if (img)
                  setImgDims({ w: img.clientWidth, h: img.clientHeight });
              }}
              draggable={false}
            />

            {hasOverlays && showOverlays && imgDims && (
              <div
                className="absolute top-0 left-0 pointer-events-none"
                style={{ width: `${imgDims.w}px`, height: `${imgDims.h}px` }}
              >
                {(overlayBoxes ?? []).map((box) => (
                  <ImageBoundingBoxOverlay
                    key={box.id}
                    box={box}
                    imgWidth={imgDims.w}
                    imgHeight={imgDims.h}
                    isHovered={hoveredBoxId === box.id}
                    isActive={activeBoxId === box.id}
                    onHover={setHoveredBoxId}
                    onClick={onBoxClick}
                  />
                ))}
              </div>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

interface ImageBoundingBoxOverlayProps {
  box: CoordinateBox;
  imgWidth: number;
  imgHeight: number;
  isHovered: boolean;
  isActive: boolean;
  onHover: (id: string | null) => void;
  onClick?: (id: string) => void;
}

function ImageBoundingBoxOverlay({
  box,
  imgWidth,
  imgHeight,
  isHovered,
  isActive,
  onHover,
  onClick,
}: ImageBoundingBoxOverlayProps) {
  const left = box.boundingBox.Left * imgWidth;
  const top = box.boundingBox.Top * imgHeight;
  const width = box.boundingBox.Width * imgWidth;
  const height = box.boundingBox.Height * imgHeight;

  const bgColor = isActive
    ? ACTIVE_BG
    : isHovered
      ? HIGHLIGHT_BG_HOVER
      : HIGHLIGHT_BG;

  const ringShadow = isActive
    ? "0 0 0 2px rgba(37, 99, 235, 0.55), 0 4px 16px rgba(0,0,0,0.25)"
    : isHovered
      ? "0 0 0 2px rgba(16, 185, 129, 0.45), 0 2px 10px rgba(0,0,0,0.18)"
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
        border: `1px solid ${isActive ? ACTIVE_BORDER : HIGHLIGHT_BORDER}`,
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
      title={`${box.type}: ${box.text}`}
    >
      {(isHovered || isActive) && box.text && (
        <div
          className="absolute bottom-full left-0 mb-2 px-3 py-2 bg-gray-900/95 backdrop-blur-sm text-white text-xs rounded-md shadow-xl whitespace-nowrap z-30 border border-gray-700"
          style={{ pointerEvents: "none" }}
        >
          <div className="font-semibold text-sm mb-1">{box.type}</div>
          <div className="text-gray-200 max-w-xs truncate">{box.text}</div>
        </div>
      )}
    </div>
  );
}
