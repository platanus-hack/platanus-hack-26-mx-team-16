"use client";

import { Check, Pencil } from "lucide-react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from "react";
import { cn } from "@/src/application/lib/utils";

interface EditableInlineNameProps {
  value: string;
  onSave: (nextValue: string) => Promise<void>;
  className?: string;
  inputClassName?: string;
  /** Optional max width for both idle button and input (e.g. "max-w-[42ch]"). */
  maxWidthClassName?: string;
}

type Status = "idle" | "editing" | "saving" | "saved" | "error";

/**
 * Inline editable text that inherits typography (font, size, weight, color)
 * from its parent. Wrap in <h1 className="text-xl font-semibold">... etc.
 */
export function EditableInlineName({
  value,
  onSave,
  className,
  inputClassName,
  maxWidthClassName,
}: EditableInlineNameProps) {
  const [status, setStatus] = useState<Status>("idle");
  const [draft, setDraft] = useState(value);
  const [width, setWidth] = useState<number | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const sizerRef = useRef<HTMLSpanElement>(null);
  const successTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (status === "idle" || status === "saved") setDraft(value);
  }, [value, status]);

  useLayoutEffect(() => {
    if (status !== "editing" && status !== "saving") return;
    if (!sizerRef.current) return;
    setWidth(Math.ceil(sizerRef.current.getBoundingClientRect().width) + 4);
  }, [draft, status]);

  useEffect(() => {
    if (status !== "editing") return;
    const node = inputRef.current;
    if (!node) return;
    node.focus();
    node.select();
  }, [status]);

  useEffect(() => {
    return () => {
      if (successTimerRef.current) clearTimeout(successTimerRef.current);
    };
  }, []);

  const beginEdit = useCallback(() => {
    if (status === "saving") return;
    setDraft(value);
    setStatus("editing");
  }, [value, status]);

  const cancel = useCallback(() => {
    setDraft(value);
    setStatus("idle");
  }, [value]);

  const commit = useCallback(async () => {
    const trimmed = draft.trim();
    if (trimmed.length === 0) {
      cancel();
      return;
    }
    if (trimmed === value) {
      setStatus("idle");
      return;
    }
    setStatus("saving");
    try {
      await onSave(trimmed);
      setStatus("saved");
      successTimerRef.current = setTimeout(() => setStatus("idle"), 900);
    } catch {
      setStatus("error");
    }
  }, [draft, value, onSave, cancel]);

  const isEditingLike = status === "editing" || status === "saving";

  if (!isEditingLike) {
    return (
      <button
        type="button"
        onClick={beginEdit}
        title="Click to rename"
        className={cn(
          "group/edit relative inline-flex items-baseline gap-2 text-left",
          "rounded-md px-1.5 -mx-1.5 py-0.5 cursor-text",
          "transition-colors hover:bg-muted/60",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40",
          maxWidthClassName,
          className,
        )}
      >
        <span
          className={cn(
            "truncate border-b border-dashed transition-colors",
            "border-foreground/25 group-hover/edit:border-foreground/60",
            status === "saved" && "border-emerald-500/70",
            status === "error" && "border-destructive/70",
          )}
        >
          {value}
        </span>
        <span
          aria-hidden
          className={cn(
            "inline-flex h-[1em] w-[1em] shrink-0 items-center justify-center self-center",
            "text-muted-foreground/70 group-hover/edit:text-foreground transition-colors",
            status === "saved" && "text-emerald-500",
          )}
        >
          {status === "saved" ? (
            <Check className="h-[0.7em] w-[0.7em]" />
          ) : (
            <Pencil className="h-[0.6em] w-[0.6em]" />
          )}
        </span>
      </button>
    );
  }

  return (
    <span
      className={cn(
        "relative inline-flex items-baseline gap-2",
        maxWidthClassName,
        className,
      )}
    >
      <span
        ref={sizerRef}
        aria-hidden
        className="invisible absolute whitespace-pre"
        style={{ font: "inherit", letterSpacing: "inherit" }}
      >
        {draft || " "}
      </span>
      <input
        ref={inputRef}
        type="text"
        value={draft}
        disabled={status === "saving"}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            void commit();
          } else if (e.key === "Escape") {
            e.preventDefault();
            cancel();
          }
        }}
        onBlur={() => {
          if (status === "editing") void commit();
        }}
        style={{
          width: width ?? undefined,
          font: "inherit",
          letterSpacing: "inherit",
          color: "inherit",
        }}
        className={cn(
          "bg-transparent border-0 border-b border-foreground/60 focus:border-foreground",
          "outline-none focus:ring-0 px-0 py-0 leading-tight",
          "caret-foreground selection:bg-foreground/15",
          "transition-colors disabled:opacity-60",
          inputClassName,
        )}
      />
      <span
        aria-hidden
        className="inline-flex h-[1em] w-[1em] shrink-0 items-center justify-center self-center text-muted-foreground/70"
      >
        {status === "saving" ? (
          <span className="h-[0.6em] w-[0.6em] rounded-full border border-current border-t-transparent animate-spin" />
        ) : null}
      </span>
    </span>
  );
}
