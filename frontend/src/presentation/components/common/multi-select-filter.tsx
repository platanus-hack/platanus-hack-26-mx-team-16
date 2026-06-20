import * as React from "react";
import { Badge } from "@/src/presentation/components/ui/badge";
import { cn } from "@/src/application/lib/utils";
import { Check, SlidersHorizontal, ChevronDown } from "lucide-react";

export interface FilterOption<T extends string> {
  label: string;
  value: T;
}

export interface MultiSelectFilterProps<T extends string> {
  title: string;
  selected: T[];
  onChange: (values: T[]) => void;
  options: FilterOption<T>[];
  className?: string;
  disabled?: boolean;
}

export function MultiSelectFilter<T extends string>({
  title,
  selected,
  onChange,
  options,
  className,
  disabled = false,
}: MultiSelectFilterProps<T>) {
  const [open, setOpen] = React.useState(false);
  const containerRef = React.useRef<HTMLDivElement>(null);
  const selectedSet = new Set(selected);

  React.useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        containerRef.current &&
        !containerRef.current.contains(event.target as Node)
      ) {
        setOpen(false);
      }
    };

    if (open) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [open]);

  const handleSelect = (value: T) => {
    const newSet = new Set(selectedSet);
    if (newSet.has(value)) {
      newSet.delete(value);
    } else {
      newSet.add(value);
    }
    onChange(Array.from(newSet));
  };

  return (
    <div ref={containerRef} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => !disabled && setOpen(!open)}
        disabled={disabled}
        className={cn(
          "flex items-center gap-2 rounded-md text-sm font-medium border border-dashed border-input px-3 py-1.5 hover:bg-accent hover:text-accent-foreground transition-colors",
          selected.length > 0 && "border-primary",
          disabled && "opacity-40 cursor-not-allowed pointer-events-none"
        )}
      >
        <SlidersHorizontal className="h-4 w-4 text-muted-foreground" />
        <span>{title}</span>
        {selected.length > 0 && (
          <>
            <span className="h-4 w-px bg-border" />
            <Badge variant="secondary" className="rounded-sm px-1 font-normal">
              {selected.length}
            </Badge>
          </>
        )}
        <ChevronDown
          className={cn(
            "h-4 w-4 text-muted-foreground transition-transform",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div className="absolute top-full left-0 mt-1 z-50 w-48 rounded-md border bg-popover p-1 shadow-md">
          <div className="px-2 py-1.5 text-sm font-semibold">
            {title}
          </div>
          <div className="border-t" />
          <div className="py-1">
            {options.map((option, idx) => {
              const isSelected = selectedSet.has(option.value);
              return (
                <button
                  key={idx}
                  type="button"
                  onClick={() => handleSelect(option.value)}
                  className="flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-accent cursor-pointer"
                >
                  <div
                    className={cn(
                      "flex h-4 w-4 items-center justify-center rounded-sm border border-border",
                      isSelected
                        ? "bg-primary text-primary-foreground"
                        : "opacity-50"
                    )}
                  >
                    {isSelected && <Check className="h-3 w-3" />}
                  </div>
                  {option.label}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
