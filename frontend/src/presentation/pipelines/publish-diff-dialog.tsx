"use client";

import { AlertTriangle, Rocket } from "lucide-react";

import { cn } from "@/src/application/lib/utils";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogBody,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import type {
  PhaseChange,
  PipelineDiff,
} from "@/src/presentation/pipelines/pipeline-diff";

const CHANGE_LABEL: Record<PhaseChange["change"], string> = {
  added: "Añadida",
  removed: "Quitada",
  moved: "Movida",
  modified: "Modificada",
};

const CHANGE_TONE: Record<PhaseChange["change"], string> = {
  added: "text-success",
  removed: "text-destructive",
  moved: "text-muted-foreground",
  modified: "text-primary",
};

interface PublishDiffDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  diff: PipelineDiff;
  currentVersion: number;
  publishing: boolean;
  error: string | null;
  onConfirm: () => void;
}

export function PublishDiffDialog({
  open,
  onOpenChange,
  diff,
  currentVersion,
  publishing,
  error,
  onConfirm,
}: PublishDiffDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-xl p-6">
        <DialogHeader>
          <DialogTitle>Publicar versión nueva</DialogTitle>
          <DialogDescription>
            Cambios respecto a la versión activa (v{currentVersion}).
          </DialogDescription>
        </DialogHeader>
        <DialogBody className="space-y-4 pt-2">
          {diff.empty ? (
            <p className="text-sm text-muted-foreground">
              No hay cambios respecto a la versión activa.
            </p>
          ) : (
            <>
              {diff.phases.length > 0 && (
                <section className="space-y-2">
                  <h3 className="font-mono text-[10px] uppercase tracking-[0.16em] text-muted-foreground/70">
                    Fases
                  </h3>
                  <ul className="space-y-1.5">
                    {diff.phases.map((change) => (
                      <li
                        key={`${change.id}-${change.change}`}
                        className="rounded-md bg-muted/40 px-3 py-2 text-sm"
                      >
                        <span className="flex items-center gap-2">
                          <span
                            className={cn(
                              "font-medium",
                              CHANGE_TONE[change.change]
                            )}
                          >
                            {CHANGE_LABEL[change.change]}
                          </span>
                          <span className="font-mono text-xs">{change.id}</span>
                          <span className="font-mono text-[10px] uppercase text-muted-foreground">
                            {change.kind}
                          </span>
                          {change.change === "moved" && (
                            <span className="text-xs text-muted-foreground">
                              {(change.fromIndex ?? 0) + 1} →{" "}
                              {(change.toIndex ?? 0) + 1}
                            </span>
                          )}
                        </span>
                        {change.details?.map((d) => (
                          <p
                            key={d}
                            className="ml-1 font-mono text-xs text-muted-foreground"
                          >
                            {d}
                          </p>
                        ))}
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}

          <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/5 px-3 py-2 text-xs text-warning-foreground">
            <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-warning" />
            <p>
              Los runs nuevos usarán esta versión de inmediato. Los runs en
              vuelo quedan sellados con su versión y no se ven afectados.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive"
            >
              {error}
            </div>
          )}
        </DialogBody>
        <DialogFooter className="pt-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={publishing}
          >
            Cancelar
          </Button>
          <ActionButton
            type="button"
            icon={<Rocket className="size-4" />}
            loading={publishing}
            onClick={onConfirm}
          >
            Publicar versión
          </ActionButton>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}
