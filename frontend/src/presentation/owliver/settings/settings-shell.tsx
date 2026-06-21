/**
 * SettingsShell — the chrome for Owliver's account/settings cluster (design
 * `Page · Ajustes *`). Mirrors the design's structure: sticky `TopNav`, a Body
 * that lays out the `SettingsSidebar` beside the page panel, then the `Footer`.
 * Replaces the boilerplate `AppShell` (shadcn sidebar + breadcrumbs) for these
 * signed-in surfaces so they wear the same light Owliver shell as the rest.
 */
import { Footer } from "@/src/presentation/owliver/chrome/footer";
import { TopNav } from "@/src/presentation/owliver/chrome/top-nav";
import { SettingsSidebar } from "@/src/presentation/owliver/settings/settings-sidebar";

export type SettingsShellProps = {
  /** Pathname of the active settings page (drives the sidebar highlight). */
  activePath: string;
  children: React.ReactNode;
};

export function SettingsShell({ activePath, children }: SettingsShellProps) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TopNav showWatchlist hasSession />
      <main className="flex-1">
        <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-4 py-10 md:flex-row md:px-6 md:py-12">
          <SettingsSidebar
            activePath={activePath}
            className="md:sticky md:top-24 md:self-start"
          />
          <div className="min-w-0 flex-1">{children}</div>
        </div>
      </main>
      <Footer />
    </div>
  );
}
