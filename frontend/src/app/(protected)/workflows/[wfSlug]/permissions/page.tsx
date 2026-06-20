"use client";

import {
  Check,
  Globe,
  Loader2,
  Lock,
  Search,
  Trash2,
  UserPlus,
  Users,
} from "lucide-react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";
import {
  useAddMemberMutation,
  useAssignableUsersQuery,
  useRemoveMemberMutation,
  useUpdateAccessTypeMutation,
  useUpdateMemberRoleMutation,
  useWorkflowPermissionsQuery,
} from "@/src/application/hooks/queries/workflow-permissions";
import { useWorkflowQuery } from "@/src/application/hooks/queries/workflows";
import { cn } from "@/src/application/lib/utils";
import type {
  AssignableUser,
  WorkflowAccessType,
  WorkflowMember,
  WorkflowMemberRole,
} from "@/src/domain/entities/workflow-permission";
import { PageContent } from "@/src/presentation/components/common/page-content";
import {
  Avatar,
  AvatarFallback,
  AvatarImage,
} from "@/src/presentation/components/ui/avatar";
import { Badge } from "@/src/presentation/components/ui/badge";
import { Button } from "@/src/presentation/components/ui/button";
import {
  Dialog,
  DialogBackdrop,
  DialogClose,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogPopup,
  DialogTitle,
} from "@/src/presentation/components/ui/dialog";
import { Input } from "@/src/presentation/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/src/presentation/components/ui/select";
import { Skeleton } from "@/src/presentation/components/ui/skeleton";
import { WorkflowAppShell } from "@/src/presentation/workflows/shared/workflow-app-shell";

const CARD = "rounded-xl bg-card ring-1 ring-foreground/10 shadow-xs";
const ROLES: WorkflowMemberRole[] = ["admin", "member", "viewer"];

function getInitials(name: string, email?: string | null): string {
  const source = name?.trim() || email?.trim() || "";
  if (!source) return "?";
  const parts = source.split(/\s+/).filter(Boolean);
  const initials = parts
    .slice(0, 2)
    .map((p) => p[0])
    .join("");
  return (initials || source[0]).toUpperCase();
}

