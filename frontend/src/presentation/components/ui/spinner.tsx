import { cn } from "@/src/application/lib/utils";

type SpinnerSize = "xs" | "sm" | "md" | "lg" | "xl";
type SpinnerVariant = "default" | "muted";

interface SpinnerProps {
  size?: SpinnerSize;
  variant?: SpinnerVariant;
  className?: string;
}

const sizeClasses: Record<SpinnerSize, string> = {
  xs: "h-3 w-3 border-[1.5px]",
  sm: "h-4 w-4 border-2",
  md: "h-6 w-6 border-2",
  lg: "h-9 w-9 border-[3px]",
  xl: "h-12 w-12 border-[3px]",
};

const variantClasses: Record<SpinnerVariant, string> = {
  default: "border-primary/20 border-t-primary",
  muted: "border-muted-foreground/20 border-t-muted-foreground",
};

export function Spinner({
  size = "md",
  variant = "default",
  className,
}: SpinnerProps) {
  return (
    <div
      role="status"
      aria-label="Loading"
      className={cn(
        "rounded-full animate-spin",
        sizeClasses[size],
        variantClasses[variant],
        className
      )}
    />
  );
}

export function FullPageSpinner({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        "flex h-full w-full items-center justify-center",
        className
      )}
    >
      <Spinner size="lg" />
    </div>
  );
}
