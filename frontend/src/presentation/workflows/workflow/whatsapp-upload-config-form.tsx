"use client";

import { Check, Copy, Phone, PlusCircle, QrCode } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { Button } from "@/src/presentation/components/ui/button";
import { Input } from "@/src/presentation/components/ui/input";

interface WhatsappUploadConfigFormProps {
  workflowSlug: string;
}

export function WhatsappUploadConfigForm({
  workflowSlug,
}: WhatsappUploadConfigFormProps) {
  const t = useTranslations("WhatsappUploadConfig");
  const [phoneInput, setPhoneInput] = useState("");
  const [allowedPhones, setAllowedPhones] = useState<string[]>([]);
  const [copiedPhone, setCopiedPhone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const whatsappNumber = "+1 (555) 123-4567";

  const handleCopyPhone = async () => {
    try {
      await navigator.clipboard.writeText(whatsappNumber);
      setCopiedPhone(true);
      setTimeout(() => setCopiedPhone(false), 2000);
    } catch (err) {
      console.error("Failed to copy phone number:", err);
    }
  };

  const handleAddPhone = () => {
    setError(null);

    if (!phoneInput.trim()) {
      return;
    }

    const phoneRegex = /^[\d\s\-\+\(\)]+$/;
    if (!phoneRegex.test(phoneInput) || phoneInput.length < 10) {
      setError(t("errors.invalidPhone"));
      return;
    }

    if (allowedPhones.includes(phoneInput)) {
      setError(t("errors.alreadyInList"));
      return;
    }

    setAllowedPhones([...allowedPhones, phoneInput]);
    setPhoneInput("");

    console.log("Phone added:", phoneInput);
  };

  const handleRemovePhone = (phone: string) => {
    setAllowedPhones(allowedPhones.filter((p) => p !== phone));
    console.log("Phone removed:", phone);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddPhone();
    }
  };

  const handleShowQRCode = () => {
    console.log("Show QR code");
  };

  return (
    <div className="flex flex-col gap-8">
      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
            <Phone className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex-1 flex flex-col gap-3">
            <div>
              <h3 className="text-base font-semibold mb-1">
                {t("numberTitle")}
              </h3>
              <p className="text-sm text-muted-foreground">
                {t("numberDescription")}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-muted rounded-md px-3 py-2 font-mono text-sm">
                {whatsappNumber}
              </div>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleCopyPhone}
                title={t("copyTitle")}
              >
                {copiedPhone ? (
                  <Check className="h-4 w-4 text-green-500" />
                ) : (
                  <Copy className="h-4 w-4" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon-sm"
                onClick={handleShowQRCode}
                title={t("qrTitle")}
              >
                <QrCode className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
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
              className="text-muted-foreground"
            >
              <circle cx="12" cy="12" r="10" />
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
          </div>
          <div className="flex-1 flex flex-col gap-3">
            <div>
              <h3 className="text-base font-semibold mb-1">
                {t("howToUseTitle")}
              </h3>
              <div className="text-sm text-muted-foreground space-y-2">
                <p>{t("step1")}</p>
                <p>{t("step2")}</p>
                <p>{t("step3")}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="flex flex-col gap-4">
        <div className="flex items-start gap-3">
          <div className="flex shrink-0 items-center justify-center w-8 h-8 rounded-full bg-muted">
            <Phone className="h-4 w-4 text-muted-foreground" />
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
                  type="tel"
                  placeholder={t("phonePlaceholder")}
                  value={phoneInput}
                  onChange={(e) => {
                    setPhoneInput(e.target.value);
                    setError(null);
                  }}
                  onKeyDown={handleKeyDown}
                  className="flex-1"
                />
                <Button
                  onClick={handleAddPhone}
                  size="sm"
                  className="gap-2 bg-blue-500 hover:bg-blue-600 text-white"
                >
                  <PlusCircle className="h-4 w-4" />
                  {t("addPhone")}
                </Button>
              </div>
              {error && <p className="text-sm text-destructive">{error}</p>}
            </div>

            {allowedPhones.length > 0 && (
              <div className="flex flex-col gap-2 mt-2">
                {allowedPhones.map((phone) => (
                  <div
                    key={phone}
                    className="flex items-center justify-between px-3 py-2 bg-muted rounded-md"
                  >
                    <span className="text-sm">{phone}</span>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => handleRemovePhone(phone)}
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