export default function WorkflowPermissionsPage() {
  const tNav = useTranslations("Nav");
  const t = useTranslations("WorkflowPermissions");
  const tc = useTranslations("WorkflowConfig");
  const params = useParams();
  const wfSlug = params.wfSlug as string;

  const { data: workflow } = useWorkflowQuery(wfSlug);
  const permissionsQuery = useWorkflowPermissionsQuery(wfSlug);
  const accessTypeMutation = useUpdateAccessTypeMutation(wfSlug);
  const roleMutation = useUpdateMemberRoleMutation(wfSlug);
  const removeMutation = useRemoveMemberMutation(wfSlug);

  const [searchQuery, setSearchQuery] = useState("");
  const [isAddOpen, setIsAddOpen] = useState(false);

  const workflowName = workflow?.name || tNav("workflows");
  const permissions = permissionsQuery.data;
  const accessType = permissions?.accessType ?? "private";
  const isPrivate = accessType === "private";

  const breadcrumbItems = [
    { label: tNav("workflows"), href: "/workflows" },
    { label: workflowName, href: `/workflows/${wfSlug}/cases` },
    { label: t("title") },
  ];

  const members = permissions?.members ?? [];
  const filteredMembers = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return members;
    return members.filter(
      (m) =>
        m.name.toLowerCase().includes(q) ||
        (m.email ?? "").toLowerCase().includes(q)
    );
  }, [members, searchQuery]);

  return (
    <WorkflowAppShell breadcrumbItems={breadcrumbItems}>
      <PageContent>
        <PageContent.Header
          icon={Lock}
          title={t("title")}
          subtitle={tc("subtitle")}
          actions={
            isPrivate && permissions ? (
              <Button onClick={() => setIsAddOpen(true)}>
                <UserPlus />
                {t("addMembers")}
              </Button>
            ) : undefined
          }
        />
        <PageContent.Body className="gap-8">
          {permissionsQuery.isLoading ? (
            <PermissionsSkeleton />
          ) : permissionsQuery.isError ? (
            <ErrorState
              title={t("error.title")}
              description={t("error.description")}
              retryLabel={t("error.retry")}
              onRetry={() => permissionsQuery.refetch()}
            />
          ) : (
            <>
              {/* Access mode */}
              <section className="flex flex-col gap-4">
                <div className="flex items-center justify-between gap-3">
                  <div className="flex flex-col gap-0.5">
                    <h2 className="text-base font-semibold">
                      {t("accessTitle")}
                    </h2>
                    <p className="text-sm text-muted-foreground">
                      {t("accessDescription")}
                    </p>
                  </div>
                  {accessTypeMutation.isPending && (
                    <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <Loader2 className="size-3.5 animate-spin" />
                      {t("saving")}
                    </span>
                  )}
                </div>
                <AccessModeToggle
                  value={accessType}
                  disabled={accessTypeMutation.isPending}
                  onChange={(value) => accessTypeMutation.mutate(value)}
                  labels={{
                    organization: t("accessType.organization"),
                    organizationDescription: t(
                      "accessType.organizationDescription"
                    ),
                    private: t("accessType.private"),
                    privateDescription: t("accessType.privateDescription"),
                  }}
                />
              </section>

              {/* Members (private) or org notice */}
              {isPrivate ? (
                <section className="flex flex-col gap-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="flex items-baseline gap-2">
                      <h2 className="text-base font-semibold">
                        {t("membersTitle")}
                      </h2>
                      <span className="text-sm text-muted-foreground tabular-nums">
                        {t("membersCount", { count: members.length })}
                      </span>
                    </div>
                    {members.length > 0 && (
                      <div className="relative w-full sm:w-[260px]">
                        <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                        <Input
                          type="search"
                          placeholder={t("searchPlaceholder")}
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          className="pl-9"
                        />
                      </div>
                    )}
                  </div>

                  <p className="text-xs text-muted-foreground">
                    {t("implicitAccessNote")}
                  </p>

                  {members.length === 0 ? (
                    <EmptyState
                      title={t("privateEmpty.title")}
                      description={t("privateEmpty.description")}
                      actionLabel={t("addMembers")}
                      onAction={() => setIsAddOpen(true)}
                    />
                  ) : filteredMembers.length === 0 ? (
                    <div className={cn(CARD, "px-6 py-10 text-center")}>
                      <p className="text-sm text-muted-foreground">
                        {t("noResults")}
                      </p>
                    </div>
                  ) : (
                    <ul
                      className={cn(
                        CARD,
                        "divide-y divide-border overflow-hidden"
                      )}
                    >
                      {filteredMembers.map((member) => (
                        <MemberRow
                          key={member.userId}
                          member={member}
                          ownerLabel={t("badge.owner")}
                          removeLabel={t("removeMember")}
                          roleLabels={{
                            admin: t("role.admin"),
                            member: t("role.member"),
                            viewer: t("role.viewer"),
                          }}
                          isUpdatingRole={
                            roleMutation.isPending &&
                            roleMutation.variables?.userId === member.userId
                          }
                          isRemoving={
                            removeMutation.isPending &&
                            removeMutation.variables === member.userId
                          }
                          onRoleChange={(role) =>
                            roleMutation.mutate({ userId: member.userId, role })
                          }
                          onRemove={() => removeMutation.mutate(member.userId)}
                        />
                      ))}
                    </ul>
                  )}
                </section>
              ) : (
                <OrgAccessNotice
                  title={t("orgAccess.title")}
                  description={t("orgAccess.description")}
                  actionLabel={t("orgAccess.switchToPrivate")}
                  isPending={accessTypeMutation.isPending}
                  onSwitch={() => accessTypeMutation.mutate("private")}
                />
              )}
            </>
          )}
        </PageContent.Body>

        <AddMemberDialog
          open={isAddOpen}
          onOpenChange={setIsAddOpen}
          workflowUuid={wfSlug}
        />
      </PageContent>
    </WorkflowAppShell>
  );
}

// ---------------------------------------------------------------------------

function AccessModeToggle({
  value,
  onChange,
  disabled,
  labels,
}: {
  value: WorkflowAccessType;
  onChange: (value: WorkflowAccessType) => void;
  disabled?: boolean;
  labels: {
    organization: string;
    organizationDescription: string;
    private: string;
    privateDescription: string;
  };
}) {
  const options = [
    {
      value: "organization" as const,
      icon: Globe,
      label: labels.organization,
      description: labels.organizationDescription,
    },
    {
      value: "private" as const,
      icon: Lock,
      label: labels.private,
      description: labels.privateDescription,
    },
  ];

  return (
    <div role="radiogroup" className="grid gap-3 sm:grid-cols-2">
      {options.map((option) => {
        const active = value === option.value;
        const Icon = option.icon;
        return (
          <button
            key={option.value}
            type="button"
            role="radio"
            aria-checked={active}
            disabled={disabled}
            onClick={() => !active && onChange(option.value)}
            className={cn(
              "flex items-start gap-3 rounded-xl p-4 text-left outline-none transition-colors",
              "focus-visible:ring-[3px] focus-visible:ring-ring/50",
              "disabled:pointer-events-none disabled:opacity-60",
              active
                ? "bg-primary/5 ring-1 ring-primary/40"
                : "bg-card ring-1 ring-foreground/10 shadow-xs hover:bg-muted/40"
            )}
          >
            <span
              className={cn(
                "flex size-9 shrink-0 items-center justify-center rounded-md transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted text-muted-foreground"
              )}
            >
              <Icon className="size-4" />
            </span>
            <span className="flex min-w-0 flex-col gap-0.5">
              <span className="flex items-center gap-1.5 text-sm font-medium">
                {option.label}
                {active && <Check className="size-3.5 text-primary" />}
              </span>
              <span className="text-xs text-muted-foreground">
                {option.description}
              </span>
            </span>
          </button>
        );
      })}
    </div>
  );
}

