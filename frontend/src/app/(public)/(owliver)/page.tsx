/**
 * `/` — Hall of Shame leaderboard (§F4) 🔴. The portada: "El Estado bajo la lupa"
 * — a worst-first ranking of `.gob.mx` sites, red and provocative, framed as the
 * civic gancho viral. Server Component: it loads the authoritative worst-first
 * page (`GET /v1/ranking?country=mx`, fixture fallback) and hands it to the
 * client board, which owns filters / "cargar más" / the count-up + pulse +
 * hover-reveal micro-interactions.
 *
 * The board NEVER re-sorts — the server's `(overall_grade DESC, penalty_raw DESC)`
 * worst-first order is authoritative. The methodology + CTA bands sit below; the public chrome
 * (TopNav + Footer) comes from the (owliver) layout.
 */
import Link from "next/link";

import { loadRankingPage } from "@/src/application/owliver/server/ranking";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { CtaBand } from "@/src/presentation/owliver/leaderboard/cta-band";
import { HeroStats } from "@/src/presentation/owliver/leaderboard/hero-stats";
import { LeaderboardBoard } from "@/src/presentation/owliver/leaderboard/leaderboard-board";
import { MethodologyBand } from "@/src/presentation/owliver/leaderboard/methodology-band";

export const metadata = {
  title: "El Estado bajo la lupa · Owliver",
  description:
    "Ranking de seguridad de los sitios del gobierno mexicano (.gob.mx), peores primero. Datos 100% pasivos y públicos.",
};

// Always render fresh server data (the board hydrates from here).
export const dynamic = "force-dynamic";

export default async function HallOfShamePage() {
  const { rows } = await loadRankingPage("mx");
  const failing = rows.filter((r) => r.overallGrade === "F").length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 md:px-6">
      {/* Hero — provocative */}
      <section className="mb-10">
        <p className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-grade-f/12 px-3 py-1 text-xs font-medium text-grade-f">
          <span className="size-2 rounded-full bg-grade-f" aria-hidden />
          El Estado bajo la lupa
        </p>
        <h1 className="text-4xl font-semibold tracking-tight text-foreground md:text-5xl">
          ¿Qué tan segura es la IA del gobierno?
        </h1>
        <HeroStats total={rows.length} failing={failing} />
        <p className="mt-2 max-w-2xl text-sm text-on-surface-variant/80">
          Datos 100% pasivos y públicos — equivalente a Mozilla Observatory /
          SSL Labs / Shodan. No intrusivo.
        </p>
        <div className="mt-6">
          <Link
            href="/scan"
            className={buttonVariants({ variant: "tertiary", size: "lg" })}
          >
            Audita cualquier URL →
          </Link>
        </div>
      </section>

      {/* Ranking (worst-first; server order preserved) */}
      <LeaderboardBoard initialRows={rows} country="mx" />

      <MethodologyBand />
      <CtaBand />
    </div>
  );
}
