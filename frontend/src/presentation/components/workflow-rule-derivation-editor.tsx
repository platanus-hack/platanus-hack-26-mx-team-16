"use client";

import { useCallback, useMemo, useRef } from "react";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import type { WorkflowRuleConfigEditorProps } from "@/src/application/lib/workflow-rule-kinds";
import { JsonSchemaBuilder } from "@/src/presentation/components/json-schema-builder";

const EMPTY_SHAPE: JSONSchemaObject = {
  type: "object",
  properties: {},
};

/**
 * Config editor for the DERIVATION kind. Drives `config.output_shape` via the
 * existing JsonSchemaBuilder (Fields / Schema tabs) — same UX the document-type
 * fields editor uses, so users get a consistent experience across the app.
 *
 * The handler reads ``config`` through a ref to keep its identity stable —
 * JsonSchemaBuilder fires ``onChange`` from a useEffect on schema change, so
 * any parent-prop dependency would feed back and loop.
 */
export function DerivationConfigEditor({
  config,
  onChange,
}: WorkflowRuleConfigEditorProps) {
  // initialSchema is consumed once by useSchemaBuilder; recomputing on every
  // render would reset the editor — so we capture the first value only.
  const initial = useMemo<JSONSchemaObject>(
    () => (config?.output_shape as JSONSchemaObject | undefined) ?? EMPTY_SHAPE,
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  const configRef = useRef(config);
  configRef.current = config;
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;

  const handleChange = useCallback((next: JSONSchemaObject) => {
    onChangeRef.current({ ...configRef.current, output_shape: next });
  }, []);

  return (
    <div className="h-[420px] overflow-hidden bg-background">
      <JsonSchemaBuilder initialSchema={initial} onChange={handleChange} />
    </div>
  );
}
