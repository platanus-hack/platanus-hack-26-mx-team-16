import { useState, useCallback } from "react";
import type {
  JSONSchemaObject,
  JSONSchemaType,
} from "@/src/domain/entities/json-schema";
import { createEmptySchema } from "@/src/application/use-cases/json-schema/generate-schema";

export interface SchemaBuilderState {
  schema: JSONSchemaObject;
  selectedPath: string[];
  history: JSONSchemaObject[];
  historyIndex: number;
}

export function useSchemaBuilder(initialSchema?: JSONSchemaObject) {
  const [state, setState] = useState<SchemaBuilderState>({
    schema: initialSchema || { type: "object", properties: {} },
    selectedPath: [],
    history: [initialSchema || { type: "object", properties: {} }],
    historyIndex: 0,
  });

  const updateSchema = useCallback((newSchema: JSONSchemaObject) => {
    setState((prev) => ({
      ...prev,
      schema: newSchema,
      history: [...prev.history.slice(0, prev.historyIndex + 1), newSchema],
      historyIndex: prev.historyIndex + 1,
    }));
  }, []);

  const setSelectedPath = useCallback((path: string[]) => {
    setState((prev) => ({ ...prev, selectedPath: path }));
  }, []);

  const getSchemaAtPath = useCallback(
    (path: string[]): JSONSchemaObject | undefined => {
      let current: any = state.schema;
      for (const key of path) {
        if (current?.properties?.[key]) {
          current = current.properties[key];
        } else if (current?.items && key === "items") {
          current = current.items;
        } else {
          return undefined;
        }
      }
      return current;
    },
    [state.schema]
  );

  const updateSchemaAtPath = useCallback(
    (path: string[], updates: Partial<JSONSchemaObject>) => {
      const newSchema = JSON.parse(JSON.stringify(state.schema));
      let current: any = newSchema;

      for (let i = 0; i < path.length - 1; i++) {
        const key = path[i];
        if (current.properties?.[key]) {
          current = current.properties[key];
        } else if (current.items && key === "items") {
          current = current.items;
        }
      }

      const lastKey = path[path.length - 1];
      if (path.length === 0) {
        Object.assign(newSchema, updates);
      } else if (current.properties?.[lastKey]) {
        Object.assign(current.properties[lastKey], updates);
      } else if (current.items && lastKey === "items") {
        Object.assign(current.items, updates);
      }

      updateSchema(newSchema);
    },
    [state.schema, updateSchema]
  );

  const addProperty = useCallback(
    (parentPath: string[], propertyName: string, type: JSONSchemaType) => {
      const newSchema = JSON.parse(JSON.stringify(state.schema));
      let current: any = newSchema;

      for (const key of parentPath) {
        if (current.properties?.[key]) {
          current = current.properties[key];
        } else if (current.items && key === "items") {
          current = current.items;
        }
      }

      if (current.type === "object") {
        if (!current.properties) {
          current.properties = {};
        }
        current.properties[propertyName] = createEmptySchema(type);
      }

      updateSchema(newSchema);
    },
    [state.schema, updateSchema]
  );

  const removeProperty = useCallback(
    (path: string[]) => {
      if (path.length === 0) return;

      const newSchema = JSON.parse(JSON.stringify(state.schema));
      let current: any = newSchema;

      for (let i = 0; i < path.length - 1; i++) {
        const key = path[i];
        if (current.properties?.[key]) {
          current = current.properties[key];
        } else if (current.items && key === "items") {
          current = current.items;
        }
      }

      const lastKey = path[path.length - 1];
      if (current.properties?.[lastKey]) {
        delete current.properties[lastKey];

        // Also remove from required array if present
        if (current.required) {
          current.required = current.required.filter(
            (r: string) => r !== lastKey
          );
          if (current.required.length === 0) {
            delete current.required;
          }
        }
      }

      updateSchema(newSchema);
    },
    [state.schema, updateSchema]
  );

  const replaceSchemaAtPath = useCallback(
    (path: string[], replacement: JSONSchemaObject) => {
      if (path.length === 0) {
        updateSchema(replacement);
        return;
      }

      const newSchema = JSON.parse(JSON.stringify(state.schema));
      let current: any = newSchema;

      for (let i = 0; i < path.length - 1; i++) {
        const key = path[i];
        if (current.properties?.[key]) {
          current = current.properties[key];
        } else if (current.items && key === "items") {
          current = current.items;
        }
      }

      const lastKey = path[path.length - 1];
      if (current.properties && lastKey in current.properties) {
        current.properties[lastKey] = replacement;
      } else if (current.items && lastKey === "items") {
        current.items = replacement;
      }

      updateSchema(newSchema);
    },
    [state.schema, updateSchema]
  );

  const renameProperty = useCallback(
    (parentPath: string[], oldName: string, newName: string) => {
      if (!newName || oldName === newName) return;

      const newSchema = JSON.parse(JSON.stringify(state.schema));
      let current: any = newSchema;

      for (const key of parentPath) {
        if (current.properties?.[key]) {
          current = current.properties[key];
        } else if (current.items && key === "items") {
          current = current.items;
        }
      }

      if (!current.properties || !(oldName in current.properties)) return;
      if (newName in current.properties) return;

      const renamed: Record<string, JSONSchemaObject> = {};
      for (const key of Object.keys(current.properties)) {
        renamed[key === oldName ? newName : key] = current.properties[key];
      }
      current.properties = renamed;

      if (Array.isArray(current.required)) {
        current.required = current.required.map((r: string) =>
          r === oldName ? newName : r
        );
      }

      updateSchema(newSchema);
    },
    [state.schema, updateSchema]
  );

  const reorderProperties = useCallback(
    (parentPath: string[], fromIndex: number, toIndex: number) => {
      if (fromIndex === toIndex) return;

      const newSchema = JSON.parse(JSON.stringify(state.schema));
      let current: any = newSchema;

      for (const key of parentPath) {
        if (current.properties?.[key]) {
          current = current.properties[key];
        } else if (current.items && key === "items") {
          current = current.items;
        }
      }

      if (!current.properties) return;
      const keys = Object.keys(current.properties);
      if (fromIndex < 0 || fromIndex >= keys.length) return;
      if (toIndex < 0 || toIndex >= keys.length) return;

      const [moved] = keys.splice(fromIndex, 1);
      keys.splice(toIndex, 0, moved);

      const reordered: Record<string, JSONSchemaObject> = {};
      for (const key of keys) reordered[key] = current.properties[key];
      current.properties = reordered;

      updateSchema(newSchema);
    },
    [state.schema, updateSchema]
  );

  const toggleRequired = useCallback(
    (parentPath: string[], propertyName: string) => {
      const newSchema = JSON.parse(JSON.stringify(state.schema));
      let current: any = newSchema;

      for (const key of parentPath) {
        if (current.properties?.[key]) {
          current = current.properties[key];
        }
      }

      if (!current.required) {
        current.required = [];
      }

      const index = current.required.indexOf(propertyName);
      if (index === -1) {
        current.required.push(propertyName);
      } else {
        current.required.splice(index, 1);
        if (current.required.length === 0) {
          delete current.required;
        }
      }

      updateSchema(newSchema);
    },
    [state.schema, updateSchema]
  );

  const undo = useCallback(() => {
    if (state.historyIndex > 0) {
      setState((prev) => ({
        ...prev,
        schema: prev.history[prev.historyIndex - 1],
        historyIndex: prev.historyIndex - 1,
      }));
    }
  }, [state.historyIndex]);

  const redo = useCallback(() => {
    if (state.historyIndex < state.history.length - 1) {
      setState((prev) => ({
        ...prev,
        schema: prev.history[prev.historyIndex + 1],
        historyIndex: prev.historyIndex + 1,
      }));
    }
  }, [state.historyIndex, state.history.length]);

  return {
    schema: state.schema,
    selectedPath: state.selectedPath,
    canUndo: state.historyIndex > 0,
    canRedo: state.historyIndex < state.history.length - 1,
    setSelectedPath,
    getSchemaAtPath,
    updateSchemaAtPath,
    addProperty,
    removeProperty,
    renameProperty,
    reorderProperties,
    replaceSchemaAtPath,
    toggleRequired,
    updateSchema,
    undo,
    redo,
  };
}
