/**
 * MethodologyBand — the "cómo medimos" explainer below the leaderboard (§F4).
 * RSC. Two parts: the A–F scale (reusing ScaleLegend, the single source of grade
 * color) and two dimension cards explaining the differentiator — 🛡️ Web (OWASP)
 * vs 🤖 Agéntico (prompt-injection / jailbreaks of embedded chatbots), the thing
 * "casi nadie mide". Reinforces the passive/public-data defensibility framing.
 */
import { ScaleLegend } from "@/src/presentation/owliver/components/scale-legend";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";

const DIMENSIONS = [
  {
    icon: ShieldWeb,
    iconColor: "text-primary",
    title: "Seguridad Web",
    body: "El OWASP de siempre: TLS, cabeceras, inyecciones, configuración. Pruebas 100% pasivas y públicas — como Mozilla Observatory o SSL Labs.",
  },
  {
    icon: AgenticChip,
    iconColor: "text-tertiary",
    title: "Superficie Agéntica",
    body: "Lo que casi nadie mide: chatbots, cajas de prompt y widgets de IA embebidos, sondeados por inyección de prompt y jailbreaks.",
  },
];

export function MethodologyBand() {
  return (
    <section
      aria-labelledby="metodologia"
      className="mt-16 border-t border-outline-variant pt-12"
    >
      <h2
        id="metodologia"
        className="text-2xl font-semibold tracking-tight text-foreground"
      >
        Cómo medimos
      </h2>
      <p className="mt-2 max-w-2xl text-sm text-on-surface-variant">
        Cada sitio recibe un grado{" "}
        <span className="font-mono font-semibold">A–F</span> estilo Mozilla
        Observatory, en dos dimensiones. El grado global lo hunde la peor.
      </p>

      <div className="mt-6 rounded-2xl border border-outline-variant bg-card p-5">
        <p className="mb-3 text-xs font-medium uppercase tracking-wide text-on-surface-variant/70">
          Escala de grados
        </p>
        <ScaleLegend />
      </div>

      <div className="mt-4 grid gap-4 md:grid-cols-2">
        {DIMENSIONS.map((d) => (
          <div
            key={d.title}
            className="rounded-2xl border border-outline-variant bg-card p-5"
          >
            <div className="mb-2 flex items-center gap-2">
              <d.icon className={`size-5 ${d.iconColor}`} />
              <h3 className="font-semibold text-foreground">{d.title}</h3>
            </div>
            <p className="text-sm text-on-surface-variant">{d.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
