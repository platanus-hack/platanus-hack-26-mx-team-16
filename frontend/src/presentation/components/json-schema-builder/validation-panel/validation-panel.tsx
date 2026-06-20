"use client";

import { useMemo } from "react";
import type {
  JSONSchemaObject,
  ValidationError,
} from "@/src/domain/entities/json-schema";
import { validateSchema } from "@/src/application/use-cases/json-schema/validate-schema";
import { ScrollArea } from "@/src/presentation/components/ui/scroll-area";
import {
  Alert,
  AlertDescription,
} from "@/src/presentation/components/ui/alert";
import { Badge } from "@/src/presentation/components/ui/badge";
import { CheckCircle2, XCircle, AlertCircle } from "lucide-react";

interface ValidationPanelProps {
  schema: JSONSchemaObject;
}

export function ValidationPanel({ schema }: ValidationPanelProps) {
  const validation = useMemo(() => validateSchema(schema), [schema]);

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b border-border/50">
        <h3 className="text-lg font-semibold">Validation</h3>
        {validation.isValid ? (
          <Badge variant="outline" className="gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
            Valid
          </Badge>
        ) : (
          <Badge variant="destructive" className="gap-1.5">
            <XCircle className="h-3.5 w-3.5" />
            {validation.errors.length}{" "}
            {validation.errors.length === 1 ? "Error" : "Errors"}
          </Badge>
        )}
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {validation.isValid ? (
            <Alert>
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <AlertDescription>
                Schema is valid and ready to use.
              </AlertDescription>
            </Alert>
          ) : (
            <>
              {validation.errors.map((error, index) => (
                <Alert key={index} variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <div className="space-y-1">
                      <div className="font-medium">{error.path || "root"}</div>
                      <div className="text-sm">{error.message}</div>
                      {error.keyword && (
                        <Badge variant="outline" className="text-xs">
                          {error.keyword}
                        </Badge>
                      )}
                    </div>
                  </AlertDescription>
                </Alert>
              ))}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
