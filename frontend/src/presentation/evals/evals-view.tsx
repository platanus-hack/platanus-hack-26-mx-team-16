"use client";

import { Play, Plus } from "lucide-react";
import { useState } from "react";

import {
  type CreateRunInput,
  type EvalDataset,
  type EvalRun,
  useCreateDatasetMutation,
  useCreateRunMutation,
  useEvalDatasetsQuery,
} from "@/src/application/hooks/queries/evals";
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

function DatasetCard({ dataset }: { dataset: EvalDataset }) {
  const run = useCreateRunMutation();
  const [version, setVersion] = useState("1");
  const [result, setResult] = useState<EvalRun | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleRun = () => {
    setError(null);
    const parsed = Number.parseInt(version, 10);
    const input: CreateRunInput = {
      datasetId: dataset.uuid,
      pipelineVersion: Number.isNaN(parsed) ? 1 : parsed,
    };
    run.mutate(input, {
      onSuccess: (data) => setResult(data),
      onError: (e) => setError(e.message),
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0 space-y-1">
            <CardTitle className="truncate">{dataset.name}</CardTitle>
            <CardDescription>
              <Badge variant="secondary" className="font-mono">
                {dataset.pipelineSlug}
              </Badge>
            </CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex items-end gap-2">
          <div className="w-24 space-y-1.5">
            <Label htmlFor={`version-${dataset.uuid}`}>Versión</Label>
            <Input
              id={`version-${dataset.uuid}`}
              type="number"
              min={1}
              value={version}
              onChange={(e) => setVersion(e.target.value)}
            />
          </div>
          <ActionButton
            icon={<Play />}
            loading={run.isPending}
            onClick={handleRun}
          >
            Ejecutar eval
          </ActionButton>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        {result && (
          <div className="flex items-center gap-6 rounded-md border border-border bg-muted/40 px-4 py-3">
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Precisión</p>
              <p className="text-lg font-semibold tabular-nums">
                {(result.metrics.accuracy * 100).toFixed(1)}%
              </p>
            </div>
            <div className="space-y-0.5">
              <p className="text-xs text-muted-foreground">Casos</p>
              <p className="text-lg font-semibold tabular-nums">
                {result.metrics.count}
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export function EvalsView() {
  const { data: datasets, isLoading } = useEvalDatasetsQuery();
  const create = useCreateDatasetMutation();

  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [pipelineSlug, setPipelineSlug] = useState("standard-extraction");
  const [error, setError] = useState<string | null>(null);

  const handleCreate = () => {
    setError(null);
    create.mutate(
      { name: name.trim(), pipelineSlug: pipelineSlug.trim() },
      {
        onSuccess: () => {
          setCreateOpen(false);
          setName("");
          setPipelineSlug("standard-extraction");
        },
        onError: (e) => setError(e.message),
      },
    );
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-3xl font-bold tracking-tight">Evaluaciones</h2>
          <p className="text-sm text-muted-foreground">
            Datasets de casos para medir la precisión de tus pipelines de
            extracción.
          </p>
        </div>
        <ActionButton icon={<Plus />} onClick={() => setCreateOpen(true)}>
          Nuevo dataset
        </ActionButton>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="px-6 py-8">
            <p className="text-sm text-muted-foreground">Cargando…</p>
          </CardContent>
        </Card>
      ) : !datasets?.length ? (
        <Card>
          <CardContent className="px-6 py-8">
            <p className="text-sm text-muted-foreground">
              Aún no hay datasets. Crea el primero para empezar a evaluar tus
              pipelines.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {datasets.map((dataset) => (
            <DatasetCard key={dataset.uuid} dataset={dataset} />
          ))}
        </div>
      )}

      {/* Create dataset dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogBackdrop />
        <DialogPopup className="w-full max-w-md p-6">
          <DialogHeader>
            <DialogTitle>Nuevo dataset</DialogTitle>
            <DialogDescription>
              Agrupa casos de evaluación para un pipeline de extracción.
            </DialogDescription>
          </DialogHeader>
          <DialogBody className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="dataset-name">Nombre</Label>
              <Input
                id="dataset-name"
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Circulares · trimestre 1"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="dataset-pipeline">Pipeline</Label>
              <Input
                id="dataset-pipeline"
                value={pipelineSlug}
                onChange={(e) => setPipelineSlug(e.target.value)}
                placeholder="standard-extraction"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>
              Cancelar
            </Button>
            <ActionButton
              loading={create.isPending}
              disabled={!name.trim() || !pipelineSlug.trim()}
              onClick={handleCreate}
            >
              Crear dataset
            </ActionButton>
          </DialogFooter>
        </DialogPopup>
      </Dialog>
    </div>
  );
}
