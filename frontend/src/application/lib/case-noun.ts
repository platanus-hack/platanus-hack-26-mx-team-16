import type { CaseNoun } from "@/src/domain/entities/workflow";

// Default i18n cuando el workflow no trae `caseNoun` (product/specs/data-model/case-noun.md §2).
const FALLBACK: CaseNoun = {
  es: { one: "Caso", other: "Casos" },
  en: { one: "Case", other: "Cases" },
};

/**
 * Sustantivo visible del caso para un workflow, en el locale activo. Devuelve el
 * noun configurado (`caseNoun`) o el default i18n («Caso/Casos», "Case/Cases")
 * si el workflow no lo trae. Función PURA: el `locale` lo pasa el llamador
 * (p.ej. `useLocale()` de next-intl), así puede usarse en cualquier contexto.
 *
 * Los plurales son SIEMPRE explícitos; no se pluraliza ni se transforma la
 * capitalización (el noun se guarda tal cual se muestra).
 *
 * @param count 1 ⇒ singular (`one`); cualquier otro ⇒ plural (`other`).
 */
export function caseNoun(
  workflow: { caseNoun?: CaseNoun | null } | null | undefined,
  locale: string,
  count: number
): string {
  const lang = locale.startsWith("en") ? "en" : "es";
  const forms = workflow?.caseNoun?.[lang] ?? FALLBACK[lang];
  return count === 1 ? forms.one : forms.other;
}
