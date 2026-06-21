/**
 * Owliver protected chrome (§F3/§F11). A NESTED group inside `(protected)` so it
 * inherits the parent layout's session gate (cookie refresh → redirect /login)
 * WITHOUT the boilerplate `AppShell` sidebar. Owliver's signed-in surfaces
 * (watchlist + monitoring) wear the same light TopNav + Footer chrome as the
 * public viral surfaces, with the Watchlist link surfaced (a session exists).
 */
import { Footer } from "@/src/presentation/owliver/chrome/footer";
import { TopNav } from "@/src/presentation/owliver/chrome/top-nav";

export default function OwliverProtectedLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TopNav showWatchlist />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
