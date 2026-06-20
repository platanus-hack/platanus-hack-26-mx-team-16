"use client";

import { Trash2 } from "lucide-react";
import { type MutableRefObject, useEffect, useState } from "react";

import {
  type ToolTransport,
  useConnectionAccountsQuery,
  useCreateToolMutation,
  useDeleteToolMutation,
  useToolsQuery,
} from "@/src/application/hooks/queries/tools";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
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

// Re-scope 2026-06: las tools son config 1:1 del workflow (como el pipeline);
// la cuenta de conexión que las autentica sigue siendo org-level.
export function ToolsView({
  workflowId,
  onCreateRef,
}: {
  workflowId: string;
  onCreateRef?: MutableRefObject<(() => void) | null>;
}) {
  const { data: tools, isLoading } = useToolsQuery(workflowId);
  const { data: connections } = useConnectionAccountsQuery();
  const create = useCreateToolMutation(workflowId);
  const remove = useDeleteToolMutation(workflowId);

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [transport, setTransport] = useState<ToolTransport>("HTTP");
  const [connectionAccountId, setConnectionAccountId] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [path, setPath] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const isScript = transport === "PYTHON" || transport === "JS";

  useEffect(() => {
    if (!onCreateRef) return;
    onCreateRef.current = () => setCreateOpen(true);
    return () => {
      onCreateRef.current = null;
    };
  }, [onCreateRef]);

  const resetForm = () => {
    setName("");
    setDisplayName("");
    setTransport("HTTP");
    setConnectionAccountId("");
    setBaseUrl("");
    setPath("");
    setCode("");
    setError(null);
  };

  const canSubmit =
    name.trim() &&
    displayName.trim() &&
    (isScript
      ? code.trim()
      : connectionAccountId && baseUrl.trim() && path.trim());

  const handleCreate = () => {
    setError(null);
    create.mutate(
      {
        name: name.trim(),
        displayName: displayName.trim(),
        transport,
        ...(isScript
          ? { code }
          : {
              connectionAccountId,
              baseUrl: baseUrl.trim(),
              path: path.trim(),
            }),
      },
      {
        onSuccess: () => {
          setCreateOpen(false);
          resetForm();
        },
        onError: (e) => setError(e.message),
      }
    );
  };

  return (
    <>
      <Card>
        <CardHeader>
          <CardTitle>Herramientas del workflow</CardTitle>
          <CardDescription>
            Herramientas invocables desde el pipeline: un endpoint HTTP (vía
            cuenta de conexión) o un script (Python/JS) en sandbox.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          {isLoading ? (
            <p className="px-6 py-8 text-sm text-muted-foreground">Cargando…</p>
          ) : !tools?.length ? (
            <p className="px-6 py-8 text-sm text-muted-foreground">
              Este workflow aún no tiene herramientas. Crea la primera para
              poder invocarla desde el pipeline.
            </p>
          ) : (
            <ul className="divide-y divide-border">
              {tools.map((tool) => (
                <li
                  key={tool.uuid}
                  className="flex items-center justify-between gap-4 px-6 py-3.5"
                >
                  <div className="min-w-0 space-y-0.5">
                    <p className="truncate text-sm font-medium">
                      {tool.displayName}
                    </p>
                    <p className="truncate font-mono text-xs text-muted-foreground">
                      {tool.name}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Badge variant="secondary">{tool.transport}</Badge>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label={`Eliminar ${tool.displayName}`}
                      onClick={() => remove.mutate(tool.uuid)}
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
      <Dialog
        open={createOpen}
        onOpenChange={(open) => {
          setCreateOpen(open);
          if (!open) resetForm();
        }}
      >
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>Nueva herramienta</DialogTitle>
            <DialogDescription>
              {isScript
                ? "Escribe el código que correrá en el sandbox aislado; recibe los argumentos y devuelve el resultado."
                : "Define un endpoint HTTP y la cuenta de conexión que lo autentica."}
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="tool-name">Nombre</Label>
              <Input
                id="tool-name"
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="lookup_company"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tool-display-name">Nombre visible</Label>
              <Input
                id="tool-display-name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Buscar empresa"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tool-transport">Transporte</Label>
              <select
                id="tool-transport"
                value={transport}
                onChange={(e) => setTransport(e.target.value as ToolTransport)}
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                <option value="HTTP">
                  HTTP — endpoint vía cuenta de conexión
                </option>
                <option value="PYTHON">Python — script en sandbox</option>
                <option value="JS">JavaScript — script en sandbox</option>
              </select>
            </div>
            {isScript ? (
              <div className="space-y-2">
                <Label htmlFor="tool-code">
                  Código
                  <span className="ml-2 font-normal text-muted-foreground text-xs">
                    {transport === "PYTHON" ? "python3.12" : "node20"} ·
                    entrypoint <span className="font-mono">main(args)</span>
                  </span>
                </Label>
                <textarea
                  id="tool-code"
                  value={code}
                  onChange={(e) => setCode(e.target.value)}
                  spellCheck={false}
                  rows={10}
                  placeholder={
                    transport === "PYTHON"
                      ? "def main(args):\n    return {}"
                      : "function main(args) {\n  return {};\n}"
                  }
                  className="w-full rounded-md border border-input bg-white px-2.5 py-1.5 font-mono text-xs shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50"
                />
                <p className="text-muted-foreground text-xs">
                  La ejecución requiere el sandbox de scripts habilitado en el
                  entorno (revisión de seguridad D-D).
                </p>
              </div>
            ) : (
              <>
                <div className="space-y-2">
                  <Label htmlFor="tool-connection">Cuenta de conexión</Label>
                  <select
                    id="tool-connection"
                    value={connectionAccountId}
                    onChange={(e) => setConnectionAccountId(e.target.value)}
                    className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring/50 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    <option value="" disabled>
                      Selecciona una cuenta…
                    </option>
                    {connections?.map((account) => (
                      <option key={account.uuid} value={account.uuid}>
                        {account.displayName}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tool-base-url">Base URL</Label>
                  <Input
                    id="tool-base-url"
                    value={baseUrl}
                    onChange={(e) => setBaseUrl(e.target.value)}
                    placeholder="https://api.example.com"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="tool-path">Path</Label>
                  <Input
                    id="tool-path"
                    value={path}
                    onChange={(e) => setPath(e.target.value)}
                    placeholder="/v1/lookup"
                  />
                </div>
              </>
            )}
            {error && <p className="text-sm text-destructive">{error}</p>}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancelar
            </Button>
            <ActionButton
              loading={create.isPending}
              disabled={!canSubmit}
              onClick={handleCreate}
            >
              Crear herramienta
            </ActionButton>
          </DialogFooter>
        </DialogPopup>
      </Dialog>
    </>
  );
}
