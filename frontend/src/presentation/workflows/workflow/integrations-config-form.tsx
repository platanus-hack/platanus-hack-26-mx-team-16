"use client";

import { Check, Copy, Hash, Key } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/src/presentation/components/ui/button";

interface IntegrationsConfigFormProps {
  workflowSlug: string;
}

export function IntegrationsConfigForm({
  workflowSlug,
}: IntegrationsConfigFormProps) {
  const t = useTranslations("IntegrationsConfigForm");
  const [copiedWorkflowId, setCopiedWorkflowId] = useState(false);

  const workflowId = "dzuZlQyX";

  const handleCopyWorkflowId = async () => {
    try {
      await navigator.clipboard.writeText(workflowId);
      setCopiedWorkflowId(true);
      setTimeout(() => setCopiedWorkflowId(false), 2000);
    } catch (err) {
      console.error("Failed to copy workflow ID:", err);
    }
  };

  const handleManageKeys = () => {
    console.log("Navigate to manage API keys");
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-6">
        <h3 className="text-base font-semibold">{t("apiSettings")}</h3>

        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
            <Key className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <h4 className="text-base font-semibold mb-1">
                  {t("apiKeysTitle")}
                </h4>
                <p className="text-sm text-muted-foreground">
                  {t("apiKeysDescription")}{" "}
                  <a
                    href="https://docs.llamit.ai/api-keys"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-500 hover:text-blue-600 underline"
                  >
                    {t("learnMore")}
                  </a>
                </p>
              </div>
              <Button
                onClick={handleManageKeys}
                variant="link"
                className="text-blue-500 hover:text-blue-600 p-0 h-auto font-normal gap-1.5"
              >
                {t("manageKeys")}
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <path d="M7 7h10v10" />
                  <path d="M7 17 17 7" />
                </svg>
              </Button>
            </div>
          </div>
        </div>

        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
            <Hash className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex-1 flex flex-col gap-2">
            <div>
              <h4 className="text-base font-semibold mb-1">
                {t("workflowIdTitle")}
              </h4>
              <p className="text-sm text-muted-foreground">
                {t("workflowIdDescription")}
              </p>
            </div>
            <div className="flex items-center justify-between px-3 py-2 bg-muted rounded-md">
              <span className="font-mono text-sm font-medium text-blue-500">
                {workflowId}
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleCopyWorkflowId}
                title={t("copyAria")}
              >
                {copiedWorkflowId ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
