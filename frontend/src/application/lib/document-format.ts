export type DocumentFormat = "pdf" | "image" | "unknown";

const IMAGE_MIMES = new Set([
  "image/png",
  "image/jpeg",
  "image/jpg",
  "image/webp",
]);

const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp"]);

export function resolveFormat(
  mimeType?: string | null,
  fileName?: string | null,
): DocumentFormat {
  if (mimeType) {
    if (mimeType === "application/pdf") return "pdf";
    if (IMAGE_MIMES.has(mimeType)) return "image";
  }
  if (fileName) {
    const dot = fileName.lastIndexOf(".");
    if (dot !== -1) {
      const ext = fileName.slice(dot).toLowerCase();
      if (ext === ".pdf") return "pdf";
      if (IMAGE_EXTS.has(ext)) return "image";
    }
  }
  return "unknown";
}
