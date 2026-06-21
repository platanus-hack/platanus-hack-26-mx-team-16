/**
 * `/watch` — Hall of Shame leaderboard (§F4) 🔴, PROTECTED (requires session).
 * The portada: "Seguridad bajo la lupa" — a worst-first ranking of audited sites,
 * red and provocative. Server Component: it loads the authoritative worst-first
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
import { ScaleLegend } from "@/src/presentation/owliver/components/scale-legend";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";
import { CtaBand } from "@/src/presentation/owliver/leaderboard/cta-band";
import { HeroStats } from "@/src/presentation/owliver/leaderboard/hero-stats";
import { LeaderboardBoard } from "@/src/presentation/owliver/leaderboard/leaderboard-board";
import { MethodologyBand } from "@/src/presentation/owliver/leaderboard/methodology-band";

export const metadata = {
  title: "Seguridad bajo la lupa",
  description:
    "Ranking de seguridad de sitios web, peores primero: seguridad web + superficie agéntica de IA, con calificación A–F. Datos 100% pasivos y públicos.",
};

// Always render fresh server data (the board hydrates from here).
export const dynamic = "force-dynamic";

export default async function HallOfShamePage() {
  const { rows } = await loadRankingPage("mx");
  const failing = rows.filter((r) => r.overallGrade === "F").length;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 md:px-6 md:py-14">
      {/* Hero — provocative */}
      <section className="mb-14 grid gap-8 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-end">
        <div>
          <p className="mb-4 inline-flex items-center gap-2 rounded-full bg-primary-container px-3 py-1 font-mono text-xs font-semibold uppercase tracking-wide text-on-primary-container">
            <span className="size-2 rounded-full bg-primary" aria-hidden />
            Seguridad bajo la lupa
          </p>
          <h1 className="font-display max-w-4xl text-5xl font-semibold leading-[0.9] tracking-[-0.02em] text-balance text-foreground md:text-7xl">
            La seguridad, medida como evidencia.
          </h1>
          <p className="mt-5 max-w-2xl text-base leading-7 text-on-surface-variant md:text-lg">
            Owliver ordena sitios de peor a mejor, muestra la razón técnica y
            cruza seguridad web con superficie agéntica para que el riesgo se
            pueda inspeccionar sin ruido.
          </p>
          <HeroStats total={rows.length} failing={failing} className="mt-5" />
          <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
            Datos 100% pasivos y públicos — equivalente a Mozilla Observatory /
            SSL Labs / Shodan. No intrusivo.
          </p>
          <div className="mt-7 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/scan"
              className={buttonVariants({ variant: "default", size: "xl" })}
            >
              Audita cualquier URL →
            </Link>
            <Link
              href="/watcher"
              className={buttonVariants({ variant: "outline", size: "xl" })}
            >
              Ir a mi watchlist
            </Link>
          </div>
        </div>

        <div className="rounded-3xl bg-surface-container-low p-5 shadow-[0_8px_18px_rgba(40,30,8,0.10)]">
          <div className="flex items-center justify-between gap-3 border-b border-outline-variant pb-4">
            <div>
              <p className="font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
                Banco de inspección
              </p>
              <p className="mt-1 text-sm text-on-surface-variant">
                Web, agentes y grado global en una sola lectura.
              </p>
            </div>
            <div className="rounded-2xl bg-primary p-3 text-primary-foreground">
              <ShieldWeb className="size-5" />
            </div>
          </div>

          <div className="mt-5 grid grid-cols-2 gap-4">
            <div className="border-r border-outline-variant pr-4">
              <ShieldWeb className="size-5 text-primary" />
              <p className="mt-3 font-semibold text-foreground">Web</p>
              <p className="mt-1 text-sm text-on-surface-variant">
                TLS, cabeceras, exposición y configuración.
              </p>
            </div>
            <div>
              <AgenticChip className="size-5 text-secondary" />
              <p className="mt-3 font-semibold text-foreground">Agéntico</p>
              <p className="mt-1 text-sm text-on-surface-variant">
                Prompts, asistentes y widgets de IA embebidos.
              </p>
            </div>
          </div>

          <div className="mt-5 border-t border-outline-variant pt-4">
            <p className="mb-3 font-mono text-xs font-semibold uppercase tracking-wide text-on-surface-variant">
              Escala visible
            </p>
            <ScaleLegend />
          </div>
        </div>
      </section>

      {/* Ranking (worst-first; server order preserved) */}
      <LeaderboardBoard initialRows={rows} country="mx" />

      <MethodologyBand />
      <CtaBand />
    </div>
  );
}
