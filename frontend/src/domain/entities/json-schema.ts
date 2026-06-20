// JSON Schema domain entities and types

export type JSONSchemaType =
  | "string"
  | "number"
  | "integer"
  | "boolean"
  | "null"
  | "array"
  | "object";

export interface JSONSchemaObject {
  type?: JSONSchemaType | JSONSchemaType[];
  title?: string;
  description?: string;
  properties?: Record<string, JSONSchemaObject>;
  required?: string[];
  items?: JSONSchemaObject;
  enum?: any[];
  const?: any;
  default?: any;

  // String constraints
  minLength?: number;
  maxLength?: number;
  pattern?: string;
  format?: string;

  // Number constraints
  minimum?: number;
  maximum?: number;
  exclusiveMinimum?: number | boolean;
  exclusiveMaximum?: number | boolean;
  multipleOf?: number;

  // Array constraints
  minItems?: number;
  maxItems?: number;
  uniqueItems?: boolean;

  // Object constraints
  minProperties?: number;
  maxProperties?: number;
  additionalProperties?: boolean | JSONSchemaObject;

  // Composition
  oneOf?: JSONSchemaObject[];
  anyOf?: JSONSchemaObject[];
  allOf?: JSONSchemaObject[];
  not?: JSONSchemaObject;

  // References
  $ref?: string;
  $defs?: Record<string, JSONSchemaObject>;
}

export interface ValidationError {
  path: string;
  message: string;
  keyword: string;
  params?: Record<string, any>;
}

export interface SchemaNode {
  path: string[];
  key: string;
  schema: JSONSchemaObject;
  parent?: SchemaNode;
  children?: SchemaNode[];
}

export const DEFAULT_SCHEMAS: Record<JSONSchemaType, JSONSchemaObject> = {
  string: { type: "string" },
  number: { type: "number" },
  integer: { type: "integer" },
  boolean: { type: "boolean" },
  null: { type: "null" },
  array: { type: "array", items: { type: "string" } },
  object: { type: "object", properties: {} },
};

export const STRING_FORMATS = [
  "date-time",
  "date",
  "time",
  "email",
  "hostname",
  "ipv4",
  "ipv6",
  "uri",
  "uri-reference",
  "uuid",
  "regex",
] as const;

export type StringFormat = (typeof STRING_FORMATS)[number];
