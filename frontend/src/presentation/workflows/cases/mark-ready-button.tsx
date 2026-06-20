"use client";

import { AlertTriangle, CheckCircle2, Flag } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import {
  CaseNotCompleteError,
  useMarkCaseReadyMutation,
} from "@/src/application/hooks/queries/case-readiness";
import type { CaseCompletenessMissing } from "@/src/domain/entities/case";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";
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

interface Props {
  workflowUuid: string;
  caseId: string;
  /** doc_type slug → nombre legible, para la lista de faltantes. */
  docTypeNames?: Record<string, string>;
  /** Refetch del detalle (el store Zustand vive fuera de TanStack Query). */
  onReady?: () => void;
}

type Notice = { kind: "success" | "error"; text: string } | null;

/**
 * E4 · «Marcar listo»: POST ready vía BFF. En 409 `case.not_complete`
 * abre un dialog de confirmación con los documentos faltantes y la opción
 * de forzar (force: true). Éxito ⇒ aviso transitorio + refetch.
 */
export function MarkReadyButton({
  workflowUuid,
  caseId,
  docTypeNames = {},
  onReady,
}: Props) {
  const markReady = useMarkCaseReadyMutation(workflowUuid, caseId);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [missing, setMissing] = useState<CaseCompletenessMissing[]>([]);
  const [notice, setNotice] = useState<Notice>(null);
  const noticeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (noticeTimer.current) clearTimeout(noticeTimer.current);
    };
  }, []);

  const flashNotice = (next: Exclude<Notice, null>) => {
    setNotice(next);
    if (noticeTimer.current) clearTimeout(noticeTimer.current);
    noticeTimer.current = setTimeout(() => setNotice(null), 2600);
  };

  const handleSuccess = () => {
    setConfirmOpen(false);
    flashNotice({ kind: "success", text: "Caso marcado como listo" });
    onReady?.();
  };

  const handleMarkReady = () => {
    markReady.mutate(
      {},
      {
        onSuccess: handleSuccess,
        onError: (error) => {
          if (error instanceof CaseNotCompleteError) {
            setMissing(error.missing);
            setConfirmOpen(true);
            return;
          }
          flashNotice({ kind: "error", text: error.message });
        },
      }
    );
  };

  const handleForce = () => {
    markReady.mutate(
      { force: true },
      {
        onSuccess: handleSuccess,
        onError: (error) => {
          setConfirmOpen(false);
          flashNotice({ kind: "error", text: error.message });
        },
      }
    );
  };

  return (
    <>
      <ActionButton
        size="sm"
        icon={<Flag />}
        loading={markReady.isPending && !confirmOpen}
        onClick={handleMarkReady}
      >
        Marcar listo
      </ActionButton>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>El expediente no está completo</DialogTitle>
            <DialogDescription>
              Faltan documentos requeridos por la política de completitud.
              Puedes forzar el inicio del procesamiento de todos modos.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            {missing.length > 0 && (
              <ul className="space-y-2">
                {missing.map((item) => (
                  <li
                    key={item.documentType}
                    className="flex items-center justify-between gap-3 rounded-md bg-muted/40 px-3 py-2"
                  >
                    <span className="truncate text-sm font-medium">
                      {docTypeNames[item.documentType] ?? item.documentType}
                    </span>
                    <Badge variant="warning">
                      {item.missing === 1
                        ? "falta 1"
                        : `faltan ${item.missing}`}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancelar
            </Button>
            <ActionButton
              icon={<Flag />}
              loading={markReady.isPending}
              onClick={handleForce}
            >
              Forzar de todos modos
            </ActionButton>
          </DialogFooter>
        </DialogPopup>
      </Dialog>

      {notice && (
        <div
          role="status"
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg bg-card px-3.5 py-2.5 text-sm font-medium shadow-md ring-1 ring-foreground/10"
        >
          {notice.kind === "success" ? (
            <CheckCircle2 className="size-4 text-emerald-600" />
          ) : (
            <AlertTriangle className="size-4 text-red-600" />
          )}
          {notice.text}
        </div>
      )}
    </>
  );
}
