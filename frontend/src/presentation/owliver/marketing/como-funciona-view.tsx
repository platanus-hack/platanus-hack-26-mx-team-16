/**
 * ComoFuncionaView — the public landing (`/`, design `g3h4Yo` evolved into a
 * conversion surface): an interactive hero (live URL form + self-running audit
 * demo), the 3-step flow wired by the violet signal, the two scored dimensions,
 * a live-theater teaser, the A–F scale, scan depths, **credits pricing**, an FAQ
 * and a closing CTA. Server component; interactive/animated pieces are isolated
 * client islands. Chrome (TopNav + Footer) comes from `(public)/(owliver)`.
 */
import { Check, Radar } from "lucide-react";
import Image from "next/image";
import Link from "next/link";

import type { Grade } from "@/src/application/owliver/schemas/api";
import { Reveal } from "@/src/presentation/components/common/reveal";
import { buttonVariants } from "@/src/presentation/components/ui/button-variants";
import { GradeBadge } from "@/src/presentation/owliver/components/grade-badge";
import { AgenticChip, ShieldWeb } from "@/src/presentation/owliver/icons";
import { HeroScanDemo } from "@/src/presentation/owliver/marketing/hero-scan-demo";
import { HeroUrlForm } from "@/src/presentation/owliver/marketing/hero-url-form";
import { LandingSteps } from "@/src/presentation/owliver/marketing/landing-steps";
import { LiveFeedTeaser } from "@/src/presentation/owliver/marketing/live-feed-teaser";
import { PricingCredits } from "@/src/presentation/owliver/marketing/pricing-credits";

const TRUST = [
  "OWASP Top 10",
  "OWASP LLM Top 10",
  "Nuclei · ZAP · testssl",
  "garak · promptfoo",
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
    cost: "1 crédito",
    recommended: true,
  },
  {
    name: "Intermedio",
    tag: "activo suave",
    tagClass: "bg-tertiary-container text-on-tertiary-container",
    body: "Pruebas activas con rate-limiting: fuzzing ligero y sondas de inyección al chatbot. Requiere declarar autorización sobre el dominio.",
    cost: "4 créditos",
    recommended: false,
  },
  {
    name: "Avanzado",
    tag: "explotación",
    tagClass: "bg-destructive/15 text-destructive-deep",
    body: "Explotación controlada para confirmar hallazgos. Solo con autorización explícita del propietario del dominio.",
    cost: "12 créditos",
    recommended: false,
  },
];

