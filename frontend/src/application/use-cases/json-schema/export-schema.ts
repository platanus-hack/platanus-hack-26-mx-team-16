import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";

export function exportSchemaAsJSON(
  schema: JSONSchemaObject,
  pretty = true
): string {
  return pretty ? JSON.stringify(schema, null, 2) : JSON.stringify(schema);
}

export function exportSchemaAsFile(
  schema: JSONSchemaObject,
  filename = "schema.json"
): void {
  const jsonString = exportSchemaAsJSON(schema, true);
  const blob = new Blob([jsonString], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export async function copySchemaToClipboard(
  schema: JSONSchemaObject
): Promise<boolean> {
  const jsonString = exportSchemaAsJSON(schema, true);

  try {
    await navigator.clipboard.writeText(jsonString);
    return true;
  } catch (error) {
    console.error("Failed to copy to clipboard:", error);
    return false;
  }
}
