export interface JsonSchemaNode {
  type?: string | string[];
  properties?: Record<string, JsonSchemaNode>;
  items?: JsonSchemaNode;
  [key: string]: unknown;
}

/**
 * Walk a JSON Schema object and collect all dotted paths reachable from the
 * root (leaves + intermediate object/array branches). Example:
 *   { type: "object", properties: { persona: { type: "object", properties: { nombres: { type: "string" } } } } }
 * returns: ["persona", "persona.nombres"]
 */
export function flattenSchemaPaths(schema: unknown): string[] {
  const out: string[] = [];
  function walk(node: JsonSchemaNode | undefined, prefix: string) {
    if (!node || typeof node !== "object") return;
    if (node.properties && typeof node.properties === "object") {
      for (const [key, child] of Object.entries(node.properties)) {
        const path = prefix ? `${prefix}.${key}` : key;
        out.push(path);
        walk(child as JsonSchemaNode, path);
      }
    } else if (node.items) {
      walk(node.items, prefix);
    }
  }
  walk(schema as JsonSchemaNode, "");
  return out;
}
