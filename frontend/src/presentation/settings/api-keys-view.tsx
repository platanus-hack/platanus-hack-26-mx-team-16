"use client";

import { Check, Copy, Plus, Trash2, TriangleAlert } from "lucide-react";
import { useState } from "react";

import {
  type MintedApiKey,
  useApiKeysQuery,
  useMintApiKeyMutation,
  useRevokeApiKeyMutation,
} from "@/src/application/hooks/queries/api-keys";
import { cn } from "@/src/application/lib/utils";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Button } from "@/src/presentation/components/ui/button";
import { Badge } from "@/src/presentation/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/src/presentation/components/ui/card";
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
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

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

export function ApiKeysView() {
  const { data: keys, isLoading } = useApiKeysQuery();
  const mint = useMintApiKeyMutation();
  const revoke = useRevokeApiKeyMutation();

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [minted, setMinted] = useState<MintedApiKey | null>(null);

  const handleMint = () => {
    setError(null);
    mint.mutate(name.trim(), {
      onSuccess: (key) => {
        setMinted(key as MintedApiKey);
        setCreateOpen(false);
        setName("");
      },
      onError: (e) => setError(e.message),
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-3xl font-bold tracking-tight">API Keys</h2>
          <p className="text-sm text-muted-foreground">
            Claves M2M para ingestar archivos y resolver tareas vía la API
            (<code className="rounded bg-muted px-1 py-0.5 text-xs">X-Api-Key</code>).
          </p>
        </div>
        <ActionButton icon={<Plus />} onClick={() => setCreateOpen(true)}>
          Nueva clave
        </ActionButton>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Claves activas</CardTitle>
          <CardDescription>
            La clave en texto plano se muestra una sola vez al crearla.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="px-6 py-8 text-sm text-muted-foreground">Cargando…</p>
          ) : !keys?.length ? (
            <p className="px-6 py-8 text-sm text-muted-foreground">
              Aún no hay claves. Crea la primera para empezar a ingestar por API.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {keys.map((key) => (
                <li
                  key={key.uuid}
                  className="flex items-center justify-between gap-4 px-6 py-3.5"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate text-sm font-medium">{key.name}</p>
                    <p className="font-mono text-xs text-muted-foreground">
                      {key.prefix}…
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant={key.enabled ? "default" : "secondary"}>
                      {key.enabled ? "Activa" : "Revocada"}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="Revocar"
                      onClick={() => revoke.mutate(key.uuid)}
                    >
                      <Trash2 className="text-destructive" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {/* Create dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>Nueva API key</DialogTitle>
            <DialogDescription>
              Dale un nombre para identificarla (p. ej. el sistema que la usará).
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-2">
            <Label htmlFor="api-key-name">Nombre</Label>
            <Input
              id="api-key-name"
              autoFocus
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Banco · ingesta circulares"
              onKeyDown={(e) => e.key === "Enter" && name.trim() && handleMint()}
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancelar
            </Button>
            <ActionButton
              loading={mint.isPending}
              disabled={!name.trim()}
              onClick={handleMint}
            >
              Crear clave
            </ActionButton>
          </DialogFooter>
        </DialogPopup>
      </Dialog>

      {/* Reveal-once dialog */}
      <Dialog open={!!minted} onOpenChange={(open) => !open && setMinted(null)}>
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>Guarda tu clave ahora</DialogTitle>
            <DialogDescription className="flex items-start gap-2 text-warning-deep dark:text-warning">
              <TriangleAlert className="mt-0.5 size-4 shrink-0" />
              No volverás a verla. Cópiala y guárdala en un lugar seguro.
            </DialogDescription>
          </DialogHeader>
          <DialogBody>
            <div
              className={cn(
                "flex items-center gap-2 rounded-md border border-border bg-muted/40 p-3",
              )}
            >
              <code className="min-w-0 flex-1 truncate font-mono text-sm">
                {minted?.key}
              </code>
              {minted && <CopyButton value={minted.key} />}
            </div>
          </DialogBody>
          <DialogFooter>
            <Button onClick={() => setMinted(null)}>Listo</Button>
          </DialogFooter>
        </DialogPopup>
      </Dialog>
    </div>
  );
}
