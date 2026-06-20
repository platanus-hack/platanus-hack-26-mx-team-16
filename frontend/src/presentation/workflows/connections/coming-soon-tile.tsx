import type { LucideIcon } from "lucide-react";

import { Badge } from "@/src/presentation/components/ui/badge";
import { Card } from "@/src/presentation/components/ui/card";

/**
 * Grid tile for a connector whose adapter has not shipped yet. Shared by the
 * source and destination type grids so both read with the same vocabulary.
 */
export function ComingSoonTile({
  icon: Icon,
  title,
  description,
  comingSoonLabel,
}: {
  icon: LucideIcon;
  title: string;
  description: string;
  comingSoonLabel: string;
}) {
  return (
    <Card className="flex h-full flex-col gap-3 border border-border p-5 opacity-70 ring-0">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted text-muted-foreground">
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold">{title}</h2>
        <Badge
          variant="secondary"
          className="text-[10px] uppercase tracking-wide"
        >
          {comingSoonLabel}
        </Badge>
      </div>
      <p className="flex-1 text-sm text-muted-foreground">{description}</p>
    </Card>
  );
}
