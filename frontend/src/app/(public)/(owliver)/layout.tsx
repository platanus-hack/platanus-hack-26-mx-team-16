/**
 * Owliver public chrome (§F3) — the layout for every anonymous viral surface:
 * Hall of Shame (`/`), scan form, theater, report, `/r/[token]`, sites. It is a
 * NESTED group inside `(public)` so it does NOT wrap the auth pages (login,
 * register, reset) which keep their own centered `AuthContainer`.
 *
 * Chrome: a sticky `TopNav` (BrandLockup + nav + amber "Escanear mi sitio" CTA,
 * NO sidebar) and a `Footer`. The SOC theater renders its own dark `.soc`
 * container INSIDE this shell, so it deliberately hides this nav (its page owns
 * the war-room frame). Everything else reads on the light app shell.
 */
import { TopNav } from "@/src/presentation/owliver/chrome/top-nav";
import { Footer } from "@/src/presentation/owliver/chrome/footer";

export default function OwliverPublicLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen flex-col bg-background">
      <TopNav />
      <main className="flex-1">{children}</main>
      <Footer />
    </div>
  );
}
