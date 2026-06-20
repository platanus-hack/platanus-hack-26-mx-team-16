"use client";

import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import { Checkbox } from "@/src/presentation/components/ui/checkbox";

interface ObjectConstraintsProps {
  schema: JSONSchemaObject;
  onChange: (updates: Partial<JSONSchemaObject>) => void;
}

export function ObjectConstraints({
  schema,
  onChange,
}: ObjectConstraintsProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Min Properties</Label>
          <Input
            type="number"
            min={0}
            value={schema.minProperties ?? ""}
            onChange={(e) =>
              onChange({
                minProperties: e.target.value
                  ? parseInt(e.target.value)
                  : undefined,
              })
            }
            placeholder="No limit"
          />
        </div>
        <div className="space-y-2">
          <Label>Max Properties</Label>
          <Input
            type="number"
            min={0}
            value={schema.maxProperties ?? ""}
            onChange={(e) =>
              onChange({
                maxProperties: e.target.value
                  ? parseInt(e.target.value)
                  : undefined,
              })
            }
            placeholder="No limit"
          />
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Checkbox
          id="additional-properties"
          checked={schema.additionalProperties !== false}
          onCheckedChange={(checked) =>
            onChange({ additionalProperties: checked === true ? true : false })
          }
        />
        <Label htmlFor="additional-properties" className="text-sm font-normal">
          Allow Additional Properties
        </Label>
      </div>
    </div>
  );
}
