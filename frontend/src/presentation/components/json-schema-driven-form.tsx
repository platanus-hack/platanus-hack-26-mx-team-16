"use client";

import type { ChangeEvent } from "react";
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

interface JsonSchemaDrivenFormProps {
  schema: Record<string, unknown>;
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
}

interface OneOfOption {
  const: unknown;
  title?: string;
  description?: string;
}

interface PropertySchema {
  type?: string;
  enum?: unknown[];
  oneOf?: OneOfOption[];
  default?: unknown;
  title?: string;
  description?: string;
  format?: string;
}

interface NormalizedOption {
  value: string;
  label: string;
  description?: string;
}

function getEnumOptions(propSchema: PropertySchema): NormalizedOption[] | null {
  if (Array.isArray(propSchema.oneOf) && propSchema.oneOf.every((o) => "const" in o)) {
    return propSchema.oneOf.map((option) => ({
      value: String(option.const),
      label: option.title ?? String(option.const),
      description: option.description,
    }));
  }
  if (Array.isArray(propSchema.enum)) {
    return propSchema.enum.map((option) => ({
      value: String(option),
      label: String(option),
    }));
  }
  return null;
}

/**
 * Minimal JSON-Schema-driven editor for kind config (spec §4.3, §13.2).
 * Supports type=string, number, boolean and string-enum at the root level.
 * Anything more complex (object/array) falls back to a JSON textarea.
 */
export function JsonSchemaDrivenForm({
  schema,
  value,
  onChange,
}: JsonSchemaDrivenFormProps) {
  const properties = (schema?.properties ?? {}) as Record<string, PropertySchema>;
  const required = new Set((schema?.required ?? []) as string[]);

  const set = (key: string, next: unknown) => onChange({ ...value, [key]: next });

  if (Object.keys(properties).length === 0) {
    return (
      <FallbackJsonEditor
        value={value}
        onChange={onChange}
        label="Configuración (JSON)"
      />
    );
  }

  const entries = Object.entries(properties);
  const hasSeverityFailActionPair =
    "severity" in properties && "fail_action" in properties;

  const renderField = (key: string, propSchema: PropertySchema) => {
    const current = value[key] ?? propSchema.default;
    const titleText = propSchema.title ?? key;
    const label = `${titleText}${required.has(key) ? " *" : ""}`;
    const options = getEnumOptions(propSchema);

    if (options) {
      const currentValue = current == null ? "" : String(current);
      const hasDescriptions = options.some((o) => Boolean(o.description));
      return (
        <Field key={key} label={label} description={propSchema.description}>
          <Select
            value={currentValue}
            onValueChange={(next) => set(key, next)}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Selecciona…">
                {(value) =>
                  options.find((o) => o.value === value)?.label ?? value
                }
              </SelectValue>
            </SelectTrigger>
            <SelectContent
              className={
                hasDescriptions
                  ? "w-auto min-w-(--anchor-width) max-w-[min(28rem,calc(100vw-2rem))]"
                  : undefined
              }
            >
              {options.map((option) => (
                <SelectItem
                  key={option.value}
                  value={option.value}
                  className={
                    option.description
                      ? "items-start py-2 [&>span:first-child]:whitespace-normal [&>span:first-child]:items-start"
                      : undefined
                  }
                >
                  {option.description ? (
                    <div className="flex flex-col gap-0.5">
                      <span className="text-sm font-medium leading-tight">
                        {option.label}
                      </span>
                      <span className="text-xs text-muted-foreground leading-snug">
                        {option.description}
                      </span>
                    </div>
                  ) : (
                    option.label
                  )}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>
      );
    }

    if (propSchema.type === "boolean") {
      return (
        <Field key={key} label={label} description={propSchema.description}>
          <Switch
            checked={Boolean(current)}
            onCheckedChange={(next) => set(key, next)}
          />
        </Field>
      );
    }

    if (propSchema.type === "number" || propSchema.type === "integer") {
      return (
        <Field key={key} label={label} description={propSchema.description}>
          <Input
            type="number"
            value={Number.isFinite(current as number) ? String(current) : ""}
            onChange={(e: ChangeEvent<HTMLInputElement>) => {
              const parsed = e.target.value === "" ? undefined : Number(e.target.value);
              set(key, parsed);
            }}
          />
        </Field>
      );
    }

    if (propSchema.type === "object") {
      return (
        <FallbackJsonEditor
          key={key}
          label={label}
          description={propSchema.description}
          value={(current as Record<string, unknown>) ?? {}}
          onChange={(next) => set(key, next)}
        />
      );
    }

    return (
      <Field key={key} label={label} description={propSchema.description}>
        <Input
          type="text"
          value={typeof current === "string" ? current : ""}
          onChange={(e) => set(key, e.target.value)}
        />
      </Field>
    );
  };

  return (
    <div className="flex flex-col gap-4">
      {entries.map(([key, propSchema]) => {
        if (hasSeverityFailActionPair && key === "fail_action") return null;
        if (hasSeverityFailActionPair && key === "severity") {
          return (
            <div key="severity-fail-action" className="grid grid-cols-2 gap-3">
              {renderField("severity", properties.severity)}
              {renderField("fail_action", properties.fail_action)}
            </div>
          );
        }
        return renderField(key, propSchema);
      })}
    </div>
  );
}

function Field({
  label,
  description,
  children,
}: {
  label: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label className="text-sm font-medium">{label}</Label>
      {children}
      {description ? (
        <p className="text-xs text-muted-foreground">{description}</p>
      ) : null}
    </div>
  );
}

function FallbackJsonEditor({
  value,
  onChange,
  label = "JSON",
  description,
}: {
  value: Record<string, unknown>;
  onChange: (next: Record<string, unknown>) => void;
  label?: string;
  description?: string;
}) {
  return (
    <Field label={label} description={description}>
      <textarea
        className="min-h-[140px] rounded-md border bg-background p-2 font-mono text-xs"
        value={JSON.stringify(value, null, 2)}
        onChange={(e) => {
          try {
            onChange(JSON.parse(e.target.value));
          } catch {
            // ignore — keep last valid value
          }
        }}
      />
    </Field>
  );
}
