import {
  Braces,
  Brackets,
  Hash,
  ToggleLeft,
  Type,
  type LucideIcon,
} from "lucide-react";
import { FieldType } from "@/src/domain/entities/doctype";

export type FieldTypeMeta = { label: string; icon: LucideIcon };

export const FIELD_TYPE_META: Record<string, FieldTypeMeta> = {
  [FieldType.TEXT]: { label: "String", icon: Type },
  [FieldType.NUMBER]: { label: "Number", icon: Hash },
  [FieldType.CHECKBOX]: { label: "Boolean", icon: ToggleLeft },
  [FieldType.OBJECT]: { label: "Object", icon: Braces },
  [FieldType.ARRAY]: { label: "Array", icon: Brackets },
};
