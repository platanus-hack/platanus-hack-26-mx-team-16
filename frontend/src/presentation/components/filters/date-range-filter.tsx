"use client";

import { type CSSProperties, useEffect, useRef, useState, useMemo } from "react";
import { createPortal } from "react-dom";
import { ChevronLeft, ChevronRight, CalendarDays } from "lucide-react";
import { useLocale } from "next-intl";
import { buttonVariants } from "@/src/presentation/components/ui/button";
import { cn } from "@/src/application/lib/utils";
import {
  MONTHS_ES,
  DAY_HEADERS_ES,
  parseLocalDate,
  toDateStr,
  formatDateRangeLabel,
  daysInMonth,
  firstDayOffset,
  shiftMonth,
} from "@/src/application/lib/calendar-utils";

interface MonthGridProps {
  year: number;
  month: number;
  from: Date | null;
  to: Date | null;
  hovered: Date | null;
  today: Date;
  onSelect: (d: Date) => void;
  onHover: (d: Date | null) => void;
}

function MonthGrid({
  year,
  month,
  from,
  to,
  hovered,
  today,
  onSelect,
  onHover,
}: MonthGridProps) {
  const rangeEnd = from && !to ? hovered : to;

  const [lo, hi] =
    from && rangeEnd
      ? from.getTime() <= rangeEnd.getTime()
        ? [from, rangeEnd]
        : [rangeEnd, from]
      : [null, null];

  const dim = daysInMonth(year, month);
  const offset = firstDayOffset(year, month);
  const [prevY, prevM] = shiftMonth(year, month, -1);
  const prevDim = daysInMonth(prevY, prevM);
  const totalCells = Math.ceil((offset + dim) / 7) * 7;
  const trailingCount = totalCells - offset - dim;

  type Cell =
    | { kind: "pad-prev"; day: number }
    | { kind: "current"; day: number }
    | { kind: "pad-next"; day: number };

  const cells: Cell[] = [
    ...Array.from({ length: offset }, (_, i) => ({
      kind: "pad-prev" as const,
      day: prevDim - offset + i + 1,
    })),
    ...Array.from({ length: dim }, (_, i) => ({
      kind: "current" as const,
      day: i + 1,
    })),
    ...Array.from({ length: trailingCount }, (_, i) => ({
      kind: "pad-next" as const,
      day: i + 1,
    })),
  ];

  return (
    <div className="w-63">
      <p className="mb-3 text-center text-sm font-semibold capitalize">
        {MONTHS_ES[month]} {year}
      </p>
      <div className="grid grid-cols-7">
        {DAY_HEADERS_ES.map((d) => (
          <div
            key={d}
            className="flex h-7 w-9 items-center justify-center text-[10px] font-medium uppercase tracking-widest text-muted-foreground/60"
          >
            {d}
          </div>
        ))}
        {cells.map((cell, idx) => {
          if (cell.kind !== "current") {
            return (
              <div
                key={`${cell.kind}-${idx}`}
                className="flex h-8 w-9 items-center justify-center"
              >
                <span className="flex h-8 w-8 items-center justify-center text-sm text-muted-foreground/25 select-none">
                  {cell.day}
                </span>
              </div>
            );
          }

          const day = cell.day;
          const d = new Date(year, month, day);
          const t = d.getTime();
          const isFrom = !!from && t === from.getTime();
          const isTo = !!rangeEnd && t === rangeEnd.getTime();
          const isSelected = isFrom || isTo;
          const inRange = !!lo && !!hi && t > lo.getTime() && t < hi.getTime();
          const isToday = t === today.getTime();
          const hasSpan = !!lo && !!hi && lo.getTime() !== hi.getTime();
          const isRangeStart = isFrom && hasSpan;
          const isRangeEnd = isTo && hasSpan;

          return (
            <div
              key={day}
              className={cn(
                "relative flex h-8 w-9 items-center justify-center",
                inRange && "bg-accent/40",
                isRangeStart &&
                  "bg-linear-to-r from-transparent from-50% to-accent/40 to-50%",
                isRangeEnd &&
                  "bg-linear-to-l from-transparent from-50% to-accent/40 to-50%",
              )}
            >
              <button
                type="button"
                onClick={() => onSelect(d)}
                onMouseEnter={() => onHover(d)}
                className={cn(
                  "relative z-10 flex h-8 w-8 items-center justify-center rounded-full text-sm transition-colors duration-100",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1",
                  !isSelected && "hover:bg-accent hover:text-accent-foreground",
                  isSelected &&
                    "bg-foreground text-background hover:bg-foreground/85",
                  isToday &&
                    !isSelected &&
                    "font-semibold ring-1 ring-inset ring-foreground/20",
                )}
              >
                {day}
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export interface DateRange {
  from?: string;
  to?: string;
}

export interface DateRangeFilterProps {
  dateFrom: string;
  dateTo: string;
  onDateFromChange: (date: string) => void;
  onDateToChange: (date: string) => void;
  className?: string;
}

export function DateRangeFilter({
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  className,
}: DateRangeFilterProps) {
  const locale = useLocale();
  const triggerRef = useRef<HTMLButtonElement>(null);
  const popoverRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const [popoverStyle, setPopoverStyle] = useState<CSSProperties>({});

  const now = new Date();
  const today = useMemo(() => {
    const d = new Date();
    d.setHours(0, 0, 0, 0);
    return d;
  }, []);

  const [viewYear, setViewYear] = useState(now.getFullYear());
  const [viewMonth, setViewMonth] = useState(now.getMonth());
  const [hovered, setHovered] = useState<Date | null>(null);

  const from = parseLocalDate(dateFrom);
  const to = parseLocalDate(dateTo);
  const [rightYear, rightMonth] = shiftMonth(viewYear, viewMonth, 1);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!open) return;

    const closeOnPointer = (e: PointerEvent) => {
      if (
        triggerRef.current?.contains(e.target as Node) ||
        popoverRef.current?.contains(e.target as Node)
      )
        return;
      setOpen(false);
      setHovered(null);
    };

    const closeOnScroll = () => {
      setOpen(false);
      setHovered(null);
    };

    document.addEventListener("pointerdown", closeOnPointer, true);
    window.addEventListener("scroll", closeOnScroll, true);
    return () => {
      document.removeEventListener("pointerdown", closeOnPointer, true);
      window.removeEventListener("scroll", closeOnScroll, true);
    };
  }, [open]);

  const handleTriggerClick = () => {
    if (open) {
      setOpen(false);
      return;
    }
    if (triggerRef.current) {
      const rect = triggerRef.current.getBoundingClientRect();
      setPopoverStyle({
        position: "fixed",
        top: rect.bottom + 6,
        left: rect.left,
        zIndex: 9999,
      });
    }
    setOpen(true);
  };

  const handleSelect = (d: Date) => {
    if (!from || (from && to)) {
      onDateFromChange(toDateStr(d));
      onDateToChange("");
    } else {
      if (d.getTime() < from.getTime()) {
        onDateFromChange(toDateStr(d));
        onDateToChange(dateFrom);
      } else {
        onDateToChange(toDateStr(d));
      }
    }
  };

  const navigate = (delta: number) => {
    const [ny, nm] = shiftMonth(viewYear, viewMonth, delta);
    setViewYear(ny);
    setViewMonth(nm);
  };

  const hasValue = !!(dateFrom || dateTo);
  const displayText = formatDateRangeLabel(dateFrom, dateTo, locale);

  const popover = (
    <div
      ref={popoverRef}
      style={popoverStyle}
      className="overflow-hidden rounded-lg border border-border bg-popover text-popover-foreground shadow-lg ring-1 ring-foreground/5"
    >
      <div className="flex items-center gap-2 px-4 pt-4 pb-2">
        <button
          type="button"
          onClick={() => navigate(-1)}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <div className="flex flex-1 items-center justify-around">
          <span className="text-sm font-semibold capitalize">
            {MONTHS_ES[viewMonth]} {viewYear}
          </span>
          <span className="text-sm font-semibold capitalize">
            {MONTHS_ES[rightMonth]} {rightYear}
          </span>
        </div>
        <button
          type="button"
          onClick={() => navigate(1)}
          className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      <div
        className="flex items-start px-3 pb-3"
        onMouseLeave={() => setHovered(null)}
      >
        <MonthGrid
          year={viewYear}
          month={viewMonth}
          from={from}
          to={to}
          hovered={hovered}
          today={today}
          onSelect={handleSelect}
          onHover={setHovered}
        />
        <div className="mx-2 w-px self-stretch bg-border/40" />
        <MonthGrid
          year={rightYear}
          month={rightMonth}
          from={from}
          to={to}
          hovered={hovered}
          today={today}
          onSelect={handleSelect}
          onHover={setHovered}
        />
      </div>

      <div className="flex items-center justify-between border-t border-border/50 px-4 py-2.5">
        <span className="text-xs text-muted-foreground">
          {hasValue ? displayText : "Selecciona un rango"}
        </span>
        {hasValue && (
          <button
            type="button"
            onClick={() => {
              onDateFromChange("");
              onDateToChange("");
            }}
            className="text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            Limpiar
          </button>
        )}
      </div>
    </div>
  );

  return (
    <div className="relative">
      <button
        ref={triggerRef}
        type="button"
        onClick={handleTriggerClick}
        className={cn(
          buttonVariants({ variant: "outline", size: "sm" }),
          "gap-2",
          hasValue && "border-primary",
          className,
        )}
      >
        <CalendarDays className="h-4 w-4 shrink-0" />
        <span className="max-w-55 truncate">{displayText}</span>
      </button>

      {mounted && open && createPortal(popover, document.body)}
    </div>
  );
}
