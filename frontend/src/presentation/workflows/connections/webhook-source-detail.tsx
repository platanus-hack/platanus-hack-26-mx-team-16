"use client";

import {
  Check,
  Copy,
  Inbox,
  Pencil,
  Trash2,
  TriangleAlert,
  Webhook,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import {
  type CreatedIngestSource,
  type SourceAuthMode,
  type SourceEvent,
  type SourceEventStatus,
  useDeleteSourceMutation,
  useSourceEventsQuery,
  useSourcesQuery,
  useUpdateSourceMutation,
} from "@/src/application/hooks/queries/sources";
import { ConfirmDeleteDialog } from "@/src/presentation/components/common/confirm-delete-dialog";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { PageContent } from "@/src/presentation/components/common/page-content";
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
import { Switch } from "@/src/presentation/components/ui/switch";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import { SourceRequestsChart } from "@/src/presentation/workflows/connections/source-requests-chart";

const AUTH_MODE_LABEL: Record<SourceAuthMode, string> = {
  api_key: "API Key",
  hmac: "HMAC",
};

const STATUS_VARIANT: Record<
  SourceEventStatus,
  "success" | "secondary" | "destructive"
> = {
  PENDING: "secondary",
  RUNNING: "secondary",
  PROCESSING: "secondary",
  COMPLETED: "success",
  PARTIAL: "success",
  FAILED: "destructive",
};

const STATUS_LABEL: Record<SourceEventStatus, string> = {
  PENDING: "Pendiente",
  RUNNING: "En curso",
  PROCESSING: "Procesando",
  COMPLETED: "Completado",
  PARTIAL: "Parcial",
  FAILED: "Fallido",
};

// Client-side filter chips for the events table. Each maps to the set of job
// statuses it matches (undefined ⇒ all).
const EVENT_FILTERS: {
  key: string;
  label: string;
  match?: SourceEventStatus[];
}[] = [
  { key: "all", label: "Todas" },
  { key: "done", label: "Completadas", match: ["COMPLETED", "PARTIAL"] },
  {
    key: "processing",
    label: "En proceso",
    match: ["PENDING", "RUNNING", "PROCESSING"],
  },
  { key: "failed", label: "Fallidas", match: ["FAILED"] },
];

function formatDate(value: string | null): string {
  return value ? new Date(value).toLocaleString() : "—";
}

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

interface DetailProps {
  workflowId: string;
  sourceId: string;
}

/**
 * Detail screen for a single webhook ingest origin, mirroring
 * WebhookDestinationDetail. The source is read from the shared list query
 * (no dedicated GET endpoint); edit (enable/disable, rotate auth mode) and
 * delete live here, with the same reveal-once credential dialog used on
 * create. The ingest URL and route token are not secret and stay visible.
 */
export function WebhookSourceDetail({ workflowId, sourceId }: DetailProps) {
  const tc = useTranslations("Connections");
  const router = useRouter();
  const { data: sources, isLoading } = useSourcesQuery(workflowId);
  const source = sources?.find((s) => s.uuid === sourceId) ?? null;
  const { data: events = [], isLoading: eventsLoading } =
    useSourceEventsQuery(sourceId);
  const update = useUpdateSourceMutation();
  const remove = useDeleteSourceMutation();

  const [editOpen, setEditOpen] = useState(false);
  const [editEnabled, setEditEnabled] = useState(true);
  const [editAuthMode, setEditAuthMode] = useState<SourceAuthMode>("api_key");
  const [editError, setEditError] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [created, setCreated] = useState<CreatedIngestSource | null>(null);

  const listHref = `/workflows/${workflowId}/connections/sources/webhooks`;

  // Seed the edit form whenever the dialog opens.
  useEffect(() => {
    if (editOpen && source) {
      setEditEnabled(source.enabled);
      setEditAuthMode(source.authMode);
      setEditError(null);
    }
  }, [editOpen, source]);

  if (isLoading) {
    return (
      <PageContent>
        <PageContent.Header
          icon={Webhook}
          title={<Skeleton className="h-6 w-48" />}
          subtitle={tc("subtitle")}
          showBack
          onBack={() => router.push(listHref)}
        />
        <PageContent.Body>
          <DetailSkeleton />
        </PageContent.Body>
      </PageContent>
    );
  }

  if (!source) {
    return (
      <PageContent>
        <PageContent.Header
          icon={Webhook}
          title="Origen webhook"
          subtitle={tc("subtitle")}
          showBack
          onBack={() => router.push(listHref)}
        />
        <PageContent.Body>
          <div className="flex flex-1 items-center justify-center">
            <EmptyState
              icon={Webhook}
              title="No se encontró el origen"
              description="El origen ya no existe o fue eliminado."
            />
          </div>
        </PageContent.Body>
      </PageContent>
    );
  }

  const handleUpdate = () => {
    setEditError(null);
    const authChanged = editAuthMode !== source.authMode;
    update.mutate(
      {
        workflowId,
        sourceId: source.uuid,
        enabled: editEnabled,
        authMode: authChanged ? editAuthMode : undefined,
      },
      {
        onSuccess: (updated) => {
          setEditOpen(false);
          // The backend re-mints (and returns) the credential only when the
          // auth mode actually changed — reveal it once.
          if (updated.apiKey || updated.signingSecret) {
            setCreated(updated as CreatedIngestSource);
          }
        },
        onError: (e) => setEditError(e.message),
      }
    );
  };

  const handleDelete = () => {
    remove.mutate(
      { workflowId, sourceId: source.uuid },
      { onSuccess: () => router.push(listHref) }
    );
  };

  const revealSecret = created?.apiKey ?? created?.signingSecret ?? null;
  const revealLabel = created?.apiKey ? "API Key" : "Signing secret";
  const editAuthChanged = editAuthMode !== source.authMode;

  return (
    <PageContent>
      <PageContent.Header
        icon={Webhook}
        title={
          <div className="flex min-w-0 items-center gap-3">
            <h1 className="truncate text-xl font-semibold leading-tight tracking-tight">
              Origen webhook
            </h1>
            <Badge variant="secondary">
              {AUTH_MODE_LABEL[source.authMode]}
            </Badge>
            <Badge variant={source.enabled ? "success" : "secondary"}>
              {source.enabled ? "Activa" : "Inactiva"}
            </Badge>
          </div>
        }
        subtitle={tc("subtitle")}
        showBack
        onBack={() => router.push(listHref)}
        actions={
          <>
            <Button
              variant="outline"
              className="gap-2"
              onClick={() => setEditOpen(true)}
            >
              <Pencil className="h-4 w-4" />
              Editar
            </Button>
            <Button
              variant="outline"
              size="icon"
              className="text-destructive"
              onClick={() => setDeleteOpen(true)}
              title="Eliminar origen"
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </>
        }
      />
      <PageContent.Body scroll={false}>
        <Tabs defaultValue="overview" className="flex min-h-0 flex-1 flex-col">
          <TabsList variant="line" className="shrink-0 border-b border-border">
            <TabsTrigger variant="line" value="overview">
              Resumen
            </TabsTrigger>
            <TabsTrigger variant="line" value="events">
              Eventos
            </TabsTrigger>
          </TabsList>

          <TabsContent
            value="overview"
            className="mt-6 flex min-h-0 flex-1 flex-col gap-6 overflow-y-auto"
          >
            {eventsLoading ? (
              <ChartsSkeleton />
            ) : (
              <SourceRequestsChart events={events} />
            )}
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              <Card className="flex flex-col gap-4 border border-border p-4 ring-0">
                <h3 className="text-sm font-semibold">Detalles</h3>
                <dl className="flex flex-col gap-3 text-sm">
                  <DetailRow label="ID">
                    <span className="font-mono text-xs">{source.uuid}</span>
                  </DetailRow>
                  <DetailRow label="Autenticación">
                    {AUTH_MODE_LABEL[source.authMode]}
                  </DetailRow>
                  <DetailRow label="Estado">
                    <Badge variant={source.enabled ? "success" : "secondary"}>
                      {source.enabled ? "Activa" : "Inactiva"}
                    </Badge>
                  </DetailRow>
                  <DetailRow label="Creada">
                    {formatDate(source.createdAt)}
                  </DetailRow>
                </dl>
              </Card>

              <Card className="flex flex-col gap-4 border border-border p-4 ring-0">
                <h3 className="text-sm font-semibold">Endpoint</h3>
                <div className="space-y-1.5">
                  <Label>URL de ingesta</Label>
                  <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3">
                    <code className="min-w-0 flex-1 truncate font-mono text-sm">
                      {source.ingestUrl}
                    </code>
                    <CopyButton value={source.ingestUrl} />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <Label>Route token</Label>
                  <div className="flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3">
                    <code className="min-w-0 flex-1 truncate font-mono text-sm">
                      {source.routeToken}
                    </code>
                    <CopyButton value={source.routeToken} />
                  </div>
                </div>
              </Card>
            </div>
          </TabsContent>

          <TabsContent
            value="events"
            className="mt-6 flex min-h-0 flex-1 flex-col"
          >
            <SourceEvents events={events} isLoading={eventsLoading} />
          </TabsContent>
        </Tabs>
      </PageContent.Body>

      {/* Edit dialog */}
      <Dialog
        open={editOpen}
        onOpenChange={(open) => !open && setEditOpen(false)}
      >
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>Editar origen</DialogTitle>
            <DialogDescription>
              La URL de ingesta no cambia. Cambiar el modo de autenticación
              regenera la credencial.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="flex items-center justify-between gap-4">
              <div className="space-y-0.5">
                <Label htmlFor="edit-enabled">Habilitada</Label>
                <p className="text-xs text-muted-foreground">
                  Una fuente deshabilitada deja de aceptar documentos.
                </p>
              </div>
              <Switch
                id="edit-enabled"
                checked={editEnabled}
                onCheckedChange={setEditEnabled}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="edit-auth-mode">Autenticación</Label>
              <select
                id="edit-auth-mode"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:ring-[3px] focus-visible:ring-ring/50"
                value={editAuthMode}
                onChange={(e) =>
                  setEditAuthMode(e.target.value as SourceAuthMode)
                }
              >
                <option value="api_key">API Key (cabecera X-Api-Key)</option>
                <option value="hmac">HMAC (firma del payload)</option>
              </select>
            </div>
            {editAuthChanged && (
              <p className="flex items-start gap-2 text-sm text-amber-600 dark:text-amber-500">
                <TriangleAlert className="mt-0.5 size-4 shrink-0" />
                Se generará una nueva credencial y se mostrará una sola vez. La
                credencial anterior dejará de funcionar.
              </p>
            )}
            {editError && (
              <p className="text-sm text-destructive">{editError}</p>
            )}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditOpen(false)}>
              Cancelar
            </Button>
            <ActionButton loading={update.isPending} onClick={handleUpdate}>
              Guardar
            </ActionButton>
          </DialogFooter>
        </DialogPopup>
      </Dialog>

      {/* Delete confirm */}
      <ConfirmDeleteDialog
        open={deleteOpen}
        onOpenChange={setDeleteOpen}
        onConfirm={handleDelete}
        title="Eliminar origen"
        description="El endpoint de ingesta dejará de aceptar documentos y su credencial quedará invalidada. Esta acción no se puede deshacer."
        confirmLabel="Eliminar"
      />

      {/* Reveal-once dialog (auth-mode rotation) */}
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
    </PageContent>
  );
}

