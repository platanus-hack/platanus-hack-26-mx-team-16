"use client";

import { Plus, X } from "lucide-react";

import type {
  ActivationPolicy,
  ReviewStage,
} from "@/src/application/hooks/queries/pipelines";
import { cn } from "@/src/application/lib/utils";
import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Switch } from "@/src/presentation/components/ui/switch";

interface PoliciesPanelProps {
  activation: ActivationPolicy;
  readOnly: boolean;
  onActivationChange: (policy: ActivationPolicy) => void;
}

const SEVERITIES = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"];

function Pct({
  value,
  onChange,
  readOnly,
  id,
}: {
  value: number;
  onChange: (v: number) => void;
  readOnly: boolean;
  id?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <input
        id={id}
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={value}
        disabled={readOnly}
        onChange={(e) => onChange(Number(e.target.value))}
        className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-muted accent-primary disabled:cursor-not-allowed"
      />
      <span className="w-12 text-right font-mono text-xs text-muted-foreground">
        {Math.round(value * 100)}%
      </span>
    </div>
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-3">
      <div className="space-y-0.5">
        <h3 className="text-sm font-medium">{title}</h3>
        {description && (
          <p className="text-xs text-muted-foreground">{description}</p>
        )}
      </div>
      {children}
    </section>
  );
}

