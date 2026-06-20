import type {
  DocumentTypeField,
  FieldType,
} from "@/src/domain/entities/doctype";

export interface JsonSchemaNode {
  $schema?: string;
  type?: string;
  description?: string;
  format?: string;
  properties?: Record<string, JsonSchemaNode>;
  items?: JsonSchemaNode;
  required?: string[];
  examples?: unknown[];
  "x-ai-prompt"?: string;
  "x-slug"?: string;
  "x-alternatives"?: string;
  "x-location-hint"?: string;
  "x-keywords"?: string[];
}

export function fieldsToJsonSchema(
  fields: DocumentTypeField[]
): JsonSchemaNode {
  const properties: Record<string, JsonSchemaNode> = {};
  const required: string[] = [];

  for (const field of fields) {
    if (!field.enabled || !field.name || field.name.trim() === "") continue;
    properties[field.name] = fieldToSchema(field);
    if (field.required) required.push(field.name);
  }

  const schema: JsonSchemaNode = {
    $schema: "https://json-schema.org/draft-07/schema",
    type: "object",
    properties,
  };
  if (required.length > 0) schema.required = required;
  return schema;
}

function fieldToSchema(field: DocumentTypeField): JsonSchemaNode {
  const desc = field.description ?? "";
  let node: JsonSchemaNode;

  switch (field.type) {
    case "object": {
      const props: Record<string, JsonSchemaNode> = {};
      const req: string[] = [];
      for (const child of field.children ?? []) {
        if (!child.enabled || !child.name || child.name.trim() === "") continue;
        const k = child.name;
        props[k] = fieldToSchema(child);
        if (child.required) req.push(k);
      }
      node = { type: "object", description: desc, properties: props };
      if (req.length > 0) node.required = req;
      break;
    }
    case "array": {
      const itemField = field.children?.[0];
      if (itemField && itemField.enabled !== false) {
        node = {
          type: "array",
          description: desc,
          items: fieldToSchema(itemField),
        };
      } else {
        node = { type: "array", description: desc, items: { type: "string" } };
      }
      break;
    }
    case "text":
    case "textarea":
    case "select":
    case "location":
      node = { type: "string", description: desc };
      break;
    case "email":
      node = { type: "string", description: desc, format: "email" };
      break;
    case "date":
      node = { type: "string", description: desc, format: "date" };
      break;
    case "number":
      node = { type: "number", description: desc };
      break;
    case "checkbox":
      node = { type: "boolean", description: desc };
      break;
    case "multiselect":
      node = { type: "array", description: desc, items: { type: "string" } };
      break;
    case "file":
      node = { type: "string", description: desc, format: "uri" };
      break;
    default:
      node = { type: "string", description: desc };
  }

  if (field.aiPrompt) node["x-ai-prompt"] = field.aiPrompt;
  if (field.slug) node["x-slug"] = field.slug;
  if (field.alternatives) node["x-alternatives"] = field.alternatives;
  if (field.locationHint) node["x-location-hint"] = field.locationHint;
  if (field.examples && field.examples.length > 0)
    node.examples = field.examples;
  if (field.keywords && field.keywords.length > 0)
    node["x-keywords"] = field.keywords;

  return node;
}

export function jsonSchemaToFields(
  schema: JsonSchemaNode
): DocumentTypeField[] {
  if (!schema.properties) return [];

  const fields: DocumentTypeField[] = [];
  let order = 0;

  for (const [key, value] of Object.entries(schema.properties)) {
    fields.push(
      schemaToField(key, value, order, schema.required?.includes(key) ?? false)
    );
    order++;
  }

  return fields;
}

function schemaToField(
  key: string,
  schema: JsonSchemaNode,
  order: number,
  required: boolean
): DocumentTypeField {
  const resolved = Array.isArray(schema.type) ? schema.type[0] : schema.type;

  if (resolved === "object" && schema.properties) {
    const children: DocumentTypeField[] = [];
    let idx = 0;
    for (const [ck, cv] of Object.entries(schema.properties)) {
      children.push(
        schemaToField(ck, cv, idx, schema.required?.includes(ck) ?? false)
      );
      idx++;
    }
    return makeField(
      key,
      "object" as FieldType,
      schema,
      order,
      required,
      children
    );
  }

  if (resolved === "array" && schema.items) {
    const itemChild = schemaToField("item", schema.items, 0, false);
    return makeField(
      key,
      "array" as FieldType,
      schema,
      order,
      required,
      [itemChild]
    );
  }

  return makeField(key, resolveFieldType(schema), schema, order, required);
}

function makeField(
  name: string,
  type: FieldType,
  schema: JsonSchemaNode,
  order: number,
  required: boolean,
  children?: DocumentTypeField[]
): DocumentTypeField {
  return {
    uuid: generateUuid(),
    name,
    type,
    required,
    enabled: true,
    order,
    description: schema.description,
    aiPrompt: schema["x-ai-prompt"],
    slug: schema["x-slug"],
    alternatives: schema["x-alternatives"],
    locationHint: schema["x-location-hint"],
    examples: schema.examples as string[],
    keywords: schema["x-keywords"],
    children,
  };
}

function resolveFieldType(schema: JsonSchemaNode): FieldType {
  const t = Array.isArray(schema.type) ? schema.type[0] : schema.type;
  if (t === "string") {
    switch (schema.format) {
      case "email":
        return "email" as FieldType;
      case "date":
      case "date-time":
        return "date" as FieldType;
      case "uri":
        return "file" as FieldType;
      default:
        return "text" as FieldType;
    }
  }
  if (t === "number" || t === "integer") return "number" as FieldType;
  if (t === "boolean") return "checkbox" as FieldType;
  if (t === "array") return "multiselect" as FieldType;
  return "text" as FieldType;
}

function generateUuid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
}
