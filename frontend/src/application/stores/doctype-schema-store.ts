import { create } from "zustand";
import {
  type JsonSchemaNode,
  jsonSchemaToFields,
  fieldsToJsonSchema,
} from "@/src/application/use-cases/json-schema/doctype-schema-converter";
import type {
  DocumentTypeField,
  FieldType,
} from "@/src/domain/entities/doctype";

function generateUuid(): string {
  if (typeof crypto !== "undefined" && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(36).substring(2, 10)}`;
}

function updateFieldInTree(
  fields: DocumentTypeField[],
  updated: DocumentTypeField
): DocumentTypeField[] {
  return fields.map((f) => {
    if (f.uuid === updated.uuid) return updated;
    if (f.children) {
      return { ...f, children: updateFieldInTree(f.children, updated) };
    }
    return f;
  });
}

function deleteFieldFromTree(
  fields: DocumentTypeField[],
  uuid: string
): DocumentTypeField[] {
  return fields
    .filter((f) => f.uuid !== uuid)
    .map((f) => {
      if (f.children) {
        return { ...f, children: deleteFieldFromTree(f.children, uuid) };
      }
      return f;
    });
}

interface DocumentTypeSchemaState {
  doctypeUuid: string | null;
  fields: DocumentTypeField[];
  jsonSchema: JsonSchemaNode;
  isDirty: boolean;

  initialize: (doctypeUuid: string, fields: DocumentTypeField[]) => void;
  initializeFromSchema: (doctypeUuid: string, schema: JsonSchemaNode) => void;
  reset: () => void;

  addField: (type?: FieldType) => void;
  updateField: (updatedField: DocumentTypeField) => void;
  deleteField: (fieldUuid: string) => void;
  toggleField: (fieldUuid: string, enabled: boolean) => void;

  setFields: (fields: DocumentTypeField[]) => void;
}

function computeSchema(fields: DocumentTypeField[]): JsonSchemaNode {
  if (fields.length === 0) {
    return { type: "object", properties: {} };
  }
  return fieldsToJsonSchema(fields);
}

export const useDocumentTypeSchemaStore = create<DocumentTypeSchemaState>(
  (set, get) => ({
    doctypeUuid: null,
    fields: [],
    jsonSchema: { type: "object", properties: {} },
    isDirty: false,

    initialize: (doctypeUuid, fields) => {
      set({
        doctypeUuid,
        fields,
        jsonSchema: computeSchema(fields),
        isDirty: false,
      });
    },

    initializeFromSchema: (doctypeUuid, schema) => {
      const fields = jsonSchemaToFields(schema);
      set({
        doctypeUuid,
        fields,
        jsonSchema: schema,
        isDirty: false,
      });
    },

    reset: () => {
      set({
        doctypeUuid: null,
        fields: [],
        jsonSchema: { type: "object", properties: {} },
        isDirty: false,
      });
    },

    addField: (type = "text" as FieldType) => {
      const { fields } = get();
      const isStructured =
        type === ("object" as FieldType) || type === ("array" as FieldType);
      const newField: DocumentTypeField = {
        uuid: generateUuid(),
        name: isStructured ? "New Object" : "",
        type,
        required: false,
        enabled: true,
        order: fields.length,
        children: isStructured ? [] : undefined,
      };

      const updated = [...fields, newField];
      set({
        fields: updated,
        jsonSchema: computeSchema(updated),
        isDirty: true,
      });
    },

    updateField: (updatedField) => {
      const { fields } = get();
      let normalized = updatedField;
      if (
        (normalized.type === ("object" as FieldType) ||
          normalized.type === ("array" as FieldType)) &&
        !normalized.children
      ) {
        normalized = { ...normalized, children: [] };
      }

      const updated = updateFieldInTree(fields, normalized);
      set({
        fields: updated,
        jsonSchema: computeSchema(updated),
        isDirty: true,
      });
    },

    deleteField: (fieldUuid) => {
      const { fields } = get();
      const updated = deleteFieldFromTree(fields, fieldUuid);
      set({
        fields: updated,
        jsonSchema: computeSchema(updated),
        isDirty: true,
      });
    },

    toggleField: (fieldUuid, enabled) => {
      const { fields } = get();

      const toggleInTree = (list: DocumentTypeField[]): DocumentTypeField[] =>
        list.map((f) => {
          if (f.uuid === fieldUuid) return { ...f, enabled };
          if (f.children) {
            return { ...f, children: toggleInTree(f.children) };
          }
          return f;
        });

      const updated = toggleInTree(fields);
      set({
        fields: updated,
        jsonSchema: computeSchema(updated),
        isDirty: true,
      });
    },

    setFields: (fields) => {
      set({
        fields,
        jsonSchema: computeSchema(fields),
        isDirty: true,
      });
    },
  })
);