function MemberRow({
  member,
  ownerLabel,
  removeLabel,
  roleLabels,
  isUpdatingRole,
  isRemoving,
  onRoleChange,
  onRemove,
}: {
  member: WorkflowMember;
  ownerLabel: string;
  removeLabel: string;
  roleLabels: Record<WorkflowMemberRole, string>;
  isUpdatingRole: boolean;
  isRemoving: boolean;
  onRoleChange: (role: WorkflowMemberRole) => void;
  onRemove: () => void;
}) {
  return (
    <li
      className={cn(
        "flex items-center gap-3 px-4 py-3 transition-colors hover:bg-muted/30",
        isRemoving && "opacity-50"
      )}
    >
      <Avatar size="default">
        {member.photo ? (
          <AvatarImage src={member.photo} alt={member.name} />
        ) : null}
        <AvatarFallback>
          {getInitials(member.name, member.email)}
        </AvatarFallback>
      </Avatar>
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium">{member.name}</p>
          {member.isOwner && (
            <Badge variant="secondary" className="shrink-0">
              {ownerLabel}
            </Badge>
          )}
        </div>
        {member.email && (
          <p className="truncate text-xs text-muted-foreground">
            {member.email}
          </p>
        )}
      </div>
      <Select
        value={member.role}
        onValueChange={(value) =>
          value && onRoleChange(value as WorkflowMemberRole)
        }
        disabled={isUpdatingRole || isRemoving}
      >
        <SelectTrigger size="sm" className="w-[120px]">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {ROLES.map((role) => (
            <SelectItem key={role} value={role}>
              {roleLabels[role]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        variant="ghost"
        size="icon-sm"
        aria-label={removeLabel}
        title={removeLabel}
        disabled={isRemoving}
        onClick={onRemove}
        className="text-muted-foreground hover:text-destructive"
      >
        {isRemoving ? <Loader2 className="animate-spin" /> : <Trash2 />}
      </Button>
    </li>
  );
}

function OrgAccessNotice({
  title,
  description,
  actionLabel,
  isPending,
  onSwitch,
}: {
  title: string;
  description: string;
  actionLabel: string;
  isPending: boolean;
  onSwitch: () => void;
}) {
  return (
    <div
      className={cn(
        CARD,
        "flex flex-col gap-4 p-6 sm:flex-row sm:items-center"
      )}
    >
      <span className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Globe className="size-5" />
      </span>
      <div className="flex min-w-0 flex-1 flex-col gap-0.5">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <Button
        variant="outline"
        disabled={isPending}
        onClick={onSwitch}
        className="shrink-0 self-start sm:self-auto"
      >
        <Lock />
        {actionLabel}
      </Button>
    </div>
  );
}

function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
}: {
  title: string;
  description: string;
  actionLabel: string;
  onAction: () => void;
}) {
  return (
    <div
      className={cn(
        CARD,
        "flex flex-col items-center gap-3 px-6 py-12 text-center"
      )}
    >
      <span className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Users className="size-5" />
      </span>
      <div className="flex max-w-sm flex-col gap-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <Button onClick={onAction} className="mt-1">
        <UserPlus />
        {actionLabel}
      </Button>
    </div>
  );
}

function ErrorState({
  title,
  description,
  retryLabel,
  onRetry,
}: {
  title: string;
  description: string;
  retryLabel: string;
  onRetry: () => void;
}) {
  return (
    <div
      className={cn(
        CARD,
        "flex flex-col items-center gap-3 px-6 py-12 text-center"
      )}
    >
      <div className="flex max-w-sm flex-col gap-1">
        <p className="text-sm font-medium">{title}</p>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <Button variant="outline" onClick={onRetry}>
        {retryLabel}
      </Button>
    </div>
  );
}

function PermissionsSkeleton() {
  return (
    <>
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <Skeleton className="h-5 w-40" />
          <Skeleton className="h-4 w-64" />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-[76px] rounded-xl" />
          <Skeleton className="h-[76px] rounded-xl" />
        </div>
      </section>
      <section className="flex flex-col gap-4">
        <Skeleton className="h-5 w-32" />
        <div className={cn(CARD, "divide-y divide-border overflow-hidden")}>
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex items-center gap-3 px-4 py-3">
              <Skeleton className="size-8 rounded-full" />
              <div className="flex flex-1 flex-col gap-1.5">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-48" />
              </div>
              <Skeleton className="h-8 w-[120px] rounded-md" />
            </div>
          ))}
        </div>
      </section>
    </>
  );
}

