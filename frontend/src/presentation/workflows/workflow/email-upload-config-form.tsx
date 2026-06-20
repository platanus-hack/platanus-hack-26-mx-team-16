"use client";

import { Check, Copy, Mail, PlusCircle, RefreshCw } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";

interface EmailUploadConfigFormProps {
  workflowSlug: string;
}

export function EmailUploadConfigForm({
  workflowSlug,
}: EmailUploadConfigFormProps) {
  const t = useTranslations("EmailUploadConfig");
  const [emailInput, setEmailInput] = useState("");
  const [allowedEmails, setAllowedEmails] = useState<string[]>([]);
  const [copiedAddress, setCopiedAddress] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const uploadAddress = `${workflowSlug}-kbcjlux@api.affinda.com`;

  const handleCopyAddress = async () => {
    try {
      await navigator.clipboard.writeText(uploadAddress);
      setCopiedAddress(true);
      setTimeout(() => setCopiedAddress(false), 2000);
    } catch (err) {
      console.error("Failed to copy email address:", err);
    }
  };

  const handleRegenerateAddress = () => {
    console.log("Regenerate email address");
  };

  const handleAddEmail = () => {
    setError(null);

    if (!emailInput.trim()) {
      return;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(emailInput)) {
      setError(t("errors.invalidEmail"));
      return;
    }

    if (allowedEmails.includes(emailInput)) {
      setError(t("errors.alreadyInList"));
      return;
    }

    setAllowedEmails([...allowedEmails, emailInput]);
    setEmailInput("");

    console.log("Email added:", emailInput);
  };

  const handleRemoveEmail = (email: string) => {
    setAllowedEmails(allowedEmails.filter((e) => e !== email));
    console.log("Email removed:", email);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddEmail();
    }
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
            <Mail className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex-1 flex flex-col gap-3">
            <div>
              <h3 className="text-base font-semibold mb-1">
                {t("uploadAddressTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("uploadAddressDescription")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-muted rounded-md px-3 py-2 font-mono text-sm">
                {uploadAddress}
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleCopyAddress}
                title={t("copyTitle")}
              >
                {copiedAddress ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleRegenerateAddress}
                title={t("regenerateTitle")}
              >
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
            <Mail className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex-1 flex flex-col gap-3">
            <div>
              <h3 className="text-base font-semibold mb-1">
                {t("allowlistTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("allowlistDescription")}
              </p>
            </div>

            <div className="flex flex-col gap-2">
              <div className="flex items-center gap-2">
                <Input
                  type="email"
                  placeholder={t("emailPlaceholder")}
                  value={emailInput}
                  onChange={(e) => {
                    setEmailInput(e.target.value);
                    setError(null);
                  }}
                  onKeyDown={handleKeyDown}
                  className="flex-1"
                />
                <Button
                  onClick={handleAddEmail}
                  size="sm"
                  className="gap-2 bg-blue-500 hover:bg-blue-600 text-white"
                >
                  <PlusCircle className="h-4 w-4" />
                  {t("addEmail")}
                </Button>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>

            {allowedEmails.length > 0 && (
              <div className="flex flex-col gap-2 mt-2">
                {allowedEmails.map((email) => (
                  <div
                    key={email}
                    className="flex items-center justify-between px-3 py-2 bg-muted rounded-md"
                  >
                    <span className="text-sm">{email}</span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => handleRemoveEmail(email)}
                      className="text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
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
                      >
                        <path d="M18 6 6 18" />
                        <path d="m6 6 12 12" />
                      </svg>
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
