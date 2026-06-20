"use client";

import { X } from "lucide-react";
import { useState } from "react";

import type {
  ActivationPolicy,
  PhaseCatalogEntry,
  PhaseConfigField,
} from "@/src/application/hooks/queries/pipelines";
import { cn } from "@/src/application/lib/utils";
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
import { PoliciesPanel } from "@/src/presentation/pipelines/policies-panel";

interface DoctypeOption {
  slug: string;
  name: string;
}

interface DestinationOption {
  uuid: string;
  name: string;
}

interface PhaseConfigFormProps {
  entry: PhaseCatalogEntry | undefined;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
  /** Doctypes del tenant para selectores de `fan_out_types`. */
  doctypes: DoctypeOption[];
  /** Destinos webhook del workflow para el selector de `deliver.channels`. */
  destinations?: DestinationOption[];
  /** Solo lectura (propaga al editor de activación del gate). */
  readOnly?: boolean;
}

function humanize(key: string): string {
  return key.replace(/_/g, " ").replace(/^\w/, (c) => c.toUpperCase());
}

/** Normaliza un mapa `{slug: valor}` desde un `unknown` del config. */
function asMap(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

/**
 * Selector «añadir tipo de documento» reutilizado por los editores de mapa.
 * Espeja el control de alta de `FanOutTypesField`: muestra los doctypes aún no
 * presentes y, al elegir uno, delega la creación de la fila en `onAdd`.
 */
function AddDoctypeRow({
  doctypes,
  used,
  onAdd,
}: {
  doctypes: DoctypeOption[];
  used: string[];
  onAdd: (slug: string) => void;
}) {
  const available = doctypes.filter((d) => !used.includes(d.slug));
  if (available.length === 0) {
    return (
      <p className="text-xs text-muted-foreground">
        No hay más tipos de documento disponibles.
      </p>
    );
  }
  return (
    <Select
      value=""
      onValueChange={(v) => {
        if (v) onAdd(v as string);
      }}
    >
      <SelectTrigger className="h-9">
        <SelectValue placeholder="Añadir tipo de documento…" />
      </SelectTrigger>
      <SelectContent>
        {available.map((d) => (
          <SelectItem key={d.slug} value={d.slug}>
            {d.name}
            <span className="ml-2 font-mono text-xs text-muted-foreground">
              {d.slug}
            </span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

/** Botón «quitar fila» con el mismo lenguaje visual que los chips de fan_out. */
function RemoveRowButton({
  slug,
  onClick,
}: {
  slug: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-label={`Quitar ${slug}`}
      onClick={onClick}
      className="shrink-0 rounded-md p-1.5 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
    >
      <X className="size-3.5" />
    </button>
  );
}

/** Etiqueta de un tipo de documento (nombre + slug en mono) para las filas. */
function DoctypeLabel({
  slug,
  doctypes,
}: {
  slug: string;
  doctypes: DoctypeOption[];
}) {
  const dt = doctypes.find((d) => d.slug === slug);
  return (
    <span className="flex min-w-0 flex-col">
      <span className="truncate text-sm">{dt?.name ?? slug}</span>
      <span className="truncate font-mono text-xs text-muted-foreground">
        {slug}
      </span>
    </span>
  );
}

/**
 * `extract_text.per_type_overrides`: mapa `{slug → extractor}`. Por cada fila,
 * a la izquierda el tipo de documento (fijo) y a la derecha un selector con el
 * mismo enum de extractores que el campo `extractor`. Mapa vacío ⇒ `undefined`
 * (el campo se omite del config, igual que el resto de controles).
 */
function PerTypeOverridesField({
  value,
  doctypes,
  extractors,
  onChange,
}: {
  value: Record<string, unknown>;
  doctypes: DoctypeOption[];
  extractors: string[];
  onChange: (next: Record<string, string> | undefined) => void;
}) {
  const entries = Object.entries(value);
  const used = entries.map(([slug]) => slug);

  function commit(next: Record<string, string>) {
    onChange(Object.keys(next).length === 0 ? undefined : next);
  }

  return (
    <div className="space-y-2">
      {entries.length > 0 && (
        <ul className="space-y-1.5">
          {entries.map(([slug, extractor]) => (
            <li key={slug} className="flex items-center gap-2">
              <span className="min-w-0 flex-1 rounded-md border border-input bg-muted/40 px-2.5 py-1.5">
                <DoctypeLabel slug={slug} doctypes={doctypes} />
              </span>
              <Select
                value={extractor == null ? "" : String(extractor)}
                onValueChange={(v) => {
                  if (v)
                    commit({ ...value, [slug]: v } as Record<string, string>);
                }}
              >
                <SelectTrigger className="h-9 w-40 shrink-0 font-mono text-xs">
                  <SelectValue placeholder="Extractor…" />
                </SelectTrigger>
                <SelectContent>
                  {extractors.map((opt) => (
                    <SelectItem key={opt} value={opt} className="font-mono">
                      {opt}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <RemoveRowButton
                slug={slug}
                onClick={() => {
                  const next = { ...value } as Record<string, string>;
                  delete next[slug];
                  commit(next);
                }}
              />
            </li>
          ))}
        </ul>
      )}
      <AddDoctypeRow
        doctypes={doctypes}
        used={used}
        onAdd={(slug) =>
          commit({
            ...value,
            [slug]: extractors[0] ?? "",
          } as Record<string, string>)
        }
      />
    </div>
  );
}

/**
 * `await_documents.required_types`: mapa `{slug → mínimo (entero ≥ 1)}`. Filas
 * con el tipo de documento fijo a la izquierda y un input numérico (min 1) a la
 * derecha. Mapa vacío ⇒ `undefined`.
 */
function RequiredTypesField({
  value,
  doctypes,
  onChange,
}: {
  value: Record<string, unknown>;
  doctypes: DoctypeOption[];
  onChange: (next: Record<string, number> | undefined) => void;
}) {
  const entries = Object.entries(value);
  const used = entries.map(([slug]) => slug);

  function commit(next: Record<string, number>) {
    onChange(Object.keys(next).length === 0 ? undefined : next);
  }

  return (
    <div className="space-y-2">
      {entries.length > 0 && (
        <ul className="space-y-1.5">
          {entries.map(([slug, min]) => (
            <li key={slug} className="flex items-center gap-2">
              <span className="min-w-0 flex-1 rounded-md border border-input bg-muted/40 px-2.5 py-1.5">
                <DoctypeLabel slug={slug} doctypes={doctypes} />
              </span>
              <Input
                type="number"
                min={1}
                step={1}
                aria-label={`Mínimo de ${slug}`}
                value={min == null ? "" : String(min)}
                onValueChange={(v) => {
                  const n = Math.max(1, Math.floor(Number(v) || 1));
                  commit({ ...value, [slug]: n } as Record<string, number>);
                }}
                className="w-24 shrink-0 text-center font-mono"
              />
              <RemoveRowButton
                slug={slug}
                onClick={() => {
                  const next = { ...value } as Record<string, number>;
                  delete next[slug];
                  commit(next);
                }}
              />
            </li>
          ))}
        </ul>
      )}
      <AddDoctypeRow
        doctypes={doctypes}
        used={used}
        onAdd={(slug) =>
          commit({ ...value, [slug]: 1 } as Record<string, number>)
        }
      />
    </div>
  );
}

function FanOutTypesField({
  value,
  doctypes,
  onChange,
}: {
  value: string[];
  doctypes: DoctypeOption[];
  onChange: (next: string[]) => void;
}) {
  const available = doctypes.filter((d) => !value.includes(d.slug));
  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {value.map((slug) => {
            const dt = doctypes.find((d) => d.slug === slug);
            return (
              <li key={slug}>
                <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 font-mono text-xs text-primary">
                  {dt?.name ?? slug}
                  <button
                    type="button"
                    aria-label={`Quitar ${slug}`}
                    onClick={() => onChange(value.filter((s) => s !== slug))}
                    className="text-primary/70 hover:text-primary"
                  >
                    <X className="size-3" />
                  </button>
                </span>
              </li>
            );
          })}
        </ul>
      )}
      {available.length > 0 ? (
        <Select
          value=""
          onValueChange={(v) => {
            if (v) onChange([...value, v as string]);
          }}
        >
          <SelectTrigger className="h-9">
            <SelectValue placeholder="Añadir tipo de documento…" />
          </SelectTrigger>
          <SelectContent>
            {available.map((d) => (
              <SelectItem key={d.slug} value={d.slug}>
                {d.name}
                <span className="ml-2 font-mono text-xs text-muted-foreground">
                  {d.slug}
                </span>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <p className="text-xs text-muted-foreground">
          No hay más tipos de documento disponibles.
        </p>
      )}
    </div>
  );
}

/**
 * Editor de `list[str]` por chips: escribe y Enter para añadir, ✕ para quitar.
 * Lista vacía ⇒ `undefined` (el campo se omite del config). Reutilizado por
 * `payload_projection` (campos del output) y por roles/usuarios de `approvers`.
 */
function StringListField({
  value,
  placeholder,
  onChange,
}: {
  value: string[];
  placeholder: string;
  onChange: (next: string[] | undefined) => void;
}) {
  const [draft, setDraft] = useState("");

  function commit(next: string[]) {
    onChange(next.length === 0 ? undefined : next);
  }
  function add() {
    const v = draft.trim();
    setDraft("");
    if (!v || value.includes(v)) return;
    commit([...value, v]);
  }

  return (
    <div className="space-y-2">
      {value.length > 0 && (
        <ul className="flex flex-wrap gap-1.5">
          {value.map((item) => (
            <li key={item}>
              <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 font-mono text-xs text-primary">
                {item}
                <button
                  type="button"
                  aria-label={`Quitar ${item}`}
                  onClick={() => commit(value.filter((s) => s !== item))}
                  className="text-primary/70 hover:text-primary"
                >
                  <X className="size-3" />
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
      <Input
        value={draft}
        placeholder={placeholder}
        onValueChange={setDraft}
        onKeyDown={(e) => {
          if (e.key === "Enter") {
            e.preventDefault();
            add();
          }
        }}
        onBlur={add}
      />
    </div>
  );
}

/**
 * `deliver.channels`: allowlist de destinos webhook. Un switch separa los dos
 * estados que el backend distingue: ausente (`None` ⇒ TODOS los destinos
 * suscritos, comportamiento de hoy) vs lista explícita (allowlist por uuid; `[]`
 * = no entregar a nadie). Match del backend por uuid o name — guardamos uuid.
 */
function ChannelsField({
  value,
  destinations,
  onChange,
}: {
  value: string[] | undefined;
  destinations: DestinationOption[];
  onChange: (next: string[] | undefined) => void;
}) {
  const restricted = Array.isArray(value);
  const selected = restricted ? (value as string[]) : [];
  const available = destinations.filter((d) => !selected.includes(d.uuid));

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-muted-foreground text-xs">
        <Switch
          checked={restricted}
          onCheckedChange={(c) => onChange(c ? [] : undefined)}
        />
        Restringir a destinos específicos
      </label>
      {restricted && (
        <>
          {selected.length > 0 && (
            <ul className="flex flex-wrap gap-1.5">
              {selected.map((uuid) => {
                const dest = destinations.find((d) => d.uuid === uuid);
                return (
                  <li key={uuid}>
                    <span className="inline-flex items-center gap-1 rounded-md bg-primary/10 px-2 py-0.5 text-primary text-xs">
                      {dest?.name ?? uuid}
                      <button
                        type="button"
                        aria-label={`Quitar ${dest?.name ?? uuid}`}
                        onClick={() =>
                          onChange(selected.filter((u) => u !== uuid))
                        }
                        className="text-primary/70 hover:text-primary"
                      >
                        <X className="size-3" />
                      </button>
                    </span>
                  </li>
                );
              })}
            </ul>
          )}
          {destinations.length === 0 ? (
            <p className="text-muted-foreground text-xs">
              No hay destinos configurados en este workflow.
            </p>
          ) : available.length > 0 ? (
            <Select
              value=""
              onValueChange={(v) => {
                if (v) onChange([...selected, v as string]);
              }}
            >
              <SelectTrigger className="h-9">
                <SelectValue placeholder="Añadir destino…" />
              </SelectTrigger>
              <SelectContent>
                {available.map((d) => (
                  <SelectItem key={d.uuid} value={d.uuid}>
                    {d.name}
                    <span className="ml-2 font-mono text-muted-foreground text-xs">
                      {d.uuid.slice(0, 8)}
                    </span>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <p className="text-muted-foreground text-xs">
              Todos los destinos están seleccionados.
            </p>
          )}
          {selected.length === 0 && (
            <p className="text-muted-foreground text-xs">
              Sin destinos seleccionados: no se entregará a nadie.
            </p>
          )}
        </>
      )}
    </div>
  );
}

/**
 * `human_review.approvers` (ApproverSpec): quién puede aprobar. Tres listas/campo
 * — roles, usuarios (user_ids) y una audiencia RBAC. Todo vacío ⇒ `undefined`
 * (sin restricción = comportamiento de hoy).
 */
function ApproverSpecField({
  value,
  onChange,
}: {
  value: unknown;
  onChange: (next: Record<string, unknown> | undefined) => void;
}) {
  const spec = asMap(value);
  const roles = Array.isArray(spec.roles) ? (spec.roles as string[]) : [];
  const users = Array.isArray(spec.users) ? (spec.users as string[]) : [];
  const audience = typeof spec.audience === "string" ? spec.audience : "";

  function commit(next: {
    roles: string[];
    users: string[];
    audience: string;
  }) {
    const clean: Record<string, unknown> = {};
    if (next.roles.length) clean.roles = next.roles;
    if (next.users.length) clean.users = next.users;
    if (next.audience.trim()) clean.audience = next.audience.trim();
    onChange(Object.keys(clean).length === 0 ? undefined : clean);
  }

  return (
    <div className="space-y-3 rounded-md border border-border bg-muted/30 p-3">
      <div className="space-y-1.5">
        <Label className="font-normal text-muted-foreground text-xs">
          Roles
        </Label>
        <StringListField
          value={roles}
          placeholder="rol y Enter…"
          onChange={(next) => commit({ roles: next ?? [], users, audience })}
        />
      </div>
      <div className="space-y-1.5">
        <Label className="font-normal text-muted-foreground text-xs">
          Usuarios
        </Label>
        <StringListField
          value={users}
          placeholder="user_id y Enter…"
          onChange={(next) => commit({ roles, users: next ?? [], audience })}
        />
      </div>
      <div className="space-y-1.5">
        <Label className="font-normal text-muted-foreground text-xs">
          Audiencia
        </Label>
        <Input
          value={audience}
          placeholder="audience RBAC…"
          onValueChange={(v) => commit({ roles, users, audience: v })}
        />
      </div>
    </div>
  );
}

function ConfigField({
  entry,
  fieldKey,
  field,
  value,
  doctypes,
  destinations,
  readOnly,
  onChange,
}: {
  entry: PhaseCatalogEntry;
  fieldKey: string;
  field: PhaseConfigField;
  value: unknown;
  doctypes: DoctypeOption[];
  destinations: DestinationOption[];
  readOnly: boolean;
  onChange: (value: unknown) => void;
}) {
  // extraction_gate.activation: la ActivationPolicy plegada (D-A) — editor dedicado
  // (umbrales, on_low_confidence, modo/severidades, stages L1/L2, muestreo/QA).
  if (fieldKey === "activation") {
    return (
      <PoliciesPanel
        activation={(value as ActivationPolicy) ?? {}}
        readOnly={readOnly}
        onActivationChange={onChange}
      />
    );
  }

  // fan_out_types: multi-chip de doctypes.
  if (fieldKey === "fan_out_types") {
    return (
      <FanOutTypesField
        value={Array.isArray(value) ? (value as string[]) : []}
        doctypes={doctypes}
        onChange={onChange}
      />
    );
  }

  // extract_text.per_type_overrides: mapa {slug → extractor}. El enum de
  // extractores vive en el MISMO entry (configSchema.extractor.enum).
  if (fieldKey === "per_type_overrides") {
    return (
      <PerTypeOverridesField
        value={asMap(value)}
        doctypes={doctypes}
        extractors={entry.configSchema.extractor?.enum ?? []}
        onChange={onChange}
      />
    );
  }

  // await_documents.required_types: mapa {slug → mínimo (entero ≥ 1)}.
  if (fieldKey === "required_types") {
    return (
      <RequiredTypesField
        value={asMap(value)}
        doctypes={doctypes}
        onChange={onChange}
      />
    );
  }

  // deliver.channels: allowlist de destinos webhook (switch + multi-select).
  if (fieldKey === "channels") {
    return (
      <ChannelsField
        value={Array.isArray(value) ? (value as string[]) : undefined}
        destinations={destinations}
        onChange={onChange}
      />
    );
  }

  // deliver.payload_projection: subconjunto de campos del output (chips libres).
  if (fieldKey === "payload_projection") {
    return (
      <StringListField
        value={Array.isArray(value) ? (value as string[]) : []}
        placeholder="campo del output y Enter…"
        onChange={onChange}
      />
    );
  }

  // human_review.approvers: ApproverSpec {roles, users, audience} (F4 · quórum).
  if (fieldKey === "approvers") {
    return <ApproverSpecField value={value} onChange={onChange} />;
  }

  if (field.enum) {
    const current = value == null ? "" : String(value);
    return (
      <Select
        value={current}
        onValueChange={(v) => onChange(v === "" ? undefined : v)}
      >
        <SelectTrigger className="h-9">
          <SelectValue placeholder="Sin definir" />
        </SelectTrigger>
        <SelectContent>
          {field.enum.map((opt) => (
            <SelectItem key={opt} value={opt}>
              {opt}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    );
  }

  if (field.type === "boolean") {
    return (
      <Switch
        checked={Boolean(value)}
        onCheckedChange={(checked) => onChange(checked)}
      />
    );
  }

  if (field.type === "number" || field.type === "integer") {
    return (
      <Input
        type="number"
        step={field.type === "integer" ? 1 : "any"}
        value={value == null ? "" : String(value)}
        onValueChange={(v) => onChange(v === "" ? undefined : Number(v))}
      />
    );
  }

  if (field.type === "object" || field.type === "array") {
    // JSON crudo para args/payload/output_schema embebidos.
    const text =
      value == null
        ? ""
        : typeof value === "string"
          ? value
          : JSON.stringify(value, null, 2);
    return (
      <textarea
        value={text}
        onChange={(e) => {
          const raw = e.target.value;
          if (!raw.trim()) {
            onChange(field.type === "array" ? [] : {});
            return;
          }
          try {
            onChange(JSON.parse(raw));
          } catch {
            // Mantén el string crudo mientras edita JSON inválido; el publish
            // lo rechaza con un 422 si nunca se vuelve válido.
            onChange(raw);
          }
        }}
        rows={4}
        className={cn(
          "w-full rounded-md border border-input bg-white px-2.5 py-1.5 font-mono text-xs shadow-xs",
          "focus-visible:border-ring focus-visible:ring-ring/50 focus-visible:ring-[3px] outline-none"
        )}
      />
    );
  }

  return (
    <Input
      value={value == null ? "" : String(value)}
      onValueChange={(v) => onChange(v === "" ? undefined : v)}
    />
  );
}

export function PhaseConfigForm({
  entry,
  config,
  onChange,
  doctypes,
  destinations = [],
  readOnly = false,
}: PhaseConfigFormProps) {
  if (!entry) return null;
  const fields = Object.entries(entry.configSchema);

  if (!fields.length) {
    return (
      <p className="text-sm text-muted-foreground">
        Esta fase no tiene configuración.
      </p>
    );
  }

  function update(key: string, value: unknown) {
    const next = { ...config };
    if (value === undefined) delete next[key];
    else next[key] = value;
    onChange(next);
  }

  return (
    <div className="space-y-4">
      {fields.map(([key, field]) => (
        <div key={key} className="space-y-1.5">
          <Label htmlFor={`cfg-${key}`} className="text-xs">
            <span className="font-mono">{key}</span>
            <span className="font-normal text-muted-foreground">
              {humanize(key)}
            </span>
          </Label>
          <ConfigField
            entry={entry}
            fieldKey={key}
            field={field}
            value={config[key]}
            doctypes={doctypes}
            destinations={destinations}
            readOnly={readOnly}
            onChange={(v) => update(key, v)}
          />
        </div>
      ))}
    </div>
  );
}
