import type { useTranslations } from "next-intl";

import { stripMarkdown } from "@/src/application/lib/strip-markdown";
import type {
  MissingDataHandling,
  UpdateDocumentTypePayload,
  ValidationRulePayload,
} from "@/src/domain/repositories/doctype";
import type { ImportChange } from "./import-doctype-modal";

// Translator scoped to the `DoctypeSettingsTab` namespace, where the import copy
// lives. Both the settings tab and the list import reuse this parser, so the
// caller supplies its own `t`.
export type ImportTranslator = ReturnType<typeof useTranslations>;

export type DoctypeImportResult =
  | { ok: true; payload: UpdateDocumentTypePayload; changes: ImportChange[] }
  | { ok: false; error: string };

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

function truncate(value: string, max = 60): string {
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
}

function generateRuleId(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
}

function toRulePayload(raw: Record<string, unknown>): ValidationRulePayload {
  const missing = (raw.missingHandling ?? raw.missingDataHandling) as
    | MissingDataHandling
    | undefined;
  return {
    id: String(raw.id ?? raw.uuid ?? generateRuleId()),
    name: typeof raw.name === "string" ? raw.name : "",
    prompt: typeof raw.prompt === "string" ? raw.prompt : "",
    enabled: typeof raw.enabled === "boolean" ? raw.enabled : true,
    missingHandling: missing ?? "skip",
  };
}

/**
 * True when a JSON Schema object defines at least one field. The backend rejects
 * a schema with empty `properties`, so callers that create/update must drop an
 * empty `fields` payload rather than send it.
 */
export function schemaHasFields(fields: unknown): boolean {
  return (
    isPlainObject(fields) &&
    isPlainObject(fields.properties) &&
    Object.keys(fields.properties).length > 0
  );
}

/**
 * Validate a parsed JSON object as a document-type import and build the update
 * payload plus a human-readable change list for the confirm modal.
 *
 * The document `uuid` is intentionally never read: an import always targets a
 * *different* document type (a freshly created one when importing from the list,
 * the current one from the settings tab), so reusing an id would collide on the
 * database primary key.
 */
export function parseDoctypeImport(
  raw: unknown,
  t: ImportTranslator
): DoctypeImportResult {
  if (!isPlainObject(raw)) {
    return { ok: false, error: t("importErrorNotObject") };
  }

  const payload: UpdateDocumentTypePayload = {};
  const changes: ImportChange[] = [];

  if ("name" in raw && raw.name != null) {
    if (typeof raw.name !== "string" || !raw.name.trim()) {
      return {
        ok: false,
        error: t("importErrorInvalidValue", { field: t("fieldName") }),
      };
    }
    payload.name = raw.name.trim();
    changes.push({ key: "name", label: t("fieldName"), preview: payload.name });
  }

  if ("slug" in raw && raw.slug != null) {
    if (typeof raw.slug !== "string") {
      return {
        ok: false,
        error: t("importErrorInvalidValue", { field: t("fieldSlug") }),
      };
    }
    payload.slug = raw.slug;
    changes.push({
      key: "slug",
      label: t("fieldSlug"),
      preview: raw.slug || t("importPreviewEmpty"),
    });
  }

  if ("description" in raw && raw.description != null) {
    if (typeof raw.description !== "string") {
      return {
        ok: false,
        error: t("importErrorInvalidValue", { field: t("fieldDescription") }),
      };
    }
    payload.description = raw.description;
    const text = stripMarkdown(raw.description).trim();
    changes.push({
      key: "description",
      label: t("fieldDescription"),
      preview: text ? truncate(text) : t("importPreviewEmpty"),
    });
  }

  if ("keywords" in raw && raw.keywords != null) {
    if (!isStringArray(raw.keywords)) {
      return {
        ok: false,
        error: t("importErrorInvalidValue", { field: t("fieldKeywords") }),
      };
    }
    payload.keywords = raw.keywords;
    changes.push({
      key: "keywords",
      label: t("fieldKeywords"),
      preview: t("importPreviewItems", { count: raw.keywords.length }),
    });
  }

  if ("examples" in raw && raw.examples != null) {
    if (!isStringArray(raw.examples)) {
      return {
        ok: false,
        error: t("importErrorInvalidValue", { field: t("fieldExamples") }),
      };
    }
    payload.examples = raw.examples;
    changes.push({
      key: "examples",
      label: t("fieldExamples"),
      preview: t("importPreviewItems", { count: raw.examples.length }),
    });
  }

  if ("fields" in raw && raw.fields != null) {
    if (!isPlainObject(raw.fields) || raw.fields.type !== "object") {
      return { ok: false, error: t("importErrorInvalidSchema") };
    }
    payload.fields = raw.fields;
    const propertyCount = isPlainObject(raw.fields.properties)
      ? Object.keys(raw.fields.properties).length
      : 0;
    changes.push({
      key: "fields",
      label: t("fieldFields"),
      preview: t("importPreviewProperties", { count: propertyCount }),
    });
  }

  if ("validationRules" in raw && raw.validationRules != null) {
    if (!Array.isArray(raw.validationRules)) {
      return {
        ok: false,
        error: t("importErrorInvalidValue", {
          field: t("fieldValidationRules"),
        }),
      };
    }
    const rules = raw.validationRules.filter(isPlainObject).map(toRulePayload);
    payload.validationRules = rules;
    changes.push({
      key: "validationRules",
      label: t("fieldValidationRules"),
      preview: t("importPreviewRules", { count: rules.length }),
    });
  }

  if (changes.length === 0) {
    return { ok: false, error: t("importErrorNoData") };
  }

  return { ok: true, payload, changes };
}
