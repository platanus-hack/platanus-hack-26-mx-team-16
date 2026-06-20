"use client";

import { BookOpen, Key, Plus, Users } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import { Switch } from "@/src/presentation/components/ui/switch";

interface DataExportConfigFormProps {
  workflowSlug: string;
}

interface Integration {
  id: string;
  name: string;
  icon: string;
  documentType: string;
  runs: number;
  enabled: boolean;
}

const MOCK_INTEGRATIONS: Integration[] = [
  {
    id: "1",
    name: "Google Photos",
    icon: "📸",
    documentType: "CVs",
    runs: 0,
    enabled: false,
  },
];

export function DataExportConfigForm({
  workflowSlug: _workflowSlug,
}: DataExportConfigFormProps) {
  const t = useTranslations("DataExportConfig");
  const [integrations, setIntegrations] =
    useState<Integration[]>(MOCK_INTEGRATIONS);

  const handleToggleIntegration = (id: string) => {
    setIntegrations(
      integrations.map((int) =>
        int.id === id ? { ...int, enabled: !int.enabled } : int
      )
    );
  };

  const handleAddIntegration = () => {
    console.log("Add integration");
  };

  const handleManageKeys = () => {
    console.log("Manage keys");
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <div className="flex items-center gap-2">
          <h3 className="text-base font-semibold">{t("integrationsTitle")}</h3>
          <Badge
            variant="secondary"
            className="bg-blue-500 text-white hover:bg-blue-600"
          >
            {t("beta")}
          </Badge>
        </div>

        <p className="text-sm text-muted-foreground">
          {t("integrationsDescription")}
        </p>

        <div className="border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-muted/20">
              <tr className="border-b border-border/50">
                <th className="px-4 py-3 text-left text-sm font-normal text-muted-foreground">
                  {t("columns.integration")}
                </th>
                <th className="px-4 py-3 text-left text-sm font-normal text-muted-foreground">
                  {t("columns.documentType")}
                </th>
                <th className="px-4 py-3 text-left text-sm font-normal text-muted-foreground">
                  {t("columns.runs")}
                </th>
                <th className="px-4 py-3 text-right text-sm font-normal text-muted-foreground">
                  {t("columns.status")}
                </th>
              </tr>
            </thead>
            <tbody>
              {integrations.map((integration) => (
                <tr
                  key={integration.id}
                  className="border-b border-border/30 last:border-b-0"
                >
                  <td className="px-4 py-4">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{integration.icon}</span>
                      <span className="text-sm">{integration.name}</span>
                    </div>
                  </td>
                  <td className="px-4 py-4">
                    <div className="inline-flex items-center gap-1.5 px-2 py-1 bg-muted/50 rounded text-xs">
                      <svg
                        xmlns="http://www.w3.org/2000/svg"
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                        <polyline points="14 2 14 8 20 8" />
                      </svg>
                      {integration.documentType}
                    </div>
                  </td>
                  <td className="px-4 py-4 text-sm text-muted-foreground">-</td>
                  <td className="px-4 py-4">
                    <div className="flex justify-end">
                      <Switch
                        checked={integration.enabled}
                        onCheckedChange={() =>
                          handleToggleIntegration(integration.id)
                        }
                      />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleAddIntegration}
            className="text-blue-500 hover:text-blue-600 hover:bg-blue-50 p-0 h-auto font-normal"
          >
            <Plus className="h-4 w-4 mr-1" />
            {t("addIntegration")}
          </Button>
        </div>

        <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/20">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="shrink-0 mt-0.5 text-muted-foreground"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <div className="flex-1 flex flex-col gap-3">
            <p className="text-sm text-muted-foreground">{t("helpText")}</p>
            <div className="flex items-center gap-4">
              <a
                href="https://docs.llamit.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-500 hover:text-blue-600 flex items-center gap-1.5"
              >
                <BookOpen className="h-3.5 w-3.5" />
                {t("readDocs")}
              </a>
              <a
                href="https://llamit.ai/contact"
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-blue-500 hover:text-blue-600 flex items-center gap-1.5"
              >
                <Users className="h-3.5 w-3.5" />
                {t("contactTeam")}
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="border-t pt-6">
        <h3 className="text-base font-semibold mb-4">{t("apiTitle")}</h3>

        <div className="flex items-start gap-3">
          <Key className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
          <div className="flex-1 flex flex-col gap-2">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <h4 className="text-base font-semibold mb-1">
                  {t("apiKeysTitle")}
                </h4>
                <p className="text-sm text-muted-foreground">
                  {t("apiKeysDescription")}{" "}
                  <a
                    href="https://docs.llamit.ai/api"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:text-blue-600 underline"
                  >
                    {t("learnMore")}
                  </a>
                </p>
              </div>
              <Button
                variant="link"
                size="sm"
                onClick={handleManageKeys}
                className="text-blue-500 hover:text-blue-600 p-0 h-auto font-normal"
              >
                {t("manageKeys")}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
