import { cn } from "@/src/application/lib/utils";

function Skeleton({ className, ...props }: React.ComponentProps<"div">) {
  return (
    <div
      data-slot="skeleton"
      className={cn("bg-surface-container-high rounded-lg animate-pulse", className)}
      {...props}
    />
  );
}

export { Skeleton };
