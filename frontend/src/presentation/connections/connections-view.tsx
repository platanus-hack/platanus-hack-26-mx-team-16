"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Cable, Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { useState } from "react";

import type {
  ConnectionAccount,
  ConnectionProvider,
} from "@/src/domain/entities/connection";
import { isErrorFeedback } from "@/src/domain/errors/error-feeback";
import { EmptyState } from "@/src/presentation/components/common/empty-state";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import { Card } from "@/src/presentation/components/ui/card";
import { FullPageSpinner } from "@/src/presentation/components/ui/spinner";

import { ConnectionFormDialog } from "./connection-form-dialog";
import { ConnectionProviderPickerDialog } from "./connection-provider-picker-dialog";
import { PROVIDER_ICON } from "./connection-providers";
import { CONNECTIONS_QUERY_KEY, connectionRepo } from "./connection-repo";

export function ConnectionsView() {
  const t = useTranslations("ConnectionsOrg");
  const queryClient = useQueryClient();
  const [pickerOpen, setPickerOpen] = useState(false);
  const [formProvider, setFormProvider] = useState<ConnectionProvider | null>(
    null
  );

  const { data: accounts = [], isLoading } = useQuery({
    queryKey: CONNECTIONS_QUERY_KEY,
    queryFn: async () => {
      const res = await connectionRepo.list();
      if (isErrorFeedback(res)) throw new Error(res.errors[0]?.message);
      return res.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (uuid: string) => {
      const res = await connectionRepo.remove(uuid);
      if (isErrorFeedback(res)) throw new Error(res.errors[0]?.message);
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: CONNECTIONS_QUERY_KEY }),
  });

  if (isLoading) return <FullPageSpinner />;

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <h2 className="text-3xl font-bold tracking-tight">{t("title")}</h2>
          <p className="text-sm text-muted-foreground">{t("subtitle")}</p>
        </div>
        <Button className="gap-2" onClick={() => setPickerOpen(true)}>
          <Plus className="h-4 w-4" />
          {t("connect")}
        </Button>
      </div>

      {accounts.length === 0 ? (
        <Card className="px-6 py-12">
          <EmptyState
            icon={Cable}
            title={t("emptyTitle")}
            description={t("emptyDescription")}
            actionLabel={t("connect")}
            onAction={() => setPickerOpen(true)}
          />
        </Card>
      ) : (
        <div className="flex flex-col gap-2">
          {accounts.map((account) => (
            <AccountRow
              key={account.uuid}
              account={account}
              onDelete={() => deleteMutation.mutate(account.uuid)}
            />
          ))}
        </div>
      )}

      <ConnectionProviderPickerDialog
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        onSelect={(provider) => {
          setPickerOpen(false);
          setFormProvider(provider);
        }}
      />
      <ConnectionFormDialog
        provider={formProvider}
        open={formProvider !== null}
        onOpenChange={(o) => {
          if (!o) setFormProvider(null);
        }}
      />
    </div>
  );
}

function AccountRow({
  account,
  onDelete,
}: {
  account: ConnectionAccount;
  onDelete: () => void;
}) {
  const t = useTranslations("ConnectionsOrg");
  const Icon = PROVIDER_ICON[account.provider] ?? Cable;
  const providerLabel = t.has(`provider.${account.provider}`)
    ? t(`provider.${account.provider}`)
    : account.provider;
  return (
    <Card className="flex flex-row items-center gap-4 px-5 py-4">
      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <div className="flex items-center gap-2">
          <p className="truncate font-medium">{account.displayName}</p>
          <Badge variant="outline" className="text-[10px] uppercase">
            {providerLabel}
          </Badge>
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          {account.capabilities.map((cap) => (
            <Badge key={cap} variant="secondary" className="text-[10px]">
              {t.has(`capability.${cap}`) ? t(`capability.${cap}`) : cap}
            </Badge>
          ))}
          <span className="text-xs text-muted-foreground">
            {t.has(`status.${account.status}`)
              ? t(`status.${account.status}`)
              : account.status}
          </span>
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        className="gap-2 text-destructive"
        onClick={onDelete}
      >
        <Trash2 className="h-4 w-4" />
        {t("delete")}
      </Button>
    </Card>
  );
}
