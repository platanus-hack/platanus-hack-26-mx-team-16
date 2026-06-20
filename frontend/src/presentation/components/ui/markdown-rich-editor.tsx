"use client";

import {
  Bold,
  Code,
  Heading1,
  Heading2,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Quote,
  Redo,
  Strikethrough,
  Undo,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Extension } from "@tiptap/core";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import Link from "@tiptap/extension-link";
import StarterKit from "@tiptap/starter-kit";
import { Plugin } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { Node as ProseMirrorNode } from "@tiptap/pm/model";
import { Markdown } from "tiptap-markdown";
import { cn } from "@/src/application/lib/utils";

interface SuggestionState {
  query: string;
  from: number;
  to: number;
  left: number;
  top: number;
  activeIdx: number;
}

interface MarkdownRichEditorProps {
  value: string;
  onChange: (markdown: string) => void;
  placeholder?: string;
  className?: string;
  minHeight?: number;
  /**
   * If provided, typing `{{` opens an autocomplete popup with these paths.
   * Selecting one inserts `{{path}}` at the cursor.
   */
  paths?: string[];
}

const TOKEN_TRIGGER = /\{\{\s*([\w.\-]*)$/;
const TOKEN_MATCH = /\{\{\s*[\w.\-]+\s*\}\}/g;

function buildTokenDecorations(doc: ProseMirrorNode): DecorationSet {
  const decorations: Decoration[] = [];
  doc.descendants((node, pos) => {
    if (!node.isText || !node.text) return;
    TOKEN_MATCH.lastIndex = 0;
    let m: RegExpExecArray | null;
    while ((m = TOKEN_MATCH.exec(node.text)) !== null) {
      const from = pos + m.index;
      const to = from + m[0].length;
      decorations.push(
        Decoration.inline(from, to, {
          class:
            "rounded px-1 py-0.5 bg-primary/10 text-primary font-mono text-[0.85em]",
        })
      );
    }
  });
  return DecorationSet.create(doc, decorations);
}

const TokenHighlight = Extension.create({
  name: "tokenHighlight",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        state: {
          init: (_config, { doc }) => buildTokenDecorations(doc),
          apply: (tr, old) =>
            tr.docChanged ? buildTokenDecorations(tr.doc) : old,
        },
        props: {
          decorations(state) {
            return this.getState(state);
          },
        },
      }),
    ];
  },
});

