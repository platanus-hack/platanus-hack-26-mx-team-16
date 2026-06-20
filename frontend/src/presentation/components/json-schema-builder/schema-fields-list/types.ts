import type {
  JSONSchemaObject,
  JSONSchemaType,
} from "@/src/domain/entities/json-schema";

export interface SchemaFieldsCallbacks {
  onAdd: (
    parentPath: string[],
    propertyName: string,
    type: JSONSchemaType
  ) => void;
  onRename: (parentPath: string[], oldName: string, newName: string) => void;
  onReplace: (path: string[], schema: JSONSchemaObject) => void;
  onDescriptionChange: (
    path: string[],
    description: string | undefined
  ) => void;
  onToggleRequired: (parentPath: string[], propertyName: string) => void;
  onDelete: (path: string[]) => void;
  onReorder: (parentPath: string[], fromIndex: number, toIndex: number) => void;
}