function DetailRow({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="shrink-0 text-muted-foreground">{label}</dt>
      <dd className="min-w-0 text-right">{children}</dd>
    </div>
  );
}

function SourceEvents({
  events,
  isLoading,
}: {
  events: SourceEvent[];
  isLoading: boolean;
}) {
  const [filter, setFilter] = useState<string>("all");
  const active =
    EVENT_FILTERS.find((f) => f.key === filter) ?? EVENT_FILTERS[0];
  const rows = active.match
    ? events.filter((e) => active.match?.includes(e.status))
    : events;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3">
      <div className="flex shrink-0 items-center justify-end gap-1">
        {EVENT_FILTERS.map((f) => (
          <Button
            key={f.key}
            variant={filter === f.key ? "secondary" : "ghost"}
            size="sm"
            onClick={() => setFilter(f.key)}
            className="h-7 px-2 text-xs font-normal"
          >
            {f.label}
          </Button>
        ))}
      </div>

      {isLoading ? (
        <EventsSkeleton />
      ) : rows.length === 0 ? (
        <div className="flex min-h-0 flex-1 items-center justify-center">
          <EmptyState
            icon={Inbox}
            title="Sin peticiones todavía"
            description="Cuando este origen reciba archivos por webhook, aparecerán aquí con su resultado."
          />
        </div>
      ) : (
        <Card className="min-h-0 flex-1 overflow-hidden border border-border p-0 ring-0">
          <div className="min-h-0 flex-1 overflow-auto">
            <table className="w-full min-w-[560px] text-sm">
              <thead className="bg-muted/30">
                <tr className="border-b border-border text-left text-xs font-medium text-muted-foreground">
                  <th className="px-4 py-3">Archivo</th>
                  <th className="px-4 py-3">Respuesta</th>
                  <th className="px-4 py-3 text-right">Recibido</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((event) => (
                  <tr
                    key={event.uuid}
                    className="border-b border-border/40 last:border-b-0"
                  >
                    <td className="px-4 py-3">
                      <span
                        className="block max-w-[280px] truncate font-medium"
                        title={event.fileName ?? undefined}
                      >
                        {event.fileName ?? "—"}
                      </span>
                      {event.error ? (
                        <span
                          className="mt-0.5 block max-w-[280px] truncate text-xs text-destructive"
                          title={event.error}
                        >
                          {event.error}
                        </span>
                      ) : null}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={STATUS_VARIANT[event.status]}>
                        {STATUS_LABEL[event.status]}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-right text-muted-foreground">
                      {formatDate(event.createdAt)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}

function DetailSkeleton() {
  return (
    <div className="flex flex-col gap-6">
      <ChartsSkeleton />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Skeleton className="h-56 w-full rounded-xl" />
        <Skeleton className="h-56 w-full rounded-xl" />
      </div>
    </div>
  );
}

function ChartsSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {[0, 1].map((i) => (
        <div
          key={i}
          className="flex flex-col gap-3 rounded-xl border border-border bg-card p-4 shadow-xs"
        >
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-3.5 w-20" />
          </div>
          <Skeleton className="h-[200px] w-full rounded-lg" />
        </div>
      ))}
    </div>
  );
}

function EventsSkeleton() {
  return (
    <Card className="min-h-0 flex-1 overflow-hidden border border-border p-0 ring-0">
      <div className="border-b border-border bg-muted/30 px-4 py-3">
        <Skeleton className="h-3 w-24" />
      </div>
      <div className="divide-y divide-border/40">
        {Array.from({ length: 5 }).map((_, i) => (
          <div
            key={i}
            className="flex items-center justify-between gap-4 px-4 py-3"
          >
            <Skeleton className="h-3.5 w-48" />
            <Skeleton className="h-5 w-20 rounded-4xl" />
            <Skeleton className="h-3.5 w-24" />
          </div>
        ))}
      </div>
    </Card>
  );
}
