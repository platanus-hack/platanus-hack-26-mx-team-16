"use client";

import { useState } from "react";
import { Popover as PopoverPrimitive } from "@base-ui/react/popover";
import { CalendarDays } from "lucide-react";
import { cn } from "@/src/application/lib/utils";
import { Calendar, dateToIso } from "./calendar";

interface DateRangePickerProps {
  fromDate: string;
  toDate: string;
  onFromChange: (date: string) => void;
  onToChange: (date: string) => void;
  placeholder?: string;
  className?: string;
}

function addMonths(year: number, month: number, delta: number): { year: number; month: number } {
  const d = new Date(year, month + delta, 1);
  return { year: d.getFullYear(), month: d.getMonth() };
}

function fmtDate(iso: string): string {
  return new Date(iso + "T00:00:00").toLocaleDateString("es-MX", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function formatDisplay(from: string, to: string): string {
  if (from && to) return `${fmtDate(from)} — ${fmtDate(to)}`;
  if (from) return `Desde: ${fmtDate(from)}`;
  return "Seleccionar fechas";
}

export function DateRangePicker({
  fromDate,
  toDate,
  onFromChange,
  onToChange,
  placeholder = "Seleccionar fechas",
  className,
}: DateRangePickerProps) {
  const now = new Date();
  const [leftYear, setLeftYear] = useState(now.getFullYear());
  const [leftMonth, setLeftMonth] = useState(now.getMonth());
  const [hoverDate, setHoverDate] = useState("");
  const [open, setOpen] = useState(false);

  const right = addMonths(leftYear, leftMonth, 1);

  function handlePrev() {
    const prev = addMonths(leftYear, leftMonth, -1);
    setLeftYear(prev.year);
    setLeftMonth(prev.month);
  }

  function handleNext() {
    const next = addMonths(leftYear, leftMonth, 1);
    setLeftYear(next.year);
    setLeftMonth(next.month);
  }

  function handleSelect(iso: string) {
    if (!fromDate || (fromDate && toDate)) {
      // Start new selection
      onFromChange(iso);
      onToChange("");
    } else {
      // Second click: set to or swap
      if (iso < fromDate) {
        onToChange(fromDate);
        onFromChange(iso);
      } else {
        onToChange(iso);
      }
    }
  }

  const hasValue = !!(fromDate || toDate);
  const displayText = hasValue ? formatDisplay(fromDate, toDate) : placeholder;

  return (
    <PopoverPrimitive.Root
      open={open}
      onOpenChange={(isOpen) => {
        setOpen(isOpen);
        if (!isOpen) setHoverDate("");
      }}
    >
      <PopoverPrimitive.Trigger
        className={cn(
          "inline-flex items-center gap-2 rounded-md border border-input bg-background px-3 py-1.5 text-sm shadow-sm",
          "hover:bg-accent hover:text-accent-foreground transition-colors",
          "focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring",
          hasValue && "border-primary",
          className,
        )}
      >
        <CalendarDays className="h-4 w-4 text-muted-foreground" />
        <span className={hasValue ? "text-foreground" : "text-muted-foreground"}>
          {displayText}
        </span>
        {hasValue && (
          <button
            type="button"
            aria-label="Limpiar fechas"
            onClick={(e) => {
              e.stopPropagation();
              onFromChange("");
              onToChange("");
              setHoverDate("");
            }}
            className="ml-1 rounded-full text-muted-foreground hover:text-foreground transition-colors"
          >
            ×
          </button>
        )}
      </PopoverPrimitive.Trigger>

      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Positioner
          side="bottom"
          align="end"
          sideOffset={8}
          className="z-50 outline-none"
        >
          <PopoverPrimitive.Popup
            onMouseDown={(e) => e.preventDefault()}
            className={cn(
              "rounded-lg border bg-popover p-4 shadow-lg outline-none",
              "data-starting-style:opacity-0 data-starting-style:scale-95",
              "data-ending-style:opacity-0 data-ending-style:scale-95",
              "transition-[opacity,transform] duration-150",
            )}
          >
            <div
              className="flex gap-6"
              onMouseLeave={() => setHoverDate("")}
            >
              <Calendar
                month={leftMonth}
                year={leftYear}
                fromDate={fromDate}
                toDate={toDate}
                hoverDate={hoverDate}
                onSelect={handleSelect}
                onHover={setHoverDate}
                onPrevMonth={handlePrev}
                onNextMonth={handleNext}
                maxDate={dateToIso(new Date())}
                showPrevNav
                showNextNav={false}
              />
              <div className="w-px bg-border" />
              <Calendar
                month={right.month}
                year={right.year}
                fromDate={fromDate}
                toDate={toDate}
                hoverDate={hoverDate}
                onSelect={handleSelect}
                onHover={setHoverDate}
                onPrevMonth={handlePrev}
                onNextMonth={handleNext}
                maxDate={dateToIso(new Date())}
                showPrevNav={false}
                showNextNav
              />
            </div>

            {hasValue && (
              <div className="flex items-center justify-between mt-4 pt-3 border-t">
                <span className="text-xs text-muted-foreground">
                  {fromDate && toDate
                    ? `${Math.round((new Date(toDate + "T00:00:00").getTime() - new Date(fromDate + "T00:00:00").getTime()) / 86400000) + 1} días seleccionados`
                    : "Selecciona la fecha final"}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    onFromChange("");
                    onToChange("");
                    setHoverDate("");
                  }}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Limpiar
                </button>
              </div>
            )}
          </PopoverPrimitive.Popup>
        </PopoverPrimitive.Positioner>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}

export { dateToIso };