const FAQ = [
  {
    q: "¿Es legal escanear cualquier sitio?",
    a: "El nivel básico es 100% pasivo y público —equivalente a Mozilla Observatory o SSL Labs—. Para niveles activos exigimos que declares autorización sobre el dominio.",
  },
  {
    q: "¿Cómo funcionan los créditos?",
    a: "Cada escaneo descuenta créditos según su profundidad: básico 1, intermedio 4, avanzado 12. Tu plan renueva un pool de créditos cada mes y puedes comprar más cuando los necesites.",
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
      {/* ── Hero ─────────────────────────────────────────────────────── */}
      <section className="landing-pattern-hero relative overflow-hidden border-b border-outline-variant/60 bg-card">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-32 -top-32 size-[28rem] rounded-full bg-primary/12 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute bottom-8 left-[48%] hidden h-40 w-40 rounded-[1.75rem] bg-secondary-container/35 blur-3xl lg:block"
        />
        <div className="mx-auto grid w-full max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-[1.05fr_0.95fr] lg:py-24">
          <Reveal className="flex flex-col items-start gap-6">
            <span className="inline-flex items-center gap-2 rounded-full bg-primary-container px-3.5 py-1.5 font-mono text-xs font-semibold uppercase tracking-[0.12em] text-on-primary-container">
              <span className="size-1.5 rounded-full bg-primary" />
              Auditoría automatizada · OWASP + IA
            </span>
            <h1 className="text-balance font-display text-[2.75rem] font-bold leading-[1.02] tracking-tight text-foreground sm:text-6xl lg:text-[4.25rem]">
              Audita tu web y tu IA. Recibe un grado A–F.
            </h1>
            <p className="max-w-xl text-pretty text-lg leading-relaxed text-on-surface-variant">
              Un equipo de agentes corre OWASP clásico y prueba la superficie
              agéntica —chatbots y widgets de IA— y te entrega un reporte claro
              pero técnicamente valioso, en menos de 90 segundos.
            </p>
            <HeroUrlForm className="max-w-md" />
            <ul className="flex flex-wrap gap-x-5 gap-y-2 pt-1">
              {TRUST.map((t) => (
                <li
                  key={t}
                  className="flex items-center gap-1.5 text-sm text-on-surface-variant"
                >
                  <Check className="size-4 text-secondary" />
                  {t}
                </li>
              ))}
            </ul>
          </Reveal>

          <Reveal delay={140} className="lg:pl-4">
            <HeroScanDemo />
          </Reveal>
        </div>
      </section>

      {/* ── Steps ────────────────────────────────────────────────────── */}
      <section className="landing-pattern-steps mx-auto w-full max-w-6xl px-6 py-16 lg:py-20">
        <div className="mb-10 flex flex-col items-center gap-2 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            De una URL a un grado, en 3 pasos
          </h2>
          <p className="max-w-xl text-[15px] text-on-surface-variant">
            Tú das el objetivo; el equipo de agentes hace la inspección y te
            deja la evidencia.
          </p>
        </div>
        <LandingSteps />
      </section>

      {/* ── Dimensions ───────────────────────────────────────────────── */}
      <section className="landing-pattern-dimensions mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 pb-16 lg:pb-20">
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Dos dimensiones, un solo grado
          </h2>
          <p className="max-w-xl text-[15px] text-on-surface-variant">
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

      {/* ── Live theater teaser ──────────────────────────────────────── */}
      <section className="landing-pattern-live border-y border-outline-variant/60 bg-surface-container">
        <div className="mx-auto grid w-full max-w-6xl items-center gap-10 px-6 py-16 lg:grid-cols-[0.9fr_1.1fr] lg:py-20">
          <div className="flex flex-col items-start gap-5">
            <div className="flex items-center gap-3">
              <Image
                src="/owliver-icon-1000.png"
                alt=""
                width={44}
                height={44}
                className="size-11 rounded-2xl bg-surface-container-lowest p-2 shadow-sm"
                aria-hidden
              />
              <span className="font-mono text-xs font-semibold uppercase tracking-[0.14em] text-secondary">
                En vivo
              </span>
            </div>
            <h2 className="text-3xl font-bold tracking-tight text-foreground">
              No es una caja negra. Míralo trabajar.
            </h2>
            <p className="max-w-md text-pretty text-[15px] leading-relaxed text-on-surface-variant">
              Cada hallazgo aparece en el feed conforme el equipo lo confirma,
              con su severidad, categoría OWASP y evidencia. Nada de “magia de
              IA”: trabajo inspeccionable.
            </p>
            <Link
              href="/scan"
              className={buttonVariants({ variant: "outline", size: "lg" })}
            >
              <Radar className="size-4" />
              Lanza una auditoría
            </Link>
          </div>
          <Reveal delay={80}>
            <LiveFeedTeaser />
          </Reveal>
        </div>
      </section>

      {/* ── Grade scale ──────────────────────────────────────────────── */}
      <section className="landing-pattern-grades mx-auto flex w-full max-w-5xl flex-col items-center gap-8 px-6 py-16 lg:py-20">
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Tu calificación, de un vistazo
          </h2>
          <p className="max-w-lg text-[15px] text-on-surface-variant">
            Una sola letra, estilo Mozilla Observatory: el grado salta a la
            vista y los detalles técnicos están a un clic.
          </p>
        </div>
        <GradeRail />
      </section>

      {/* ── Scan depths ──────────────────────────────────────────────── */}
      <section className="landing-pattern-levels mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 pb-16 lg:pb-24">
        <div className="flex flex-col items-center gap-2 text-center">
          <h2 className="text-3xl font-bold tracking-tight text-foreground">
            Tú eliges qué tan a fondo
          </h2>
          <p className="max-w-xl text-[15px] text-on-surface-variant">
            Cada profundidad descuenta créditos distintos; empieza pasivo y sube
            cuando tengas autorización.
          </p>
        </div>
        <div className="grid gap-5 lg:grid-cols-3">
          {LEVELS.map((level) => (
            <div
              key={level.name}
              className={`relative flex flex-col gap-3.5 overflow-hidden rounded-[1.75rem] bg-card p-7 ${
                level.recommended
                  ? "ring-2 ring-primary"
                  : "border border-outline-variant"
              }`}
            >
              <div
                aria-hidden
                className="absolute inset-x-0 top-0 h-1 bg-[linear-gradient(90deg,var(--primary),var(--secondary),var(--tertiary))]"
              />
              <div className="flex items-center justify-between gap-2.5">
                <h3 className="text-xl font-bold text-foreground">
                  {level.name}
                </h3>
                <span className="font-mono text-xs font-semibold text-primary">
                  {level.cost}
                </span>
              </div>
              <span
                className={`w-fit rounded-full px-3 py-1 font-mono text-xs font-semibold ${level.tagClass}`}
              >
                {level.tag}
              </span>
              <p className="text-[15px] leading-relaxed text-on-surface-variant">
                {level.body}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── Pricing ──────────────────────────────────────────────────── */}
      <section className="landing-pattern-pricing border-y border-outline-variant/60 bg-card py-16 lg:py-24">
        <PricingCredits />
      </section>

      {/* ── FAQ ──────────────────────────────────────────────────────── */}
      <section className="landing-pattern-faq bg-surface-container-low px-6 py-16 lg:py-20">
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-3.5">
          <h2 className="mb-2 text-center text-3xl font-bold tracking-tight text-foreground">
            Preguntas frecuentes
          </h2>
          {FAQ.map((item) => (
            <details
              key={item.q}
              className="group rounded-2xl border border-outline-variant bg-card p-6 transition-colors open:bg-surface-container-lowest"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
                <span className="text-[17px] font-semibold text-foreground">
                  {item.q}
                </span>
                <span className="grid size-6 shrink-0 place-items-center rounded-full bg-surface-container text-on-surface-variant transition-transform duration-300 ease-[cubic-bezier(0.2,0,0,1)] group-open:rotate-45">
                  +
                </span>
              </summary>
              <p className="mt-3 text-[15px] leading-relaxed text-on-surface-variant">
                {item.a}
              </p>
            </details>
          ))}
        </div>
      </section>

      {/* ── Closing CTA ──────────────────────────────────────────────── */}
      <section className="landing-pattern-cta bg-primary-container px-6 py-20 text-center">
        <div className="mx-auto flex max-w-2xl flex-col items-center gap-6">
          <Image
            src="/owliver-icon-1000.png"
            alt=""
            width={76}
            height={76}
            className="size-[76px] rounded-[1.35rem] object-contain shadow-sm"
            aria-hidden
          />
          <h2 className="text-balance font-display text-4xl font-bold leading-tight tracking-tight text-on-primary-container sm:text-5xl">
            Audita tu primer sitio en 90 segundos.
          </h2>
          <p className="max-w-lg text-pretty text-[15px] text-on-primary-container/80">
            Gratis, pasivo y sin registro. Pega tu URL y mira al equipo
            trabajar.
          </p>
          <HeroUrlForm className="max-w-md" />
        </div>
      </section>
    </div>
  );
}

function GradeRail() {
  return (
    <div className="w-full rounded-[1.75rem] bg-surface-container-low p-3 shadow-[0_1px_3px_rgba(40,30,8,0.10)]">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-6">
        {GRADES.map(({ grade, range }, i) => (
          <Reveal
            key={grade}
            delay={i * 60}
            className="relative flex min-h-34 flex-col items-center justify-between overflow-hidden rounded-2xl bg-card px-3 py-4 text-center"
          >
            <span
              aria-hidden
              className="absolute inset-x-3 top-0 h-1 rounded-b-full"
              style={{ backgroundColor: `var(--grade-${grade.toLowerCase()})` }}
            />
            <GradeBadge grade={grade} size="lg" />
            <span className="font-mono text-xs text-outline">{range}</span>
          </Reveal>
        ))}
      </div>
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
      <p className="text-[15px] leading-relaxed text-on-surface-variant">
        {description}
      </p>
      <ul className="flex flex-col gap-2.5 pt-1.5">
        {checks.map((check) => (
          <li
            key={check}
            className="flex items-center gap-2.5 text-[15px] text-foreground"
          >
            <Check className="size-4 shrink-0 text-secondary" />
            {check}
          </li>
        ))}
      </ul>
    </div>
  );
}
