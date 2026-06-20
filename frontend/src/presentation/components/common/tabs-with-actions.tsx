"use client";

import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";
import { cn } from "@/src/application/lib/utils";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "@/src/presentation/components/ui/tabs";

export interface TabAction {
  label: string;
  icon?: LucideIcon;
  onClick?: () => void;
  variant?: "default" | "primary" | "destructive";
  separator?: boolean;
  disabled?: boolean;
  title?: string;
  /** When provided, replaces the default Button rendering with a custom node. */
  render?: () => ReactNode;
}

export interface TabDefinition {
  value: string;
  // ReactNode para permitir indicadores junto al texto (p.ej. dot LIVE de
  // Actividad mientras hay procesamiento en vuelo).
  label: ReactNode;
  icon?: LucideIcon;
  content: ReactNode;
  actions?: TabAction[];
}

interface TabsWithActionsProps {
  tabs: TabDefinition[];
  defaultValue?: string;
  value?: string;
  onValueChange?: (value: string) => void;
  className?: string;
  contentClassName?: string;
  listVariant?: "default" | "line";
  triggerVariant?: "default" | "line";
}

export function TabsWithActions({
  tabs,
  defaultValue,
  value,
  onValueChange,
  className,
  contentClassName,
  listVariant,
  triggerVariant,
}: TabsWithActionsProps) {
  const controlled = value !== undefined;
  const activeTab = controlled ? value : undefined;

  const currentActions = tabs.find(
    (t) => t.value === (activeTab ?? defaultValue ?? tabs[0]?.value)
  )?.actions;

  return (
    <Tabs
      defaultValue={controlled ? undefined : (defaultValue ?? tabs[0]?.value)}
      value={controlled ? value : undefined}
      onValueChange={onValueChange}
      className={cn("flex-1 min-h-0 flex flex-col", className)}
    >
      <div className="flex items-center justify-between">
        <TabsList variant={listVariant}>
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.value}
              value={tab.value}
              variant={triggerVariant}
              className="gap-2"
            >
              {tab.icon && <tab.icon className="h-4 w-4" />}
              {tab.label}
            </TabsTrigger>
          ))}
        </TabsList>

        {currentActions && currentActions.length > 0 && (
          <div className="flex items-center gap-2">
            {currentActions.map((action) => {
              if (action.render) {
                return <span key={action.label}>{action.render()}</span>;
              }
              const ActionIcon = action.icon;
              return (
                <Button
                  key={action.label}
                  variant={action.variant === "primary" ? "default" : "outline"}
                  size="default"
                  onClick={action.onClick}
                  disabled={action.disabled}
                  title={action.title}
                  className={cn(
                    "gap-2 cursor-pointer",
                    action.variant === "destructive" &&
                      "text-destructive border-destructive/30 hover:bg-destructive/10"
                  )}
                >
                  {ActionIcon && <ActionIcon className="h-4 w-4" />}
                  {action.label}
                </Button>
              );
            })}
          </div>
        )}
      </div>

      {tabs.map((tab) => (
        <TabsContent
          key={tab.value}
          value={tab.value}
          className={cn("mt-8 flex-1 min-h-0 flex flex-col", contentClassName)}
        >
          {tab.content}
        </TabsContent>
      ))}
    </Tabs>
  );
}
