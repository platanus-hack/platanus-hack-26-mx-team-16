"use client";

import { AlignLeft, Code, Redo2, Undo2 } from "lucide-react";
import { useEffect, useState } from "react";
import { cn } from "@/src/application/lib/utils";
import type { JSONSchemaObject } from "@/src/domain/entities/json-schema";
import { Button } from "@/src/presentation/components/ui/button";
import { ScrollArea } from "@/src/presentation/components/ui/scroll-area";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/src/presentation/components/ui/tabs";
import { useSchemaBuilder } from "./hooks/use-schema-builder";
import { SchemaFieldsList } from "./schema-fields-list";
import { SchemaPreview } from "./schema-preview/schema-preview";

type SchemaBuilderTab = "fields" | "schema";

interface JsonSchemaBuilderProps {
  initialSchema?: JSONSchemaObject;
  onChange?: (schema: JSONSchemaObject) => void;
  className?: string;
}

const TAB_TRIGGER_CLASS =
  "gap-2 text-muted-foreground data-active:text-blue-500 hover:text-blue-400";

export function JsonSchemaBuilder({
  initialSchema,
  onChange,
  className,
}: JsonSchemaBuilderProps) {
  const {
    schema,
    canUndo,
    canRedo,
    addProperty,
    removeProperty,
    renameProperty,
    reorderProperties,
    replaceSchemaAtPath,
    updateSchemaAtPath,
    toggleRequired,
    undo,
    redo,
  } = useSchemaBuilder(initialSchema);

  const [activeTab, setActiveTab] = useState<SchemaBuilderTab>("fields");

  useEffect(() => {
    onChange?.(schema);
  }, [schema, onChange]);

  const handleDescriptionChange = (
    path: string[],
    description: string | undefined
  ) => {
    updateSchemaAtPath(path, { description });
  };

  return (
    <div className={cn("flex h-full flex-col bg-background", className)}>
      <Tabs
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as SchemaBuilderTab)}
        className="flex h-full flex-col"
      >
        <div className="flex items-center justify-between border-b border-border/50">
          <TabsList variant="line" className="h-12">
            <TabsTrigger
              variant="line"
              value="fields"
              className={TAB_TRIGGER_CLASS}
            >
              <AlignLeft className="h-4 w-4" />
              <span className="text-sm">Fields</span>
            </TabsTrigger>
            <TabsTrigger
              variant="line"
              value="schema"
              className={TAB_TRIGGER_CLASS}
            >
              <Code className="h-4 w-4" />
              <span className="text-sm">Schema</span>
            </TabsTrigger>
          </TabsList>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="sm"
              onClick={undo}
              disabled={!canUndo}
              aria-label="Undo"
            >
              <Undo2 className="h-4 w-4" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={redo}
              disabled={!canRedo}
              aria-label="Redo"
            >
              <Redo2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex-1 overflow-hidden">
          <TabsContent value="fields" className="m-0 h-full">
            <ScrollArea className="h-full">
              <div className="p-4">
                <SchemaFieldsList
                  parentSchema={schema}
                  parentPath={[]}
                  depth={0}
                  onAdd={addProperty}
                  onRename={renameProperty}
                  onReplace={replaceSchemaAtPath}
                  onDescriptionChange={handleDescriptionChange}
                  onToggleRequired={toggleRequired}
                  onDelete={removeProperty}
                  onReorder={reorderProperties}
                />
              </div>
            </ScrollArea>
          </TabsContent>

          <TabsContent value="schema" className="m-0 h-full">
            <SchemaPreview schema={schema} />
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}