export function MarkdownRichEditor({
  value,
  onChange,
  placeholder,
  className,
  minHeight = 180,
  paths,
}: MarkdownRichEditorProps) {
  const [suggestion, setSuggestion] = useState<SuggestionState | null>(null);
  const suggestionRef = useRef<SuggestionState | null>(null);
  const pathsRef = useRef<string[] | undefined>(paths);
  pathsRef.current = paths;

  useEffect(() => {
    suggestionRef.current = suggestion;
  }, [suggestion]);

  const filteredPaths = useMemo(() => {
    if (!suggestion || !paths || paths.length === 0) return [];
    const q = suggestion.query.toLowerCase();
    return paths
      .filter((p) => p.toLowerCase().includes(q))
      .slice(0, 10);
  }, [paths, suggestion]);
  const filteredRef = useRef(filteredPaths);
  filteredRef.current = filteredPaths;

  const insertTokenRef = useRef<((path: string) => void) | null>(null);

  const updateSuggestion = useCallback((ed: Editor) => {
    if (!pathsRef.current?.length) {
      setSuggestion(null);
      return;
    }
    const { from, empty } = ed.state.selection;
    if (!empty) {
      setSuggestion(null);
      return;
    }
    const $pos = ed.state.doc.resolve(from);
    const before = $pos.parent.textBetween(
      Math.max(0, $pos.parentOffset - 80),
      $pos.parentOffset,
      undefined,
      "￼"
    );
    const match = TOKEN_TRIGGER.exec(before);
    if (!match) {
      setSuggestion(null);
      return;
    }
    const matchStart = from - match[0].length;
    const coords = ed.view.coordsAtPos(matchStart);
    setSuggestion((prev) => {
      const query = match[1] || "";
      return {
        query,
        from: matchStart,
        to: from,
        left: coords.left,
        top: coords.bottom,
        activeIdx: prev && prev.query === query ? prev.activeIdx : 0,
      };
    });
  }, []);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Link.configure({
        openOnClick: false,
        HTMLAttributes: { class: "text-blue-600 underline" },
      }),
      Markdown.configure({
        html: false,
        linkify: true,
        breaks: true,
        transformPastedText: true,
      }),
      TokenHighlight,
    ],
    content: value || "",
    editorProps: {
      attributes: {
        class: cn(
          "tiptap prose prose-sm dark:prose-invert max-w-none px-3 py-2 text-base md:text-sm leading-snug focus:outline-none",
          "[&_p]:my-1 [&_h1]:mt-3 [&_h1]:mb-1 [&_h1]:text-lg [&_h2]:mt-3 [&_h2]:mb-1 [&_h2]:text-base [&_ul]:my-1 [&_ol]:my-1 [&_blockquote]:my-1"
        ),
      },
      handleKeyDown: (_view, event) => {
        const sug = suggestionRef.current;
        const filtered = filteredRef.current;
        if (!sug || filtered.length === 0) return false;
        if (event.key === "ArrowDown") {
          setSuggestion((s) =>
            s
              ? {
                  ...s,
                  activeIdx: Math.min(filtered.length - 1, s.activeIdx + 1),
                }
              : null
          );
          return true;
        }
        if (event.key === "ArrowUp") {
          setSuggestion((s) =>
            s ? { ...s, activeIdx: Math.max(0, s.activeIdx - 1) } : null
          );
          return true;
        }
        if (event.key === "Enter" || event.key === "Tab") {
          insertTokenRef.current?.(filtered[sug.activeIdx]);
          return true;
        }
        if (event.key === "Escape") {
          setSuggestion(null);
          return true;
        }
        return false;
      },
    },
    onUpdate: ({ editor }) => {
      const md =
        (editor.storage as { markdown?: { getMarkdown?: () => string } })
          .markdown?.getMarkdown?.() ?? "";
      onChange(md);
      updateSuggestion(editor);
    },
    onSelectionUpdate: ({ editor }) => {
      updateSuggestion(editor);
    },
    immediatelyRender: false,
  });

  const insertToken = useCallback(
    (path: string) => {
      const sug = suggestionRef.current;
      if (!sug || !editor) return;
      editor
        .chain()
        .focus()
        .insertContentAt({ from: sug.from, to: sug.to }, `{{${path}}} `)
        .run();
      setSuggestion(null);
    },
    [editor]
  );

  useEffect(() => {
    insertTokenRef.current = insertToken;
  }, [insertToken]);

  useEffect(() => {
    if (!editor) return;
    const current =
      (editor.storage as { markdown?: { getMarkdown?: () => string } })
        .markdown?.getMarkdown?.() ?? "";
    if (value !== current) {
      editor.commands.setContent(value || "", { emitUpdate: false });
    }
  }, [editor, value]);

  if (!editor) {
    return (
      <div
        className={cn(
          "rounded-md border border-input bg-background",
          className
        )}
        style={{ minHeight }}
      />
    );
  }

  return (
    <div
      className={cn(
        "rounded-md border border-input bg-background flex flex-col",
        className
      )}
    >
      <Toolbar editor={editor} />
      <EditorContent
        editor={editor}
        className="flex-1 overflow-y-auto"
        style={{ minHeight }}
        data-placeholder={placeholder}
      />
      {suggestion && filteredPaths.length > 0 && (
        <SuggestionPopup
          items={filteredPaths}
          activeIdx={suggestion.activeIdx}
          left={suggestion.left}
          top={suggestion.top}
          onPick={insertToken}
        />
      )}
    </div>
  );
}

