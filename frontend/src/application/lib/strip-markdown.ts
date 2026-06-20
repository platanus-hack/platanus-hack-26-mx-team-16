/**
 * Convert markdown source to a single-line plain text snippet for use in
 * compact UI surfaces (subtitles, breadcrumbs, table cells). Strips inline
 * emphasis, links, images, code spans, headings, list markers, and
 * collapses whitespace.
 *
 * Not a full markdown renderer — use a real renderer (tiptap/remark) when
 * formatting matters. This is the right tool when a one-liner is all
 * you can show.
 */
export function stripMarkdown(input: string | null | undefined): string {
  if (!input) return "";
  return (
    input
      // Code blocks: keep inner text without backticks
      .replace(/```[\s\S]*?```/g, (m) => m.replace(/```\w*\n?|```/g, ""))
      // Images ![alt](url) → alt
      .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
      // Links [text](url) → text
      .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
      // Inline code `x` → x
      .replace(/`([^`]+)`/g, "$1")
      // Bold/italic markers
      .replace(/(\*\*|__)(.*?)\1/g, "$2")
      .replace(/(\*|_)(.*?)\1/g, "$2")
      // Strikethrough
      .replace(/~~(.*?)~~/g, "$1")
      // Headings / blockquotes / list markers at line start
      .replace(/^\s{0,3}(#{1,6}\s+|>\s+|[-*+]\s+|\d+\.\s+)/gm, "")
      // HTML tags
      .replace(/<\/?[^>]+>/g, "")
      // Collapse whitespace
      .replace(/\s+/g, " ")
      .trim()
  );
}
