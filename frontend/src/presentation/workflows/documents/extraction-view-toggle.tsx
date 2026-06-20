"use client";

import { AlignLeft, Braces, List } from "lucide-react";
import { useTranslations } from "next-intl";
import { cn } from "@/src/application/lib/utils";
import {
  ToggleGroup,
  ToggleGroupItem,
} from "@/src/presentation/components/ui/toggle-group";

export type ExtractionView = "fields" | "json" | "plain";

/** Each segment is a quiet pill that lifts into a teal-tint thumb when active.
 *  Weight stays constant so selecting never reflows the row; the active state
 *  reads through fill + ink + a whisper shadow, the same vocabulary badges and
 *  selected rows use (DESIGN.md). The resting transparent border reserves the
 *  1px the active border occupies, so the thumb never jumps. The shared focus
 *  ring (3px teal) comes from the toggle primitive. The active fill is marked
 *  important so it beats the primitive's default `hover:bg-muted` when the
 *  selected pill is also hovered. */
const ITEM_CLASS = cn(
  "h-7 min-w-0 cursor-pointer gap-1.5 rounded-sm border border-transparent px-2.5",
  "text-xs font-medium text-muted-foreground",
  "transition-[color,background-color,border-color,box-shadow] duration-150 ease-out",
  "motion-reduce:transition-none",
  "hover:bg-background/70 hover:text-foreground",
  "aria-pressed:border-border aria-pressed:bg-accent! aria-pressed:text-accent-foreground! aria-pressed:shadow-xs"
);

/** View options in display order. `labelKey`/`ariaKey` resolve against the
 *  `DocumentDataPane` i18n namespace. */
const OPTIONS = [
  { value: "fields", Icon: List, labelKey: "fields", ariaKey: "fieldsView" },
  { value: "json", Icon: Braces, labelKey: "json", ariaKey: "jsonView" },
  { value: "plain", Icon: AlignLeft, labelKey: "plain", ariaKey: "plainView" },
] as const;

interface ExtractionViewToggleProps {
  value: ExtractionView;
  onChange: (view: ExtractionView) => void;
  className?: string;
}

/** Segmented control that switches the extraction panel between the mapped
 *  fields list, the raw JSON viewer, and the plain extracted text. */
export function ExtractionViewToggle({
  value,
  onChange,
  className,
}: ExtractionViewToggleProps) {
  const t = useTranslations("DocumentDataPane");

  return (
    <ToggleGroup
      value={[value]}
      onValueChange={(next) => {
        const v = next[0] as ExtractionView | undefined;
        if (v) onChange(v);
      }}
      spacing={1}
      className={cn(
        "rounded-md border border-border bg-muted/50 p-0.5 shadow-xs",
        className
      )}
    >
      {OPTIONS.map(({ value: optionValue, Icon, labelKey, ariaKey }) => (
        <ToggleGroupItem
          key={optionValue}
          value={optionValue}
          aria-label={t(ariaKey)}
          className={ITEM_CLASS}
        >
          <Icon className="size-3.5" aria-hidden />
          {t(labelKey)}
        </ToggleGroupItem>
      ))}
    </ToggleGroup>
  );
}