// ---------------------------------------------------------------------------

function AddMemberDialog({
  open,
  onOpenChange,
  workflowUuid,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workflowUuid: string;
}) {
  const t = useTranslations("WorkflowPermissions");
  const assignableQuery = useAssignableUsersQuery(workflowUuid, open);
  const addMutation = useAddMemberMutation(workflowUuid);

  const [search, setSearch] = useState("");
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [role, setRole] = useState<WorkflowMemberRole>("member");

  const users = assignableQuery.data ?? [];
  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter(
      (u) =>
        u.name.toLowerCase().includes(q) ||
        (u.email ?? "").toLowerCase().includes(q)
    );
  }, [users, search]);

  function reset() {
    setSearch("");
    setSelectedUserId(null);
    setRole("member");
    addMutation.reset();
  }

  function handleOpenChange(next: boolean) {
    if (!next) reset();
    onOpenChange(next);
  }

  function handleAdd() {
    if (!selectedUserId) return;
    addMutation.mutate(
      { userId: selectedUserId, role },
      { onSuccess: () => handleOpenChange(false) }
    );
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogBackdrop />
      <DialogPopup className="max-w-lg p-6">
        <DialogHeader>
          <DialogTitle>{t("dialog.title")}</DialogTitle>
          <DialogDescription>{t("dialog.description")}</DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder={t("dialog.searchPlaceholder")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-9"
              autoFocus
            />
          </div>

          <div className="max-h-64 overflow-y-auto rounded-lg ring-1 ring-foreground/10">
            {assignableQuery.isLoading ? (
              <div className="flex flex-col">
                {[0, 1, 2].map((i) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-2.5">
                    <Skeleton className="size-8 rounded-full" />
                    <div className="flex flex-1 flex-col gap-1.5">
                      <Skeleton className="h-3.5 w-28" />
                      <Skeleton className="h-3 w-40" />
                    </div>
                  </div>
                ))}
              </div>
            ) : filtered.length === 0 ? (
              <p className="px-3 py-8 text-center text-sm text-muted-foreground">
                {users.length === 0 ? t("dialog.allAdded") : t("dialog.empty")}
              </p>
            ) : (
              <ul className="divide-y divide-border">
                {filtered.map((user) => (
                  <AssignableUserRow
                    key={user.userId}
                    user={user}
                    selected={selectedUserId === user.userId}
                    onSelect={() => setSelectedUserId(user.userId)}
                  />
                ))}
              </ul>
            )}
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-xs font-medium text-muted-foreground">
              {t("dialog.roleLabel")}
            </label>
            <Select
              value={role}
              onValueChange={(value) =>
                value && setRole(value as WorkflowMemberRole)
              }
            >
              <SelectTrigger className="w-full">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((r) => (
                  <SelectItem key={r} value={r}>
                    {t(`role.${r}`)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {addMutation.isError && (
            <p className="text-sm text-destructive">
              {(addMutation.error as Error)?.message}
            </p>
          )}
        </div>

        <DialogFooter className="gap-2">
          <DialogClose
            render={<Button variant="outline">{t("dialog.cancel")}</Button>}
          />
          <Button
            disabled={!selectedUserId || addMutation.isPending}
            onClick={handleAdd}
          >
            {addMutation.isPending && <Loader2 className="animate-spin" />}
            {addMutation.isPending ? t("dialog.adding") : t("dialog.add")}
          </Button>
        </DialogFooter>
      </DialogPopup>
    </Dialog>
  );
}

function AssignableUserRow({
  user,
  selected,
  onSelect,
}: {
  user: AssignableUser;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onSelect}
        aria-pressed={selected}
        className={cn(
          "flex w-full items-center gap-3 px-3 py-2.5 text-left outline-none transition-colors",
          "focus-visible:bg-muted/60",
          selected ? "bg-primary/5" : "hover:bg-muted/40"
        )}
      >
        <Avatar size="default">
          {user.photo ? <AvatarImage src={user.photo} alt={user.name} /> : null}
          <AvatarFallback>{getInitials(user.name, user.email)}</AvatarFallback>
        </Avatar>
        <div className="flex min-w-0 flex-1 flex-col">
          <p className="truncate text-sm font-medium">{user.name}</p>
          {user.email && (
            <p className="truncate text-xs text-muted-foreground">
              {user.email}
            </p>
          )}
        </div>
        <span
          className={cn(
            "flex size-5 shrink-0 items-center justify-center rounded-full transition-colors",
            selected
              ? "bg-primary text-primary-foreground"
              : "ring-1 ring-inset ring-border"
          )}
        >
          {selected && <Check className="size-3" />}
        </span>
      </button>
    </li>
  );
}
