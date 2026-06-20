import type {
  JSONSchemaObject,
  JSONSchemaType,
} from "@/src/domain/entities/json-schema";

export function generateSchemaFromJSON(data: any): JSONSchemaObject {
  if (data === null) {
    return { type: "null" };
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return {
        type: "array",
        items: { type: "string" },
      };
    }

    const itemSchemas = data.map(generateSchemaFromJSON);
    const firstType = itemSchemas[0].type;
    const allSameType = itemSchemas.every((s) => s.type === firstType);

    return {
      type: "array",
      items: allSameType ? itemSchemas[0] : { oneOf: itemSchemas },
    };
  }

  const type = typeof data;

  switch (type) {
    case "string":
      return { type: "string" };
    case "number":
      return Number.isInteger(data) ? { type: "integer" } : { type: "number" };
    case "boolean":
      return { type: "boolean" };
    case "object":
      const properties: Record<string, JSONSchemaObject> = {};
      const required: string[] = [];

      for (const [key, value] of Object.entries(data)) {
        properties[key] = generateSchemaFromJSON(value);
        if (value !== null && value !== undefined) {
          required.push(key);
        }
      }

      return {
        type: "object",
        properties,
        required: required.length > 0 ? required : undefined,
      };
    default:
      return { type: "string" };
  }
}

export function createEmptySchema(type: JSONSchemaType): JSONSchemaObject {
  switch (type) {
    case "object":
      return { type: "object", properties: {} };
    case "array":
      return { type: "array", items: { type: "string" } };
    case "string":
      return { type: "string" };
    case "number":
      return { type: "number" };
    case "integer":
      return { type: "integer" };
    case "boolean":
      return { type: "boolean" };
    case "null":
      return { type: "null" };
    default:
      return { type: "string" };
  }
}
