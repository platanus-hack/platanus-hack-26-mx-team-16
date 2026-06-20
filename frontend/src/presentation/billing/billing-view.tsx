"use client";

import { Info, Plus } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import {
  useBillingQuery,
  useBuyCreditsMutation,
} from "@/src/application/hooks/queries/billing";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Card, CardContent } from "@/src/presentation/components/ui/card";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";

export function BillingView() {
  const t = useTranslations("Billing");
  const locale = useLocale();
  const { data, isLoading, error } = useBillingQuery();
  const buyCredits = useBuyCreditsMutation();

  const formatDate = (dateString: string) => {
    if (!dateString) return "";
    const date = new Date(dateString);
    return date.toLocaleDateString(locale === "es" ? "es-ES" : "en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    });
  };

  if (isLoading) return <FullPageSpinner />;

  if (error) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-destructive">{error.message}</div>
      </div>
    );
  }

  const { creditBalance, invoices } = data ?? {
    creditBalance: null,
    invoices: [],
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight mb-2">{t("title")}</h2>
        <p className="text-muted-foreground text-sm max-w-3xl">
          {t("description")}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[2fr_1fr] gap-4">
        <Card className="bg-card">
          <CardContent className="pt-6">
            <div className="text-sm text-muted-foreground mb-2">
              {t("creditBalance")}
            </div>
            <div className="text-6xl font-bold mb-1">
              {creditBalance?.credits || 0}
            </div>
            <div className="text-sm text-muted-foreground mb-1">
              {t("creditsRemaining")}
            </div>
            <div className="text-xs text-muted-foreground">
              {t("expiresOn", {
                date: formatDate(creditBalance?.expiresAt || ""),
              })}
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card">
          <CardContent className="pt-6">
            <h3 className="font-semibold mb-2">{t("buyCreditsTitle")}</h3>
            <p className="text-sm text-muted-foreground mb-4">
              {t("buyCreditsDescription")}
            </p>
            <ActionButton
              onClick={() => buyCredits.mutate(100)}
              loading={buyCredits.isPending}
              icon={<Plus className="h-4 w-4" />}
              className="gap-2"
            >
              {t("buyCreditsCta")}
            </ActionButton>
          </CardContent>
        </Card>
      </div>

      <Card className="bg-card border-blue-500/20">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <Info className="h-5 w-5 text-blue-500 mt-0.5 shrink-0" />
            <div className="flex-1">
              <p className="text-sm">
                <span className="font-medium">{t("customNeedsText")}</span>
              </p>
              <div className="flex gap-4 mt-2">
                <a href="#" className="text-sm text-blue-500 hover:underline">
                  {t("viewPricing")}
                </a>
                <a href="#" className="text-sm text-blue-500 hover:underline">
                  {t("contactSales")}
                </a>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div>
        <h3 className="text-lg font-semibold mb-4">{t("invoicesHistory")}</h3>
        <Card className="bg-card">
          <CardContent className="pt-6 pb-6">
            {invoices.length === 0 ? (
              <div className="text-center py-8">
                <p className="text-muted-foreground mb-2">{t("noInvoices")}</p>
                <p className="text-sm text-muted-foreground">
                  {t("noInvoicesHint")}
                </p>
              </div>
            ) : (
              <div className="flex flex-col gap-2">
                {invoices.map((invoice) => (
                  <div
                    key={invoice.uuid}
                    className="flex items-center justify-between py-2 border-b last:border-0"
                  >
                    <span className="text-sm">
                      {t("invoiceLine", {
                        date: formatDate(invoice.date),
                        credits: invoice.credits,
                      })}
                    </span>
                    <span className="text-sm font-medium">
                      ${invoice.amount.toFixed(2)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
