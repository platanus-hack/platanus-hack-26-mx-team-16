"use client";

import {
  Check,
  ChevronRight,
  Copy,
  TriangleAlert,
  Webhook,
} from "lucide-react";
import Link from "next/link";
import { type MutableRefObject, useEffect, useState } from "react";

import {
  type CreatedIngestSource,
  type SourceAuthMode,
  useCreateSourceMutation,
  useSourcesQuery,
} from "@/src/application/hooks/queries/sources";
import { cn } from "@/src/application/lib/utils";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import { Card } from "@/src/presentation/components/ui/card";
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
import { Label } from "@/src/presentation/components/ui/label";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";

const AUTH_MODE_LABEL: Record<SourceAuthMode, string> = {
  api_key: "API Key",
  hmac: "HMAC",
};

function CopyButton({ value }: { value: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => {
        void navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }}
    >
      {copied ? <Check className="text-primary" /> : <Copy />}
      {copied ? "Copiado" : "Copiar"}
    </Button>
  );
}

/**
 * Full-screen list of a workflow's webhook ingest origins, mirroring
 * WebhookDestinationsList. Each row links to its detail screen (view, edit,
 * delete). The "create" action is exposed to the page header via `onAddRef`;
 * the credential is revealed once, right after creation.
 */
export function WebhookSourcesList({
  workflowId,
  onAddRef,
}: {
  workflowId: string | null;
  onAddRef?: MutableRefObject<(() => void) | null>;
}) {
  const { data: sources, isLoading } = useSourcesQuery(workflowId);
  const create = useCreateSourceMutation();

  const [createOpen, setCreateOpen] = useState(false);
  const [authMode, setAuthMode] = useState<SourceAuthMode>("api_key");
  const [error, setError] = useState<string | null>(null);
  const [created, setCreated] = useState<CreatedIngestSource | null>(null);

  const openCreate = () => {
    setError(null);
    setAuthMode("api_key");
    setCreateOpen(true);
  };

  // Expose "open create dialog" to the page so the header action can trigger it
  // (mirrors WebhookDestinationsList). Inlined so the effect stays free of the
  // `openCreate` dependency.
  useEffect(() => {
    if (!onAddRef) return;
    onAddRef.current = () => {
      setError(null);
      setAuthMode("api_key");
      setCreateOpen(true);
    };
    return () => {
      onAddRef.current = null;
    };
  }, [onAddRef]);

  const handleCreate = () => {
    if (!workflowId) return;
    setError(null);
    create.mutate(
      { workflowId, authMode },
      {
        onSuccess: (source) => {
          setCreated(source as CreatedIngestSource);
          setCreateOpen(false);
        },
        onError: (e) => setError(e.message),
      }
    );
  };

  const revealSecret = created?.apiKey ?? created?.signingSecret ?? null;
  const revealLabel = created?.apiKey ? "API Key" : "Signing secret";

  return (
    <div className="flex flex-1 flex-col gap-4">
      {isLoading ? (
        <SourcesSkeleton />
      ) : !sources?.length ? (
        <div className="flex flex-1 items-center justify-center">
          <EmptyState
            icon={Webhook}
            title="Aún no hay orígenes webhook"
            description="Crea un endpoint de ingesta para empezar a recibir documentos por webhook."
            actionLabel="Nueva"
            onAction={openCreate}
          />
        </div>
      ) : (
        <Card className="overflow-hidden border border-border p-0 ring-0">
          <div className="divide-y divide-border">
            {sources.map((source) => (
              <Link
                key={source.uuid}
                href={`/workflows/${workflowId}/connections/sources/webhooks/${source.uuid}`}
                className={cn(
                  "group flex items-center gap-4 px-4 py-3 outline-none transition-colors",
                  "hover:bg-muted/40",
                  "focus-visible:relative focus-visible:z-10 focus-visible:bg-muted/40 focus-visible:ring-[3px] focus-visible:ring-inset focus-visible:ring-ring/50"
                )}
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <Webhook className="h-5 w-5" />
                </div>
                <div className="flex min-w-0 flex-1 flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <Badge variant="secondary">
                      {AUTH_MODE_LABEL[source.authMode]}
                    </Badge>
                    <Badge variant={source.enabled ? "success" : "secondary"}>
                      {source.enabled ? "Activa" : "Inactiva"}
                    </Badge>
                  </div>
                  <p
                    className="truncate font-mono text-xs text-muted-foreground"
                    title={source.ingestUrl}
                  >
                    {source.ingestUrl}
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 motion-reduce:transform-none motion-reduce:transition-none" />
              </Link>
            ))}
          </div>
        </Card>
      )}

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>Nuevo endpoint de ingesta</DialogTitle>
            <DialogDescription>
              Elige cómo se autentican las peticiones entrantes a este flujo.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="origin-auth-mode">Autenticación</Label>
              <select
                id="origin-auth-mode"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                value={authMode}
                onChange={(e) => setAuthMode(e.target.value as SourceAuthMode)}
              >
                <option value="api_key">API Key (cabecera X-Api-Key)</option>
                <option value="hmac">HMAC (firma del payload)</option>
              </select>
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancelar
            </Button>
            <ActionButton
              loading={create.isPending}
              disabled={!workflowId}
              onClick={handleCreate}
            >
              Crear endpoint
            </ActionButton>
          </DialogFooter>
        </DialogPopup>
      </Dialog>

      {/* Reveal-once dialog (create) */}
      <Dialog
        open={!!created}
        onOpenChange={(open) => !open && setCreated(null)}
      >
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>Guarda tu credencial ahora</DialogTitle>
            <DialogDescription className="flex items-start gap-2 text-amber-600 dark:text-amber-500">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              La credencial no volverá a mostrarse. Cópiala y guárdala en un
              lugar seguro.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-1.5">
              <Label>URL de ingesta</Label>
              <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3">
                <code className="min-w-0 flex-1 truncate font-mono text-sm">
                  {created?.ingestUrl}
                </code>
                {created && <CopyButton value={created.ingestUrl} />}
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Route token</Label>
              <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3">
                <code className="min-w-0 flex-1 truncate font-mono text-sm">
                  {created?.routeToken}
                </code>
                {created && <CopyButton value={created.routeToken} />}
              </div>
            </div>
            {revealSecret && (
              <div className="space-y-1.5">
                <Label>{revealLabel}</Label>
                <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3">
                  <code className="min-w-0 flex-1 truncate font-mono text-sm">
                    {revealSecret}
                  </code>
                  <CopyButton value={revealSecret} />
                </div>
              </div>
            )}
          </DialogBody>
          <DialogFooter>
            <Button onClick={() => setCreated(null)}>Listo</Button>
          </DialogFooter>
        </DialogPopup>
      </Dialog>
    </div>
  );
}

function SourcesSkeleton() {
  return (
    <Card className="overflow-hidden border border-border p-0 ring-0">
      <div className="divide-y divide-border">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-4 py-3">
            <Skeleton className="h-10 w-10 shrink-0 rounded-lg" />
            <div className="flex min-w-0 flex-1 flex-col gap-1.5">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-3 w-64 max-w-full" />
            </div>
            <Skeleton className="h-4 w-4 shrink-0" />
          </div>
        ))}
      </div>
    </Card>
  );
}
