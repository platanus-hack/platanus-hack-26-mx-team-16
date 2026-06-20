"use client";

import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/src/application/lib/utils";

export interface DoctypeRef {
  name: string;
  paths: string[];
}

interface PromptEditorProps {
  value: string;
  onChange: (value: string) => void;
  /** Paths to reference inside `{{...}}`. Used for the simple mode (e.g. doctype validation rules). */
  paths?: string[];
  /** Doctypes available via `@name[.path]` references (analysis rules). */
  doctypes?: DoctypeRef[];
  /** System variable names accessible via `{{name}}` (extensible). */
  systemVariables?: string[];
  placeholder?: string;
  className?: string;
  minHeightClassName?: string;
}

// Token matchers (completed references rendered in the backdrop)
const DOCTYPE_TOKEN = /@([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)*)/g;
const BRACE_TOKEN = /\{\{\s*([a-zA-Z_][a-zA-Z0-9_.\-]*)\s*\}\}/g;

const EMPTY_PATHS: string[] = [];
const EMPTY_DOCTYPES: DoctypeRef[] = [];
const EMPTY_SYSVARS: string[] = [];

// Caret-before triggers
const DOCTYPE_TRIGGER = /@([a-zA-Z0-9_.]*)$/;
const BRACE_TRIGGER = /\{\{\s*([a-zA-Z0-9_.\-]*)$/;

interface Suggestion {
  display: string;
  insert: string;
}

interface PopupState {
  start: number;
  end: number;
  suggestions: Suggestion[];
  activeIdx: number;
  pos: { left: number; top: number };
  kind: "doctype" | "brace";
  query: string;
}

function getCaretCoords(ta: HTMLTextAreaElement, position: number) {
  const div = document.createElement("div");
  const style = window.getComputedStyle(ta);
  const props = [
    "boxSizing",
    "width",
    "height",
    "overflowX",
    "overflowY",
    "borderTopWidth",
    "borderRightWidth",
    "borderBottomWidth",
    "borderLeftWidth",
    "borderStyle",
    "paddingTop",
    "paddingRight",
    "paddingBottom",
    "paddingLeft",
    "fontStyle",
    "fontVariant",
    "fontWeight",
    "fontStretch",
    "fontSize",
    "fontSizeAdjust",
    "lineHeight",
    "fontFamily",
    "textAlign",
    "textTransform",
    "textIndent",
    "textDecoration",
    "letterSpacing",
    "wordSpacing",
    "tabSize",
    "MozTabSize",
  ] as const;
  div.style.position = "absolute";
  div.style.visibility = "hidden";
  div.style.whiteSpace = "pre-wrap";
  div.style.wordWrap = "break-word";
  div.style.top = "0";
  div.style.left = "-9999px";
  props.forEach((p) => {
    // @ts-expect-error index signature
    div.style[p] = style[p];
  });
  div.style.width = ta.clientWidth + "px";
  div.textContent = ta.value.substring(0, position);
  const span = document.createElement("span");
  span.textContent = ta.value.substring(position) || ".";
  div.appendChild(span);
  document.body.appendChild(div);
  const left = span.offsetLeft - ta.scrollLeft;
  const top = span.offsetTop - ta.scrollTop;
  const lineHeight = parseInt(style.lineHeight || "20", 10) || 20;
  document.body.removeChild(div);
  return { left, top, lineHeight };
}

/** Render `text` with the substring that matches `query` wrapped in <strong>. */
function renderMatch(text: string, query: string): ReactNode {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <strong className="font-semibold text-foreground">
        {text.slice(idx, idx + query.length)}
      </strong>
      {text.slice(idx + query.length)}
    </>
  );
}

export function PromptEditor({
  value,
  onChange,
  paths = EMPTY_PATHS,
  doctypes = EMPTY_DOCTYPES,
  systemVariables = EMPTY_SYSVARS,
  placeholder,
  className,
  minHeightClassName = "min-h-32",
}: PromptEditorProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);
  const popupListRef = useRef<HTMLUListElement>(null);
  const [popup, setPopup] = useState<PopupState | null>(null);
  const suppressCaretEventRef = useRef(false);
  const skipNextDetectRef = useRef(false);

  const doctypesEnabled = doctypes.length > 0;
  const systemVarsEnabled = systemVariables.length > 0;

  const doctypeByName = useMemo(() => {
    const map = new Map<string, DoctypeRef>();
    doctypes.forEach((d) => map.set(d.name, d));
    return map;
  }, [doctypes]);

  const bracePathSet = useMemo(() => new Set(paths), [paths]);
  const sysvarSet = useMemo(() => new Set(systemVariables), [systemVariables]);

  const isValidDoctypeToken = useCallback(
    (inner: string) => {
      const [name, ...rest] = inner.split(".");
      const dt = doctypeByName.get(name);
      if (!dt) return false;
      if (rest.length === 0) return true;
      return dt.paths.includes(rest.join("."));
    },
    [doctypeByName]
  );

  const isValidBraceToken = useCallback(
    (inner: string) => {
      if (systemVarsEnabled) return sysvarSet.has(inner);
      return bracePathSet.has(inner);
    },
    [bracePathSet, sysvarSet, systemVarsEnabled]
  );

  const invalidHintFor = useCallback(
    (kind: "doctype" | "brace"): string => {
      if (kind === "brace") {
        if (systemVarsEnabled) {
          const sample = systemVariables
            .slice(0, 3)
            .map((v) => `{{${v}}}`)
            .join(", ");
          return sample
            ? `Variable desconocida. Válidas: ${sample}…`
            : "Variable desconocida.";
        }
        return "Referencia desconocida.";
      }
      return "Referencia a doctype desconocida.";
    },
    [systemVarsEnabled, systemVariables]
  );

  const renderHighlighted = useCallback(
    (text: string): ReactNode[] => {
      type Match = {
        index: number;
        end: number;
        full: string;
        kind: "doctype" | "brace";
        inner: string;
      };
      const matches: Match[] = [];

      if (doctypesEnabled) {
        const re = new RegExp(DOCTYPE_TOKEN.source, "g");
        let m: RegExpExecArray | null;
        while ((m = re.exec(text)) !== null) {
          matches.push({
            index: m.index,
            end: m.index + m[0].length,
            full: m[0],
            inner: m[1],
            kind: "doctype",
          });
        }
      }
      {
        const re = new RegExp(BRACE_TOKEN.source, "g");
        let m: RegExpExecArray | null;
        while ((m = re.exec(text)) !== null) {
          matches.push({
            index: m.index,
            end: m.index + m[0].length,
            full: m[0],
            inner: m[1],
            kind: "brace",
          });
        }
      }
      matches.sort((a, b) => a.index - b.index);

      const filtered: Match[] = [];
      let cursor = -1;
      for (const m of matches) {
        if (m.index >= cursor) {
          filtered.push(m);
          cursor = m.end;
        }
      }

      const nodes: ReactNode[] = [];
      let last = 0;
      for (const m of filtered) {
        if (m.index > last) {
          nodes.push(
            <span key={`t-${last}`}>{text.slice(last, m.index)}</span>
          );
        }
        const ok =
          m.kind === "doctype"
            ? isValidDoctypeToken(m.inner)
            : isValidBraceToken(m.inner);
        nodes.push(
          <span
            key={`${m.kind}-${m.index}`}
            title={ok ? undefined : invalidHintFor(m.kind)}
            className={cn(
              "rounded-sm font-medium",
              ok
                ? "bg-primary/15 text-primary ring-1 ring-primary/25"
                : "bg-destructive/10 text-destructive ring-1 ring-destructive/25"
            )}
          >
            {m.full}
          </span>
        );
        last = m.end;
      }
      if (last < text.length)
        nodes.push(<span key="tail">{text.slice(last)}</span>);
      if (text.endsWith("\n")) nodes.push(" ");
      return nodes;
    },
    [doctypesEnabled, invalidHintFor, isValidBraceToken, isValidDoctypeToken]
  );

  const tokenAt = useCallback(
    (text: string, caret: number) => {
      const kinds: Array<{ re: RegExp; kind: "doctype" | "brace" }> = [];
      if (doctypesEnabled)
        kinds.push({
          re: new RegExp(DOCTYPE_TOKEN.source, "g"),
          kind: "doctype",
        });
      kinds.push({ re: new RegExp(BRACE_TOKEN.source, "g"), kind: "brace" });
      for (const { re, kind } of kinds) {
        let m: RegExpExecArray | null;
        while ((m = re.exec(text)) !== null) {
          const start = m.index;
          const end = m.index + m[0].length;
          if (caret >= start && caret <= end) {
            return { start, end, inner: m[1], kind };
          }
        }
      }
      return null;
    },
    [doctypesEnabled]
  );

  const suggestionsFor = useCallback(
    (kind: "doctype" | "brace", query: string): Suggestion[] => {
      const q = query.toLowerCase();
      if (kind === "brace") {
        if (systemVarsEnabled) {
          return systemVariables
            .filter((v) => v.toLowerCase().includes(q))
            .slice(0, 10)
            .map((v) => ({ display: `{{${v}}}`, insert: `{{${v}}}` }));
        }
        return paths
          .filter((p) => p.toLowerCase().includes(q))
          .slice(0, 10)
          .map((p) => ({ display: `{{${p}}}`, insert: `{{${p}}}` }));
      }
      const [head, ...rest] = query.split(".");
      if (rest.length === 0) {
        const qh = head.toLowerCase();
        return doctypes
          .filter((d) => d.name.toLowerCase().includes(qh))
          .slice(0, 10)
          .map((d) => ({ display: `@${d.name}`, insert: `@${d.name}` }));
      }
      const dt = doctypeByName.get(head);
      if (!dt) return [];
      const rq = rest.join(".").toLowerCase();
      return dt.paths
        .filter((p) => p.toLowerCase().includes(rq))
        .slice(0, 15)
        .map((p) => ({
          display: `@${dt.name}.${p}`,
          insert: `@${dt.name}.${p}`,
        }));
    },
    [doctypeByName, doctypes, paths, systemVariables, systemVarsEnabled]
  );

  const closePopup = useCallback(() => setPopup(null), []);

  const openPopup = useCallback(
    (kind: "doctype" | "brace", start: number, end: number, query: string) => {
      const suggestions = suggestionsFor(kind, query);
      const ta = textareaRef.current;
      let pos = { left: 0, top: 0 };
      if (ta) {
        const { left, top, lineHeight } = getCaretCoords(ta, start);
        const rect = ta.getBoundingClientRect();
        pos = { left: rect.left + left, top: rect.top + top + lineHeight + 4 };
      }
      setPopup((prev) => {
        const sameContext =
          prev &&
          prev.kind === kind &&
          prev.start === start &&
          prev.end === end;
        return {
          start,
          end,
          suggestions,
          activeIdx: sameContext
            ? Math.min(prev.activeIdx, Math.max(suggestions.length - 1, 0))
            : 0,
          pos,
          kind,
          query,
        };
      });
    },
    [suggestionsFor]
  );

  const detect = useCallback(
    (text: string, caret: number) => {
      const before = text.slice(0, caret);
      const brace = before.match(BRACE_TRIGGER);
      if (brace) {
        const start = caret - brace[0].length;
        openPopup("brace", start, caret, brace[1]);
        return;
      }
      if (doctypesEnabled) {
        const dt = before.match(DOCTYPE_TRIGGER);
        if (dt) {
          const start = caret - dt[0].length;
          openPopup("doctype", start, caret, dt[1]);
          return;
        }
      }
      closePopup();
    },
    [closePopup, doctypesEnabled, openPopup]
  );

  /** Manually invoked via Ctrl/Cmd+Space. Opens suggestions at caret. */
  const manualTrigger = useCallback(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    const caret = ta.selectionStart ?? 0;
    const tok = tokenAt(ta.value, caret);
    if (tok) {
      openPopup(tok.kind, tok.start, tok.end, "");
      return;
    }
    // Try the natural trigger detection first.
    detect(ta.value, caret);
  }, [detect, openPopup, tokenAt]);

  const applySuggestion = useCallback(
    (s: Suggestion) => {
      if (!popup) return;
      const ta = textareaRef.current;
      const before = value.slice(0, popup.start);
      const after = value.slice(popup.end);
      const next = before + s.insert + after;
      skipNextDetectRef.current = true;
      suppressCaretEventRef.current = true;
      onChange(next);
      closePopup();
      requestAnimationFrame(() => {
        const pos = before.length + s.insert.length;
        ta?.focus();
        ta?.setSelectionRange(pos, pos);
      });
    },
    [closePopup, onChange, popup, value]
  );

  const handleKeyDown: React.KeyboardEventHandler<HTMLTextAreaElement> = (
    e
  ) => {
    // Ctrl/Cmd+Space: manual autocomplete trigger (works regardless of popup state).
    if ((e.ctrlKey || e.metaKey) && e.code === "Space") {
      e.preventDefault();
      manualTrigger();
      return;
    }

    // Backspace on the END of a completed token deletes the whole token.
    if (e.key === "Backspace" && !popup) {
      const ta = textareaRef.current;
      if (!ta) return;
      const caret = ta.selectionStart ?? 0;
      const selEnd = ta.selectionEnd ?? caret;
      if (caret === selEnd) {
        const tok = tokenAt(value, caret);
        if (tok && tok.end === caret) {
          e.preventDefault();
          const next = value.slice(0, tok.start) + value.slice(tok.end);
          skipNextDetectRef.current = true;
          suppressCaretEventRef.current = true;
          onChange(next);
          requestAnimationFrame(() => {
            ta.focus();
            ta.setSelectionRange(tok.start, tok.start);
          });
          return;
        }
      }
    }

    if (!popup) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      suppressCaretEventRef.current = true;
      setPopup((p) =>
        p && p.suggestions.length > 0
          ? { ...p, activeIdx: (p.activeIdx + 1) % p.suggestions.length }
          : p
      );
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      suppressCaretEventRef.current = true;
      setPopup((p) =>
        p && p.suggestions.length > 0
          ? {
              ...p,
              activeIdx:
                (p.activeIdx - 1 + p.suggestions.length) % p.suggestions.length,
            }
          : p
      );
    } else if (e.key === "Enter") {
      if (popup.suggestions.length === 0) return; // let Enter insert a newline
      e.preventDefault();
      suppressCaretEventRef.current = true;
      applySuggestion(popup.suggestions[popup.activeIdx]);
    } else if (e.key === "Tab") {
      // Tab closes the popup and lets the browser move focus naturally.
      closePopup();
    } else if (e.key === "Escape") {
      e.preventDefault();
      closePopup();
    }
  };

  const handleCaretEvent = useCallback(() => {
    if (suppressCaretEventRef.current) {
      suppressCaretEventRef.current = false;
      return;
    }
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart ?? 0;
    const end = ta.selectionEnd ?? start;
    // Non-collapsed selection (user is selecting text): don't hijack with popup.
    if (start !== end) {
      closePopup();
      return;
    }
    detect(ta.value, start);
  }, [closePopup, detect]);

  useEffect(() => {
    if (skipNextDetectRef.current) {
      skipNextDetectRef.current = false;
      return;
    }
    const ta = textareaRef.current;
    if (!ta) return;
    const start = ta.selectionStart ?? value.length;
    const end = ta.selectionEnd ?? start;
    if (start !== end) return;
    detect(value, start);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, paths, doctypes, systemVariables]);

  useLayoutEffect(() => {
    const ta = textareaRef.current;
    const bd = backdropRef.current;
    if (!ta || !bd) return;
    ta.style.height = "auto";
    const h = Math.max(ta.scrollHeight, 128);
    ta.style.height = h + "px";
    bd.style.height = h + "px";
  }, [value]);

  useEffect(() => {
    if (!popup) return;
    const onDismiss = () => closePopup();
    window.addEventListener("scroll", onDismiss, true);
    window.addEventListener("resize", onDismiss);
    return () => {
      window.removeEventListener("scroll", onDismiss, true);
      window.removeEventListener("resize", onDismiss);
    };
  }, [closePopup, popup]);

  // Scroll active suggestion into view when navigating with arrows.
  useEffect(() => {
    if (!popup || !popupListRef.current) return;
    const el = popupListRef.current.querySelector<HTMLLIElement>(
      '[data-active="true"]'
    );
    el?.scrollIntoView({ block: "nearest" });
  }, [popup?.activeIdx, popup]);

  const sharedTypography =
    "font-sans text-sm leading-6 tracking-normal whitespace-pre-wrap break-words";
  const sharedBox = "px-3 py-2 rounded-md border";

  return (
    <div className="relative">
      <div
        ref={backdropRef}
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-0 overflow-hidden text-foreground border-transparent",
          sharedBox,
          sharedTypography,
          minHeightClassName,
          className
        )}
      >
        {renderHighlighted(value)}
      </div>
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onClick={handleCaretEvent}
        onSelect={handleCaretEvent}
        onBlur={() => closePopup()}
        onScroll={() => {
          if (backdropRef.current && textareaRef.current) {
            backdropRef.current.scrollTop = textareaRef.current.scrollTop;
            backdropRef.current.scrollLeft = textareaRef.current.scrollLeft;
          }
        }}
        placeholder={placeholder}
        className={cn(
          "relative w-full resize-none bg-transparent text-transparent caret-foreground",
          "selection:bg-primary/25 selection:text-transparent",
          "outline-none border-input focus-visible:border-primary/40 placeholder:text-muted-foreground/70",
          sharedBox,
          sharedTypography,
          minHeightClassName,
          className
        )}
        spellCheck={false}
      />
      {popup &&
        typeof document !== "undefined" &&
        createPortal(
          <ul
            ref={popupListRef}
            role="listbox"
            className="fixed z-[9999] min-w-[220px] max-h-56 w-max overflow-y-auto rounded-md border bg-popover shadow-lg text-sm"
            style={{ left: popup.pos.left, top: popup.pos.top }}
            onMouseDown={(e) => e.preventDefault()}
          >
            {popup.suggestions.length === 0 ? (
              <li className="px-3 py-2 text-xs text-muted-foreground italic">
                Sin resultados
              </li>
            ) : (
              popup.suggestions.map((s, i) => (
                <li
                  key={s.insert + i}
                  role="option"
                  aria-selected={i === popup.activeIdx}
                  data-active={i === popup.activeIdx ? "true" : undefined}
                  onMouseDown={(e) => {
                    e.preventDefault();
                    applySuggestion(s);
                  }}
                  onMouseEnter={() =>
                    setPopup((p) => (p ? { ...p, activeIdx: i } : p))
                  }
                  className={cn(
                    "px-3 py-1.5 cursor-pointer font-mono text-xs",
                    i === popup.activeIdx
                      ? "bg-accent text-accent-foreground"
                      : "hover:bg-muted/50"
                  )}
                >
                  {renderMatch(s.display, popup.query)}
                </li>
              ))
            )}
          </ul>,
          document.body
        )}
    </div>
  );
}
