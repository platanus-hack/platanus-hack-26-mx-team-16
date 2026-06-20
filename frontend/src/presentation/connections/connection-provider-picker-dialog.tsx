"use client";

import { useTranslations } from "next-intl";

import type { ConnectionProvider } from "@/src/domain/entities/connection";
import { Card } from "@/src/presentation/components/ui/card";
import {
  Dialog,
  DialogBackdrop,
  DialogDescription,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { ComingSoonTile } from "@/src/presentation/workflows/connections/coming-soon-tile";

import { PROVIDER_OPTIONS } from "./connection-providers";

/**
 * Step one of the "add integration" flow: a grid of every possible integration
 * type. Enabled tiles are buttons that hand the chosen provider back to the
 * caller (which then opens the per-type creation modal); disabled ones render
 * as non-interactive "coming soon" tiles.
 */
export function ConnectionProviderPickerDialog({
  open,
  onOpenChange,
  onSelect,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSelect: (provider: ConnectionProvider) => void;
}) {
  const t = useTranslations("ConnectionsOrg");

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="w-full max-w-xl p-6">
        <DialogTitle className="mb-1 text-lg font-semibold">
          {t("picker.title")}
        </DialogTitle>
        <DialogDescription className="mb-5 text-sm text-muted-foreground">
          {t("picker.description")}
        </DialogDescription>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {PROVIDER_OPTIONS.map(({ provider, icon: Icon, enabled }) => {
            const label = t(`provider.${provider}`);
            const description = t(`providerDescription.${provider}`);

            if (!enabled) {
              return (
                <ComingSoonTile
                  key={provider}
                  icon={Icon}
                  title={label}
                  description={description}
                  comingSoonLabel={t("comingSoon")}
                />
              );
            }

            return (
              <button
                key={provider}
                type="button"
                onClick={() => onSelect(provider)}
                className="text-left transition focus-visible:outline-none"
              >
                <Card className="flex h-full flex-col gap-3 border border-border p-5 transition hover:border-primary/40 hover:shadow-sm">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-sm font-semibold">{label}</h3>
                  <p className="flex-1 text-sm text-muted-foreground">
                    {description}
                  </p>
                </Card>
              </button>
            );
          })}
        </div>
      </DialogPopup>
    </Dialog>
  );
}
