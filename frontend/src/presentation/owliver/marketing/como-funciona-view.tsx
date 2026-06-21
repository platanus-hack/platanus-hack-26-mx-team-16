/**
 * ComoFuncionaView — the public "Cómo funciona" page (design `g3h4Yo`): hero,
 * 3-step flow, the two scored dimensions (web OWASP + agentic surface), the A–F
 * grade scale, the three scan levels, an FAQ accordion and a closing CTA band.
 * Server component (static); lives inside `(public)/(owliver)`, so the TopNav +
 * Footer chrome comes from that layout.
 */
import { Award, Check, Link as LinkIcon, Radar } from "lucide-react";
import Link from "next/link";

import type { Grade } from "@/src/application/owliver/schemas/api";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";

const STEPS = [
  {
    icon: LinkIcon,
    title: "Ingresa una URL y un nivel",
    body: "Pega cualquier dominio y elige qué tan a fondo escanear: básico pasivo, intermedio o avanzado (con autorización).",
  },
  {
    icon: Radar,
    title: "El equipo de agentes audita",
    body: "Un orquestador (Opus) coordina dos agentes (Sonnet) que corren Nuclei, ZAP, testssl y más, mientras sondean la IA embebida. Lo ves en vivo.",
  },
  {
    icon: Award,
    title: "Recibe tu grado A–F",
    body: "Un reporte de dos capas: ejecutiva (qué pasa y por qué importa) y técnica (evidencia, impacto y remediación paso a paso).",
  },
];

const WEB_CHECKS = [
  "Cabeceras de seguridad y CSP",
  "Configuración TLS/SSL y cifrados",
  "Inyección, XSS y exposición de datos",
  "Componentes y dependencias vulnerables",
  "Autenticación, sesiones y configuración",
];

const AGENTIC_CHECKS = [
  "Inventario de chatbots y widgets de IA",
  "Prompt-injection directa e indirecta",
  "Jailbreaks y fuga del system prompt",
  "Exfiltración de datos a través de la IA",
  "Abuso de herramientas y acciones del agente",
];

const GRADES: { grade: Grade; range: string }[] = [
  { grade: "A", range: "≥90 seguro" },
  { grade: "B", range: "≥80" },
  { grade: "C", range: "≥70" },
  { grade: "D", range: "≥60" },
  { grade: "E", range: "≥40" },
  { grade: "F", range: "<40" },
];

const LEVELS = [
  {
    name: "Básico",
    tag: "pasivo · anónimo",
    tagClass: "bg-primary-container text-on-primary-container",
    body: "Sondas no intrusivas sobre datos públicos: cabeceras, TLS, tecnologías e inventario de IA. No requiere permisos ni autorización del dominio.",
    recommended: true,
  },
  {
    name: "Intermedio",
    tag: "activo suave",
    tagClass: "bg-tertiary-container text-on-tertiary-container",
    body: "Pruebas activas con rate-limiting: fuzzing ligero y sondas de inyección al chatbot. Requiere declarar autorización sobre el dominio.",
    recommended: false,
  },
  {
    name: "Avanzado",
    tag: "explotación",
    tagClass: "bg-destructive/15 text-destructive-deep",
    body: "Explotación controlada para confirmar hallazgos. Solo con autorización explícita del propietario del dominio.",
    recommended: false,
  },
];

const FAQ = [
  {
    q: "¿Es legal escanear cualquier sitio?",
    a: "El nivel básico es 100% pasivo y público —equivalente a Mozilla Observatory o SSL Labs—. Para niveles activos exigimos que declares autorización sobre el dominio.",
  },
  {
    q: "¿Cuánto tarda un escaneo?",
    a: "Menos de 90 segundos para un escaneo básico. Lo ves correr en vivo, paso a paso.",
  },
  {
    q: "¿Qué es la “superficie agéntica”?",
    a: "Los chatbots, cajas de prompt y widgets de IA embebidos en tu sitio. Casi nadie los audita; Owliver los detecta y los prueba contra prompt-injection y jailbreaks.",
  },
  {
    q: "¿Guardan mis datos?",
    a: "El ranking público solo usa datos pasivos. Tus escaneos privados viven en tu watchlist y no se publican sin tu consentimiento.",
  },
  {
    q: "¿Puedo monitorear de forma continua?",
    a: "Sí. Agrega dominios a tu watchlist para re-escaneos periódicos y alertas por email o Slack cuando el grado cambie.",
  },
];