function SuggestionPopup({
  items,
  activeIdx,
  left,
  top,
  onPick,
}: {
  items: string[];
  activeIdx: number;
  left: number;
  top: number;
  onPick: (path: string) => void;
}) {
  if (typeof document === "undefined") return null;
  return createPortal(
    <div
      className="fixed z-50 rounded-md border border-border bg-popover text-popover-foreground shadow-md py-1 min-w-[220px] max-w-[320px] max-h-60 overflow-y-auto"
      style={{ left, top: top + 4 }}
    >
      {items.map((path, i) => (
        <button
          key={path}
          type="button"
          onMouseDown={(e) => {
            e.preventDefault();
            onPick(path);
          }}
          className={cn(
            "block w-full text-left px-3 py-1.5 text-xs font-mono cursor-pointer",
            i === activeIdx
              ? "bg-accent text-accent-foreground"
              : "hover:bg-muted/60"
          )}
        >
          {path}
        </button>
      ))}
    </div>,
    document.body
  );
}

function ToolbarButton({
  active,
  disabled,
  onClick,
  ariaLabel,
  children,
}: {
  active?: boolean;
  disabled?: boolean;
  onClick: () => void;
  ariaLabel: string;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      aria-label={ariaLabel}
      aria-pressed={active}
      className={cn(
        "inline-flex items-center justify-center rounded p-1.5 text-muted-foreground hover:bg-muted/60 hover:text-foreground transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed",
        active && "bg-muted text-foreground"
      )}
    >
      {children}
    </button>
  );
}

function Toolbar({ editor }: { editor: Editor }) {
  const setLink = useCallback(() => {
    const previousUrl = editor.getAttributes("link").href as string | undefined;
    const url = window.prompt("URL", previousUrl ?? "");
    if (url === null) return;
    if (url === "") {
      editor.chain().focus().extendMarkRange("link").unsetLink().run();
      return;
    }
    editor
      .chain()
      .focus()
      .extendMarkRange("link")
      .setLink({ href: url })
      .run();
  }, [editor]);

  return (
    <div className="flex flex-wrap items-center gap-0.5 border-b border-border/60 px-1 py-1 bg-muted/20">
      <ToolbarButton
        ariaLabel="Bold"
        active={editor.isActive("bold")}
        onClick={() => editor.chain().focus().toggleBold().run()}
      >
        <Bold className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Italic"
        active={editor.isActive("italic")}
        onClick={() => editor.chain().focus().toggleItalic().run()}
      >
        <Italic className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Strikethrough"
        active={editor.isActive("strike")}
        onClick={() => editor.chain().focus().toggleStrike().run()}
      >
        <Strikethrough className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Inline code"
        active={editor.isActive("code")}
        onClick={() => editor.chain().focus().toggleCode().run()}
      >
        <Code className="h-3.5 w-3.5" />
      </ToolbarButton>
      <span className="mx-0.5 h-4 w-px bg-border/60" />
      <ToolbarButton
        ariaLabel="Heading 1"
        active={editor.isActive("heading", { level: 1 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()}
      >
        <Heading1 className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Heading 2"
        active={editor.isActive("heading", { level: 2 })}
        onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
      >
        <Heading2 className="h-3.5 w-3.5" />
      </ToolbarButton>
      <span className="mx-0.5 h-4 w-px bg-border/60" />
      <ToolbarButton
        ariaLabel="Bulleted list"
        active={editor.isActive("bulletList")}
        onClick={() => editor.chain().focus().toggleBulletList().run()}
      >
        <List className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Ordered list"
        active={editor.isActive("orderedList")}
        onClick={() => editor.chain().focus().toggleOrderedList().run()}
      >
        <ListOrdered className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Quote"
        active={editor.isActive("blockquote")}
        onClick={() => editor.chain().focus().toggleBlockquote().run()}
      >
        <Quote className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Link"
        active={editor.isActive("link")}
        onClick={setLink}
      >
        <LinkIcon className="h-3.5 w-3.5" />
      </ToolbarButton>
      <span className="ml-auto" />
      <ToolbarButton
        ariaLabel="Undo"
        disabled={!editor.can().undo()}
        onClick={() => editor.chain().focus().undo().run()}
      >
        <Undo className="h-3.5 w-3.5" />
      </ToolbarButton>
      <ToolbarButton
        ariaLabel="Redo"
        disabled={!editor.can().redo()}
        onClick={() => editor.chain().focus().redo().run()}
      >
        <Redo className="h-3.5 w-3.5" />
      </ToolbarButton>
    </div>
  );
}
