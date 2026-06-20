export interface ErrorItem {
  message: string;
  code: string;
}

export interface ErrorFeeback {
  errors: Array<ErrorItem>;
  validation: object | null;
}

export function isErrorFeedback(obj: unknown): obj is ErrorFeeback {
  return (
    typeof obj === "object" &&
    obj !== null &&
    "errors" in (obj as Record<string, unknown>) &&
    "validation" in (obj as Record<string, unknown>)
  );
}

export function showErrorItems(errors: Array<ErrorItem>): string {
  return errors.map((error) => error.message).join(", ");
}
