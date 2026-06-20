"use client";

import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";

interface StringConstraintsProps {
  schema: JSONSchemaObject;
  onChange: (updates: Partial<JSONSchemaObject>) => void;
}

const STRING_FORMATS = [
  { value: "", label: "None" },
  { value: "email", label: "Email" },
  { value: "uri", label: "URI" },
  { value: "uuid", label: "UUID" },
  { value: "date", label: "Date" },
  { value: "date-time", label: "Date-Time" },
  { value: "time", label: "Time" },
  { value: "ipv4", label: "IPv4" },
  { value: "ipv6", label: "IPv6" },
];

export function StringConstraints({
  schema,
  onChange,
}: StringConstraintsProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Min Length</Label>
          <Input
            type="number"
            min={0}
            value={schema.minLength ?? ""}
            onChange={(e) =>
              onChange({
                minLength: e.target.value
                  ? parseInt(e.target.value)
                  : undefined,
              })
            }
            placeholder="No limit"
          />
        </div>
        <div className="space-y-2">
          <Label>Max Length</Label>
          <Input
            type="number"
            min={0}
            value={schema.maxLength ?? ""}
            onChange={(e) =>
              onChange({
                maxLength: e.target.value
                  ? parseInt(e.target.value)
                  : undefined,
              })
            }
            placeholder="No limit"
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Pattern (regex)</Label>
        <Input
          value={schema.pattern ?? ""}
          onChange={(e) =>
            onChange({
              pattern: e.target.value || undefined,
            })
          }
          placeholder="^[a-z]+$"
        />
      </div>

      <div className="space-y-2">
        <Label>Format</Label>
        <Select
          value={schema.format ?? ""}
          onValueChange={(value) =>
            onChange({
              format: value || undefined,
            })
          }
        >
          <SelectTrigger>
            <SelectValue placeholder="Select format" />
          </SelectTrigger>
          <SelectContent>
            {STRING_FORMATS.map((format) => (
              <SelectItem key={format.value} value={format.value}>
                {format.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
