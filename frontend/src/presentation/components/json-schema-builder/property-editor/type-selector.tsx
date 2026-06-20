"use client";

import type { JSONSchemaType } from "@/src/domain/entities/json-schema";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Label } from "@/src/presentation/components/ui/label";

interface TypeSelectorProps {
  value: JSONSchemaType | JSONSchemaType[] | undefined;
  onChange: (type: JSONSchemaType) => void;
}

const TYPES: { value: JSONSchemaType; label: string }[] = [
  { value: "string", label: "String" },
  { value: "number", label: "Number" },
  { value: "integer", label: "Integer" },
  { value: "boolean", label: "Boolean" },
  { value: "array", label: "Array" },
  { value: "object", label: "Object" },
  { value: "null", label: "Null" },
];

export function TypeSelector({ value, onChange }: TypeSelectorProps) {
  const currentType = Array.isArray(value) ? value[0] : value;

  const handleChange = (newValue: string | null) => {
    if (newValue) {
      onChange(newValue as JSONSchemaType);
    }
  };

  return (
    <div className="space-y-2">
      <Label>Type</Label>
      <Select value={currentType || "string"} onValueChange={handleChange}>
        <SelectTrigger>
          <SelectValue placeholder="Select type" />
        </SelectTrigger>
        <SelectContent>
          {TYPES.map((type) => (
            <SelectItem key={type.value} value={type.value}>
              {type.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
