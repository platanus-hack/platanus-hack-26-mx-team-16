"use client";

import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import { Checkbox } from "@/src/presentation/components/ui/checkbox";

interface ArrayConstraintsProps {
  schema: JSONSchemaObject;
  onChange: (updates: Partial<JSONSchemaObject>) => void;
}

export function ArrayConstraints({ schema, onChange }: ArrayConstraintsProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Min Items</Label>
          <Input
            type="number"
            min={0}
            value={schema.minItems ?? ""}
            onChange={(e) =>
              onChange({
                minItems: e.target.value ? parseInt(e.target.value) : undefined,
              })
            }
            placeholder="No limit"
          />
        </div>
        <div className="space-y-2">
          <Label>Max Items</Label>
          <Input
            type="number"
            min={0}
            value={schema.maxItems ?? ""}
            onChange={(e) =>
              onChange({
                maxItems: e.target.value ? parseInt(e.target.value) : undefined,
              })
            }
            placeholder="No limit"
          />
        </div>
      </div>

      <div className="flex items-center space-x-2">
        <Checkbox
          id="unique-items"
          checked={schema.uniqueItems ?? false}
          onCheckedChange={(checked) =>
            onChange({ uniqueItems: checked === true ? true : undefined })
          }
        />
        <Label htmlFor="unique-items" className="text-sm font-normal">
          Unique Items
        </Label>
      </div>
    </div>
  );
}
