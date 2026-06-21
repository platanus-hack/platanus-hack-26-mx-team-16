"use client";

import { BadgeCheck, ShieldAlert } from "lucide-react";
import { useTranslations } from "next-intl";
import { useEffect, useState } from "react";

import { useProfileStore } from "@/src/application/stores/profile-store";
import { LocaleSwitcher } from "@/src/presentation/components/locale-switcher";
import { ActionButton } from "@/src/presentation/components/ui/action-button";
import { Input } from "@/src/presentation/components/ui/input";
import { Label } from "@/src/presentation/components/ui/label";

function GoogleGlyph({ className }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 48 48" role="img" aria-hidden>
      <path
        fill="#4285F4"
        d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
      />
      <path
        fill="#FF3D00"
        d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238C29.211 35.091 26.715 36 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
      />
      <path
        fill="#1976D2"
        d="M43.611 20.083H42V20H24v8h11.303c-.792 2.237-2.231 4.166-4.087 5.571l6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"
      />
    </svg>
  );
}

export function ProfileView() {
  const t = useTranslations("Profile");
  const profile = useProfileStore((s) => s.profile);
  const isLoading = useProfileStore((s) => s.isLoading);
  const isSaving = useProfileStore((s) => s.isSaving);
  const isChangingPassword = useProfileStore((s) => s.isChangingPassword);
  const saveError = useProfileStore((s) => s.saveError);
  const saveSuccess = useProfileStore((s) => s.saveSuccess);
  const passwordError = useProfileStore((s) => s.passwordError);
  const passwordSuccess = useProfileStore((s) => s.passwordSuccess);
  const loadProfile = useProfileStore((s) => s.loadProfile);
  const updateProfile = useProfileStore((s) => s.updateProfile);
  const updatePassword = useProfileStore((s) => s.updatePassword);
  const clearFeedback = useProfileStore((s) => s.clearFeedback);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [confirmPasswordError, setConfirmPasswordError] = useState("");

  useEffect(() => {
    loadProfile();
  }, [loadProfile]);

  useEffect(() => {
    if (profile) {
      setFirstName(profile.firstName ?? "");
      setLastName(profile.lastName ?? "");
    }
  }, [profile]);

  useEffect(() => {
    if (passwordSuccess) {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setConfirmPasswordError("");
    }
  }, [passwordSuccess]);

  const handleProfileSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    clearFeedback();
    updateProfile({ firstName, lastName });
  };

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    clearFeedback();

    if (newPassword !== confirmPassword) {
      setConfirmPasswordError(t("passwordsDontMatch"));
      return;
    }
    setConfirmPasswordError("");
    updatePassword({ currentPassword, newPassword });
  };

  const email = profile?.emailAddress?.email ?? "";
  const isVerified = profile?.emailAddress?.isVerified ?? false;
  const hasPassword = profile?.hasPassword ?? true;

  const displayName =
    [profile?.firstName, profile?.lastName].filter(Boolean).join(" ") || email;
  const initials =
    (
      (profile?.firstName?.[0] ?? "") + (profile?.lastName?.[0] ?? "")
    ).toUpperCase() ||
    email[0]?.toUpperCase() ||
    "U";

  if (isLoading) {
    return (
      <div className="flex min-h-[400px] items-center justify-center">
        <div className="text-muted-foreground">{t("loading")}</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1.5">
        <h1 className="text-3xl font-bold tracking-tight text-foreground">
          {t("title")}
        </h1>
        <p className="text-[15px] text-muted-foreground">{t("description")}</p>
      </header>

      {/* Account card — identity + editable name fields */}
      <form
        onSubmit={handleProfileSubmit}
        className="flex flex-col gap-6 rounded-2xl border border-outline-variant bg-card p-7"
      >
        <div className="flex items-center gap-4">
          <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary-container text-lg font-semibold text-on-primary-container">
            {initials}
          </div>
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-lg font-semibold text-foreground">
              {displayName}
            </span>
            <span className="truncate text-sm text-muted-foreground">
              {email}
            </span>
          </div>
          {isVerified && (
            <span className="ml-auto inline-flex shrink-0 items-center gap-1.5 rounded-full bg-secondary-container px-3 py-1 text-xs font-medium text-on-secondary-container">
              <BadgeCheck className="size-3.5 text-primary" />
              {t("emailVerified")}
            </span>
          )}
        </div>

        <div className="h-px w-full bg-outline-variant" />

        <div className="grid gap-5 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="firstName">{t("firstName")}</Label>
            <Input
              id="firstName"
              value={firstName}
              onValueChange={setFirstName}
              placeholder={t("firstNamePlaceholder")}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <Label htmlFor="lastName">{t("lastName")}</Label>
            <Input
              id="lastName"
              value={lastName}
              onValueChange={setLastName}
              placeholder={t("lastNamePlaceholder")}
            />
          </div>
          <div className="flex flex-col gap-1.5 sm:col-span-2">
            <Label htmlFor="email">{t("email")}</Label>
            <Input
              id="email"
              value={email}
              readOnly
              className="bg-surface-container text-muted-foreground"
            />
          </div>
        </div>

        {saveError && <p className="text-sm text-destructive">{saveError}</p>}
        {saveSuccess && (
          <p className="text-sm text-success-deep">{t("saveSuccess")}</p>
        )}

        <div>
          <ActionButton type="submit" loading={isSaving}>
            {isSaving ? t("saving") : t("save")}
          </ActionButton>
        </div>
      </form>

      {/* Security + Language */}
      <div className="grid gap-6 lg:grid-cols-2">
        <section className="flex flex-col gap-4 rounded-2xl border border-outline-variant bg-card p-6">
          <div className="flex flex-col gap-0.5">
            <h2 className="text-base font-semibold text-foreground">
              {hasPassword ? t("security") : t("accessMethod")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {hasPassword
                ? t("securityDescription")
                : t("googleConnectedDescription")}
            </p>
          </div>

          {hasPassword ? (
            <form
              onSubmit={handlePasswordSubmit}
              className="flex flex-col gap-4"
            >
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="currentPassword">{t("currentPassword")}</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  value={currentPassword}
                  onValueChange={setCurrentPassword}
                  placeholder={t("currentPasswordPlaceholder")}
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="newPassword">{t("newPassword")}</Label>
                <Input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onValueChange={setNewPassword}
                  placeholder={t("newPasswordPlaceholder")}
                  required
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <Label htmlFor="confirmPassword">{t("confirmPassword")}</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onValueChange={setConfirmPassword}
                  placeholder={t("confirmPasswordPlaceholder")}
                  required
                />
                {confirmPasswordError && (
                  <p className="text-xs text-destructive">
                    {confirmPasswordError}
                  </p>
                )}
              </div>

              {passwordError && (
                <p className="text-sm text-destructive">{passwordError}</p>
              )}
              {passwordSuccess && (
                <p className="text-sm text-success-deep">
                  {t("passwordSuccess")}
                </p>
              )}

              <div>
                <ActionButton type="submit" loading={isChangingPassword}>
                  {isChangingPassword ? t("changing") : t("changePassword")}
                </ActionButton>
              </div>
            </form>
          ) : (
            <div className="flex items-center gap-3 rounded-xl border border-outline-variant bg-surface-container-low px-4 py-4">
              <GoogleGlyph className="size-5 shrink-0" />
              <div className="flex min-w-0 flex-col">
                <span className="text-sm font-medium text-foreground">
                  {t("googleConnected")}
                </span>
                <span className="truncate text-sm text-muted-foreground">
                  {email}
                </span>
              </div>
            </div>
          )}
        </section>

        <section className="flex flex-col gap-4 rounded-2xl border border-outline-variant bg-card p-6">
          <div className="flex flex-col gap-0.5">
            <h2 className="text-base font-semibold text-foreground">
              {t("language")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("languageDescription")}
            </p>
          </div>
          <LocaleSwitcher />
        </section>
      </div>

      {/* Danger zone — account deletion (not yet wired) */}
      <section className="flex flex-col gap-4 rounded-2xl border border-destructive/40 bg-card p-6">
        <div className="flex items-start gap-3">
          <ShieldAlert className="mt-0.5 size-5 shrink-0 text-destructive" />
          <div className="flex flex-col gap-0.5">
            <h2 className="text-base font-semibold text-destructive">
              {t("deleteAccount")}
            </h2>
            <p className="text-sm text-muted-foreground">
              {t("deleteAccountDescription")}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <ActionButton type="button" variant="destructive" disabled>
            {t("deleteAccount")}
          </ActionButton>
          <span className="text-xs text-outline">{t("comingSoon")}</span>
        </div>
      </section>
    </div>
  );
}