export function ComoFuncionaView() {
  return (
    <div className="flex flex-col">
      {/* Hero */}
      <section className="flex flex-col items-center gap-5 bg-card px-6 py-20 text-center">
        <span className="rounded-full bg-primary-container px-3.5 py-1.5 font-mono text-xs font-semibold tracking-wide text-on-primary-container">
          CÓMO FUNCIONA
        </span>
        <h1 className="max-w-3xl text-balance text-5xl font-extrabold leading-[1.05] tracking-tight text-foreground">
          Tú das una URL. Owliver hace el resto.
        </h1>
        <p className="max-w-2xl text-pretty text-[17px] leading-relaxed text-muted-foreground">
          Un equipo de agentes de IA audita tu sitio —OWASP clásico y la
          superficie agéntica— y te entrega un grado A–F fácil de entender pero
          técnicamente valioso.
        </p>
      </section>

      {/* Steps */}
      <section className="mx-auto grid w-full max-w-6xl gap-5 px-6 pt-16 pb-10 md:grid-cols-3">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          return (
            <div
              key={step.title}
              className="flex flex-col gap-4 rounded-3xl bg-surface-container-low p-7"
            >
              <div className="flex items-center gap-3.5">
                <span className="flex size-11 items-center justify-center rounded-full bg-tertiary-container font-mono text-lg font-bold text-on-tertiary-container">
                  {i + 1}
                </span>
                <Icon className="size-6 text-primary" />
              </div>
              <h2 className="text-xl font-bold text-foreground">
                {step.title}
              </h2>
              <p className="text-[15px] leading-relaxed text-muted-foreground">
                {step.body}
              </p>
            </div>
          );
        })}
      </section>

      {/* Dimensions */}
      <section className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 pt-10 pb-16">
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-3xl font-bold text-foreground">
            Dos dimensiones, un solo grado
          </h2>
          <p className="max-w-xl text-[15px] text-muted-foreground">
            La peor de las dos dimensiones arrastra tu calificación global.
          </p>
        </div>
        <div className="grid gap-5 lg:grid-cols-2">
          <DimensionCard
            icon={<ShieldWeb className="size-6 text-primary" />}
            iconClass="bg-primary-container"
            title="Web · OWASP"
            description="Cobertura clásica y a fondo del sitio, en lenguaje claro."
            checks={WEB_CHECKS}
          />
          <DimensionCard
            icon={<AgenticChip className="size-6 text-tertiary" />}
            iconClass="bg-tertiary-container"
            title="Agéntico · lo que nadie mide"
            description="Detectamos y atacamos la IA embebida en tu sitio."
            checks={AGENTIC_CHECKS}
          />
        </div>
      </section>

      {/* Grade scale */}
      <section className="flex flex-col items-center gap-6 bg-surface-container px-6 py-14">
        <h2 className="text-center text-[28px] font-bold text-foreground">
          Tu calificación, de un vistazo
        </h2>
        <div className="flex flex-wrap justify-center gap-3.5">
          {GRADES.map(({ grade, range }) => (
            <div key={grade} className="flex flex-col items-center gap-2">
              <GradeBadge grade={grade} size="lg" />
              <span className="font-mono text-xs text-outline">{range}</span>
            </div>
          ))}
        </div>
        <p className="max-w-lg text-center text-sm text-muted-foreground">
          Una sola letra, estilo Mozilla Observatory: el grado salta a la vista
          y los detalles técnicos están a un clic.
        </p>
      </section>

      {/* Levels */}
      <section className="mx-auto flex w-full max-w-6xl flex-col gap-6 px-6 py-16">
        <h2 className="text-center text-3xl font-bold text-foreground">
          Tú eliges qué tan a fondo
        </h2>
        <div className="grid gap-5 lg:grid-cols-3">
          {LEVELS.map((level) => (
            <div
              key={level.name}
              className={`flex flex-col gap-3.5 rounded-3xl bg-card p-7 ${
                level.recommended
                  ? "ring-2 ring-primary"
                  : "border border-outline-variant"
              }`}
            >
              <div className="flex items-center justify-between gap-2.5">
                <h3 className="text-xl font-bold text-foreground">
                  {level.name}
                </h3>
                {level.recommended && (
                  <span className="rounded-full bg-primary-container px-2.5 py-1 font-mono text-[11px] font-semibold text-on-primary-container">
                    Recomendado
                  </span>
                )}
              </div>
              <span
                className={`w-fit rounded-full px-3 py-1 font-mono text-xs font-semibold ${level.tagClass}`}
              >
                {level.tag}
              </span>
              <p className="text-[15px] leading-relaxed text-muted-foreground">
                {level.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* FAQ */}
      <section className="bg-surface-container-low px-6 py-16">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-3.5">
          <h2 className="text-3xl font-bold text-foreground">
            Preguntas frecuentes
          </h2>
          {FAQ.map((item) => (
            <details
              key={item.q}
              className="group rounded-xl border border-outline-variant bg-card p-6"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                <span className="text-[17px] font-semibold text-foreground">
                  {item.q}
                </span>
                <span className="text-outline transition-transform group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
                {item.a}
              </p>
            </details>
          ))}
        </div>
      </section>

      {/* CTA band */}
      <section className="flex flex-col items-center gap-5 bg-primary-container px-6 py-16 text-center">
        <h2 className="max-w-2xl text-balance text-[34px] font-extrabold leading-tight text-on-primary-container">
          Audita tu primer sitio en 90 segundos.
        </h2>
        <Link
          href="/scan"
          className={buttonVariants({ variant: "tertiary", size: "xl" })}
        >
          Audita cualquier URL →
        </Link>
      </section>
    </div>
  );
}

function DimensionCard({
  icon,
  iconClass,
  title,
  description,
  checks,
}: {
  icon: React.ReactNode;
  iconClass: string;
  title: string;
  description: string;
  checks: string[];
}) {
  return (
    <div className="flex flex-col gap-4 rounded-3xl border border-outline-variant bg-card p-8">
      <div className="flex items-center gap-3.5">
        <span
          className={`flex size-13 items-center justify-center rounded-2xl ${iconClass}`}
        >
          {icon}
        </span>
        <h3 className="text-xl font-bold text-foreground">{title}</h3>
      </div>
      <p className="text-[15px] leading-relaxed text-muted-foreground">
        {description}
      </p>
      <ul className="flex flex-col gap-2.5 pt-1.5">
        {checks.map((check) => (
          <li
            key={check}
            className="flex items-center gap-2.5 text-[15px] text-foreground"
          >
            <Check className="size-4 shrink-0 text-primary" />
            {check}
          </li>
        ))}
      </ul>
    </div>
  );
}
