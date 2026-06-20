"use client";

import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";
import { Checkbox } from "@/src/presentation/components/ui/checkbox";

interface NumberConstraintsProps {
  schema: JSONSchemaObject;
  onChange: (updates: Partial<JSONSchemaObject>) => void;
}

export function NumberConstraints({
  schema,
  onChange,
}: NumberConstraintsProps) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Minimum</Label>
          <Input
            type="number"
            value={schema.minimum ?? ""}
            onChange={(e) =>
              onChange({
                minimum: e.target.value
                  ? parseFloat(e.target.value)
                  : undefined,
              })
            }
            placeholder="No limit"
          />
          <div className="flex items-center space-x-2">
            <Checkbox
              id="exclusive-min"
              checked={schema.exclusiveMinimum === true}
              onCheckedChange={(checked) =>
                onChange({
                  exclusiveMinimum: checked === true ? true : undefined,
                })
              }
            />
            <Label htmlFor="exclusive-min" className="text-sm font-normal">
              Exclusive
            </Label>
          </div>
        </div>

        <div className="space-y-2">
          <Label>Maximum</Label>
          <Input
            type="number"
            value={schema.maximum ?? ""}
            onChange={(e) =>
              onChange({
                maximum: e.target.value
                  ? parseFloat(e.target.value)
                  : undefined,
              })
            }
            placeholder="No limit"
          />
          <div className="flex items-center space-x-2">
            <Checkbox
              id="exclusive-max"
              checked={schema.exclusiveMaximum === true}
              onCheckedChange={(checked) =>
                onChange({
                  exclusiveMaximum: checked === true ? true : undefined,
                })
              }
            />
            <Label htmlFor="exclusive-max" className="text-sm font-normal">
              Exclusive
            </Label>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        <Label>Multiple Of</Label>
        <Input
          type="number"
          step="any"
          value={schema.multipleOf ?? ""}
          onChange={(e) =>
            onChange({
              multipleOf: e.target.value
                ? parseFloat(e.target.value)
                : undefined,
            })
          }
          placeholder="Any value"
        />
      </div>
    </div>
  );
}