export function PoliciesPanel({
  activation,
  readOnly,
  onActivationChange,
}: PoliciesPanelProps) {
  const thresholds = activation.field_thresholds ?? {};
  const severities = activation.blocking_rule_severities ?? ["BLOCKER"];
  const stages = activation.stages ?? [];

  // ── Activation thresholds ──
  function setThreshold(key: string, value: number) {
    onActivationChange({
      ...activation,
      field_thresholds: { ...thresholds, [key]: value },
    });
  }
  function renameThreshold(oldKey: string, newKey: string) {
    if (!newKey || newKey === oldKey) return;
    const next = { ...thresholds };
    const v = next[oldKey];
    delete next[oldKey];
    next[newKey] = v;
    onActivationChange({ ...activation, field_thresholds: next });
  }
  function removeThreshold(key: string) {
    const next = { ...thresholds };
    delete next[key];
    onActivationChange({ ...activation, field_thresholds: next });
  }

  // ── Stages (L1/L2) ──
  function setStages(next: ReviewStage[]) {
    onActivationChange({
      ...activation,
      stages: next.length ? next : null,
    });
  }
  function toggleStage(stage: ReviewStage["stage"], on: boolean) {
    if (on) {
      const next = [...stages, { stage, mode: "mandatory" as const }];
      next.sort((a, b) => (a.stage < b.stage ? -1 : 1));
      setStages(next);
    } else {
      setStages(stages.filter((s) => s.stage !== stage));
    }
  }
  function setStageMode(stage: ReviewStage["stage"], mode: ReviewStage["mode"]) {
    setStages(stages.map((s) => (s.stage === stage ? { ...s, mode } : s)));
  }

  const usedThresholdKeys = new Set(Object.keys(thresholds));

  return (
    <div className="space-y-8">
      <Section
        title="Activación de revisión"
        description="Umbrales de confianza y reglas que enrutan un caso a revisión humana."
      >
        <div className="space-y-3">
          <Label className="text-xs text-muted-foreground">
            Umbral por defecto
          </Label>
          <Pct
            id="threshold-default"
            value={thresholds.default ?? 0.75}
            readOnly={readOnly}
            onChange={(v) => setThreshold("default", v)}
          />
          {Object.entries(thresholds)
            .filter(([k]) => k !== "default")
            .map(([key, value]) => (
              <div key={key} className="flex items-center gap-2">
                <Input
                  value={key}
                  disabled={readOnly}
                  onValueChange={(v) => renameThreshold(key, v)}
                  className="w-44 font-mono text-xs"
                  placeholder="doctype.campo"
                />
                <div className="flex-1">
                  <Pct
                    value={value}
                    readOnly={readOnly}
                    onChange={(v) => setThreshold(key, v)}
                  />
                </div>
                {!readOnly && (
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={`Quitar umbral ${key}`}
                    onClick={() => removeThreshold(key)}
                  >
                    <X className="size-4" />
                  </Button>
                )}
              </div>
            ))}
          {!readOnly && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => {
                let key = "campo";
                let n = 1;
                while (usedThresholdKeys.has(key)) {
                  n += 1;
                  key = `campo_${n}`;
                }
                setThreshold(key, 0.75);
              }}
            >
              <Plus className="size-4" /> Umbral por campo
            </Button>
          )}
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label className="text-xs">Acción ante baja confianza</Label>
            <Select
              value={activation.on_low_confidence ?? "clarify"}
              onValueChange={(v) =>
                onActivationChange({
                  ...activation,
                  on_low_confidence: v as ActivationPolicy["on_low_confidence"],
                })
              }
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="clarify">Pedir aclaración</SelectItem>
                <SelectItem value="review">Enviar a revisión</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label className="text-xs">Modo de revisión</Label>
            <Select
              value={activation.mode ?? "mandatory"}
              onValueChange={(v) =>
                onActivationChange({
                  ...activation,
                  mode: v as ActivationPolicy["mode"],
                })
              }
            >
              <SelectTrigger className="h-9">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="mandatory">Obligatoria</SelectItem>
                <SelectItem value="by_exception">Por excepción</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="space-y-1.5">
          <Label className="text-xs">Severidades bloqueantes</Label>
          <div className="flex flex-wrap gap-1.5">
            {SEVERITIES.map((sev) => {
              const on = severities.includes(sev);
              return (
                <button
                  key={sev}
                  type="button"
                  disabled={readOnly}
                  onClick={() =>
                    onActivationChange({
                      ...activation,
                      blocking_rule_severities: on
                        ? severities.filter((s) => s !== sev)
                        : [...severities, sev],
                    })
                  }
                  className={cn(
                    "inline-flex h-7 items-center rounded-md px-2.5 font-mono text-xs transition-colors",
                    on
                      ? "bg-primary/10 text-primary ring-1 ring-primary/30"
                      : "bg-muted text-muted-foreground hover:bg-muted/70",
                    readOnly && "cursor-not-allowed opacity-60",
                  )}
                >
                  {sev}
                </button>
              );
            })}
          </div>
        </div>
      </Section>

      <Section
        title="Etapas de revisión (L1 / L2)"
        description="Sin etapas, la compuerta es única. Activa L1/L2 para revisión multinivel."
      >
        <div className="space-y-2">
          {(["review_l1", "review_l2"] as const).map((stageId) => {
            const stage = stages.find((s) => s.stage === stageId);
            return (
              <div
                key={stageId}
                className="flex items-center gap-3 rounded-md bg-muted/40 px-3 py-2"
              >
                <Switch
                  checked={Boolean(stage)}
                  disabled={readOnly}
                  onCheckedChange={(on) => toggleStage(stageId, on)}
                />
                <span className="flex-1 font-mono text-xs">{stageId}</span>
                {stage && (
                  <Select
                    value={stage.mode}
                    onValueChange={(v) =>
                      setStageMode(stageId, v as ReviewStage["mode"])
                    }
                  >
                    <SelectTrigger className="h-8 w-40">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="mandatory">Obligatoria</SelectItem>
                      <SelectItem value="by_exception">Por excepción</SelectItem>
                    </SelectContent>
                  </Select>
                )}
              </div>
            );
          })}
        </div>
      </Section>

      <Section
        title="Muestreo"
        description="Dos muestreos distintos: pre-aprobación (qué revisa un humano) y post-aprobación (auditoría QA de lo auto-aprobado)."
      >
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">
            Muestreo a revisión
            <span className="font-normal">— % de casos enviados a un humano</span>
          </Label>
          <Pct
            value={activation.sample_rate ?? 0}
            readOnly={readOnly}
            onChange={(v) =>
              onActivationChange({ ...activation, sample_rate: v })
            }
          />
        </div>
        <div className="space-y-2">
          <Label className="text-xs text-muted-foreground">
            Auditoría QA post-aprobación
            <span className="font-normal">
              — % de casos auto-aprobados auditados después
            </span>
          </Label>
          <Pct
            value={activation.qa_sample_rate ?? 0}
            readOnly={readOnly}
            onChange={(v) =>
              onActivationChange({ ...activation, qa_sample_rate: v })
            }
          />
        </div>
      </Section>
    </div>
  );
}
