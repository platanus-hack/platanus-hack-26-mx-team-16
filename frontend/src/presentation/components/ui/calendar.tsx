"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";
import { cn } from "@/src/application/lib/utils";

const DAY_NAMES = ["lu", "ma", "mi", "ju", "vi", "sá", "do"];

const MONTH_NAMES = [
  "enero", "febrero", "marzo", "abril", "mayo", "junio",
  "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
];

function isoToDate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function dateToIso(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function startOfDay(date: Date): number {
  return new Date(date.getFullYear(), date.getMonth(), date.getDate()).getTime();
}

interface CalendarProps {
  month: number;
  year: number;
  fromDate: string;
  toDate: string;
  hoverDate?: string;
  maxDate?: string;
  onSelect: (iso: string) => void;
  onHover: (iso: string) => void;
  onPrevMonth?: () => void;
  onNextMonth?: () => void;
  showPrevNav?: boolean;
  showNextNav?: boolean;
}

export function Calendar({
  month,
  year,
  fromDate,
  toDate,
  hoverDate,
  maxDate,
  onSelect,
  onHover,
  onPrevMonth,
  onNextMonth,
  showPrevNav = true,
  showNextNav = true,
}: CalendarProps) {
  const firstDay = new Date(year, month, 1);
  // Monday-based (0=Mon … 6=Sun)
  const startOffset = (firstDay.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  const today = dateToIso(new Date());

  const maxTs = maxDate ? startOfDay(isoToDate(maxDate)) : null;

  const fromTs = fromDate ? startOfDay(isoToDate(fromDate)) : null;
  const toTs = toDate
    ? startOfDay(isoToDate(toDate))
    : hoverDate && fromDate
    ? startOfDay(isoToDate(hoverDate))
    : null;

  const cells: (number | null)[] = [
    ...Array(startOffset).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  return (
    <div className="w-64 select-none">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 px-1">
        <button
          type="button"
          aria-label="Mes anterior"
          onClick={onPrevMonth}
          disabled={!showPrevNav}
          className={cn(
            "p-1 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors",
            !showPrevNav && "invisible",
          )}
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold text-foreground">
          {MONTH_NAMES[month]} {year}
        </span>
        <button
          type="button"
          aria-label="Mes siguiente"
          onClick={onNextMonth}
          disabled={!showNextNav}
          className={cn(
            "p-1 rounded-md hover:bg-accent text-muted-foreground hover:text-foreground transition-colors",
            !showNextNav && "invisible",
          )}
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>

      {/* Day names */}
      <div className="grid grid-cols-7 mb-1">
        {DAY_NAMES.map((d) => (
          <div key={d} className="text-center text-xs text-muted-foreground py-1">
            {d}
          </div>
        ))}
      </div>

      {/* Day cells */}
      <div className="grid grid-cols-7">
        {cells.map((day, idx) => {
          if (day === null) return <div key={idx} />;

          const iso = `${year}-${String(month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
          const ts = startOfDay(new Date(year, month, day));

          const isDisabled = maxTs !== null && ts > maxTs;
          const isFrom = fromTs !== null && ts === fromTs;
          const isTo = toTs !== null && ts === toTs;
          const inRange =
            fromTs !== null &&
            toTs !== null &&
            ts > Math.min(fromTs, toTs) &&
            ts < Math.max(fromTs, toTs);
          const isToday = iso === today;
          const isSelected = isFrom || isTo;

          const rangeStart = fromTs !== null && toTs !== null && ts === Math.min(fromTs, toTs);
          const rangeEnd = fromTs !== null && toTs !== null && ts === Math.max(fromTs, toTs);

          return (
            <div
              key={idx}
              className={cn(
                "relative h-9 flex items-center justify-center",
                !isDisabled && inRange && "bg-accent",
                !isDisabled && inRange && !rangeStart && !rangeEnd && "rounded-none",
                !isDisabled && rangeStart && "rounded-l-full",
                !isDisabled && rangeEnd && "rounded-r-full",
              )}
            >
              <button
                type="button"
                disabled={isDisabled}
                aria-label={iso}
                aria-selected={isSelected || undefined}
                onClick={() => !isDisabled && onSelect(iso)}
                onMouseEnter={() => !isDisabled && onHover(iso)}
                className={cn(
                  "h-8 w-8 rounded-full text-sm transition-colors flex items-center justify-center",
                  isDisabled
                    ? "text-muted-foreground/40 cursor-not-allowed"
                    : isSelected
                    ? "bg-primary text-primary-foreground font-semibold"
                    : isToday
                    ? "border border-primary text-foreground font-semibold hover:bg-accent"
                    : "text-foreground hover:bg-accent",
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

export { dateToIso, isoToDate };
