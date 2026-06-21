/**
 * Hall of Shame ranking fixture (§F4) — ~40 `.gob.mx` rows, WORST-FIRST
 * (overall grade F → A, penaltyRaw DESC tiebreak), matching the authoritative
 * order so screens never re-sort. Includes the star "SAT: C web / F agéntico"
 * contrast row and a spread of agenticStatus / partialCoverage states.
 *
 * Data is illustrative for the demo (the real board is seeded server-side).
 */
import type { Grade, RankingRow } from "../schemas/api";
import { gradeFromScore } from "../lib/grade";

type Seed = {
  host: string;
  departmentName: string;
  web: number;
  agentic: number | null;
  overall: Grade;
  penaltyRaw: number;
  agenticStatus: RankingRow["agenticStatus"];
  partial?: boolean;
  trend?: RankingRow["trend"];
  topFinding?: string;
};

// Ordered worst-first already (this is the server's authoritative order).
const SEEDS: Seed[] = [
  { host: "datos.gob.mx", departmentName: "Datos Abiertos del Gobierno", web: 22, agentic: 12, overall: "F", penaltyRaw: 214, agenticStatus: "tested", trend: "down", topFinding: "TLS 1.0 habilitado + 3 inyecciones de prompt en el asistente" },
  { host: "tramites.gob.mx", departmentName: "Portal Único de Trámites", web: 18, agentic: 20, overall: "F", penaltyRaw: 198, agenticStatus: "tested", trend: "flat", topFinding: "SQL injection en buscador de trámites" },
  { host: "salud.gob.mx", departmentName: "Secretaría de Salud", web: 28, agentic: null, overall: "F", penaltyRaw: 176, agenticStatus: "detected_not_tested", trend: "down", topFinding: "Cabeceras de seguridad ausentes; chatbot detectado sin auditar" },
  { host: "imss.gob.mx", departmentName: "Instituto Mexicano del Seguro Social", web: 31, agentic: 26, overall: "F", penaltyRaw: 168, agenticStatus: "tested", trend: "down", topFinding: "Jailbreak del asistente médico revela prompt de sistema" },
  { host: "sep.gob.mx", departmentName: "Secretaría de Educación Pública", web: 29, agentic: 38, overall: "F", penaltyRaw: 162, agenticStatus: "tested", trend: "up", topFinding: "XSS reflejado en formulario de becas" },
  { host: "cfe.gob.mx", departmentName: "Comisión Federal de Electricidad", web: 33, agentic: null, overall: "F", penaltyRaw: 154, agenticStatus: "no_surface", trend: "flat", topFinding: "Certificado caducado en subdominio de pagos" },
  { host: "pemex.gob.mx", departmentName: "Petróleos Mexicanos", web: 35, agentic: 30, overall: "F", penaltyRaw: 148, agenticStatus: "tested", trend: "down", topFinding: "Directorio expuesto con respaldos .sql" },
  { host: "infonavit.gob.mx", departmentName: "Instituto del Fondo Nacional de la Vivienda", web: 37, agentic: null, overall: "F", penaltyRaw: 141, agenticStatus: "detected_not_tested", trend: "flat", topFinding: "Widget de IA detectado, sin auditar" },
  { host: "conagua.gob.mx", departmentName: "Comisión Nacional del Agua", web: 39, agentic: 34, overall: "F", penaltyRaw: 133, agenticStatus: "tested", trend: "up", topFinding: "CSRF en panel de reportes ciudadanos" },
  { host: "profeco.gob.mx", departmentName: "Procuraduría Federal del Consumidor", web: 41, agentic: 28, overall: "E", penaltyRaw: 126, agenticStatus: "tested", partial: true, trend: "down", topFinding: "Cobertura parcial: ZAP no completó" },
  { host: "sat.gob.mx", departmentName: "Servicio de Administración Tributaria", web: 72, agentic: 24, overall: "E", penaltyRaw: 119, agenticStatus: "tested", trend: "down", topFinding: "★ Fuga de system-prompt del asistente fiscal (canary filtrado)" },
  { host: "gob.mx", departmentName: "Portal Ciudadano del Gobierno de México", web: 48, agentic: 44, overall: "E", penaltyRaw: 112, agenticStatus: "tested", trend: "flat", topFinding: "Cookies de sesión sin flag Secure" },
  { host: "issste.gob.mx", departmentName: "ISSSTE", web: 44, agentic: null, overall: "E", penaltyRaw: 104, agenticStatus: "no_surface", trend: "up", topFinding: "Versiones de software reveladas en cabeceras" },
  { host: "banxico.gob.mx", departmentName: "Banco de México", web: 51, agentic: 40, overall: "E", penaltyRaw: 98, agenticStatus: "tested", trend: "flat", topFinding: "Clickjacking posible (sin X-Frame-Options)" },
  { host: "inai.gob.mx", departmentName: "INAI — Transparencia", web: 46, agentic: null, overall: "E", penaltyRaw: 92, agenticStatus: "detected_not_tested", trend: "down", topFinding: "Chatbot de transparencia detectado, sin auditar" },
  { host: "economia.gob.mx", departmentName: "Secretaría de Economía", web: 53, agentic: 47, overall: "E", penaltyRaw: 86, agenticStatus: "tested", trend: "up", topFinding: "Mixed content en página de aranceles" },
  { host: "sct.gob.mx", departmentName: "Secretaría de Comunicaciones y Transportes", web: 49, agentic: 49, overall: "E", penaltyRaw: 81, agenticStatus: "tested", trend: "flat", topFinding: "HSTS no configurado" },
  { host: "semarnat.gob.mx", departmentName: "Secretaría de Medio Ambiente", web: 55, agentic: null, overall: "E", penaltyRaw: 74, agenticStatus: "no_surface", trend: "up", topFinding: "Formulario sin protección anti-bot" },
  { host: "sener.gob.mx", departmentName: "Secretaría de Energía", web: 58, agentic: 52, overall: "D", penaltyRaw: 68, agenticStatus: "tested", trend: "flat", topFinding: "Subdominios con certificados débiles" },
  { host: "sre.gob.mx", departmentName: "Secretaría de Relaciones Exteriores", web: 61, agentic: 48, overall: "D", penaltyRaw: 62, agenticStatus: "tested", trend: "down", topFinding: "Asistente de citas expone rutas internas" },
  { host: "gobernacion.gob.mx", departmentName: "Secretaría de Gobernación", web: 60, agentic: null, overall: "D", penaltyRaw: 57, agenticStatus: "detected_not_tested", trend: "flat", topFinding: "IA detectada, sin auditar" },
  { host: "sedena.gob.mx", departmentName: "Secretaría de la Defensa Nacional", web: 64, agentic: 55, overall: "D", penaltyRaw: 51, agenticStatus: "tested", trend: "up", topFinding: "TLS bien configurado; cabeceras parciales" },
  { host: "stps.gob.mx", departmentName: "Secretaría del Trabajo", web: 63, agentic: 59, overall: "D", penaltyRaw: 46, agenticStatus: "tested", trend: "flat", topFinding: "Cookie de sesión sin SameSite" },
  { host: "sader.gob.mx", departmentName: "Secretaría de Agricultura", web: 66, agentic: null, overall: "D", penaltyRaw: 41, agenticStatus: "no_surface", trend: "up", topFinding: "Versión de CMS expuesta" },
  { host: "cultura.gob.mx", departmentName: "Secretaría de Cultura", web: 68, agentic: 61, overall: "D", penaltyRaw: 36, agenticStatus: "tested", trend: "flat", topFinding: "Recursos sin Subresource Integrity" },
  { host: "turismo.gob.mx", departmentName: "Secretaría de Turismo", web: 69, agentic: 57, overall: "D", penaltyRaw: 32, agenticStatus: "tested", partial: true, trend: "down", topFinding: "Cobertura parcial: testssl agotó tiempo" },
  { host: "indesol.gob.mx", departmentName: "Instituto Nacional de Desarrollo Social", web: 71, agentic: null, overall: "C", penaltyRaw: 28, agenticStatus: "detected_not_tested", trend: "up", topFinding: "Asistente social detectado, sin auditar" },
  { host: "conacyt.gob.mx", departmentName: "Consejo Nacional de Ciencia y Tecnología", web: 74, agentic: 66, overall: "C", penaltyRaw: 24, agenticStatus: "tested", trend: "flat", topFinding: "Cabecera Referrer-Policy ausente" },
  { host: "inegi.gob.mx", departmentName: "INEGI — Estadística y Geografía", web: 76, agentic: 70, overall: "C", penaltyRaw: 21, agenticStatus: "tested", trend: "up", topFinding: "Buen TLS; un endpoint sin rate-limit" },
  { host: "correosdemexico.gob.mx", departmentName: "Correos de México", web: 73, agentic: 72, overall: "C", penaltyRaw: 18, agenticStatus: "tested", trend: "flat", topFinding: "Formulario de rastreo verboso en errores" },
  { host: "imjuventud.gob.mx", departmentName: "Instituto Mexicano de la Juventud", web: 78, agentic: null, overall: "C", penaltyRaw: 15, agenticStatus: "no_surface", trend: "up", topFinding: "Cabeceras casi completas" },
  { host: "conade.gob.mx", departmentName: "Comisión Nacional de Cultura Física y Deporte", web: 79, agentic: 75, overall: "C", penaltyRaw: 12, agenticStatus: "tested", trend: "flat", topFinding: "CSP en modo report-only" },
  { host: "fonatur.gob.mx", departmentName: "Fondo Nacional de Fomento al Turismo", web: 81, agentic: 74, overall: "B", penaltyRaw: 9, agenticStatus: "tested", trend: "up", topFinding: "Configuración sólida; cookie menor" },
  { host: "inmujeres.gob.mx", departmentName: "Instituto Nacional de las Mujeres", web: 83, agentic: 80, overall: "B", penaltyRaw: 7, agenticStatus: "tested", trend: "flat", topFinding: "Asistente robusto ante inyecciones básicas" },
  { host: "profepa.gob.mx", departmentName: "Procuraduría Federal de Protección al Ambiente", web: 85, agentic: null, overall: "B", penaltyRaw: 5, agenticStatus: "no_surface", trend: "up", topFinding: "TLS A; CSP presente" },
  { host: "cofepris.gob.mx", departmentName: "COFEPRIS", web: 86, agentic: 82, overall: "B", penaltyRaw: 4, agenticStatus: "tested", trend: "flat", topFinding: "Endurecimiento casi completo" },
  { host: "conapred.gob.mx", departmentName: "Consejo Nacional para Prevenir la Discriminación", web: 88, agentic: 85, overall: "B", penaltyRaw: 3, agenticStatus: "tested", trend: "up", topFinding: "Buen manejo de errores y cabeceras" },
  { host: "presidencia.gob.mx", departmentName: "Presidencia de la República", web: 91, agentic: 88, overall: "A", penaltyRaw: 2, agenticStatus: "tested", trend: "flat", topFinding: "Sin hallazgos altos; asistente resistente" },
  { host: "scjn.gob.mx", departmentName: "Suprema Corte de Justicia de la Nación", web: 93, agentic: null, overall: "A", penaltyRaw: 1, agenticStatus: "no_surface", trend: "up", topFinding: "Configuración ejemplar" },
  { host: "ine.gob.mx", departmentName: "Instituto Nacional Electoral", web: 94, agentic: 90, overall: "A", penaltyRaw: 0, agenticStatus: "tested", trend: "flat", topFinding: "TLS A+, CSP estricta, asistente endurecido" },
];

export const rankingFixture: RankingRow[] = SEEDS.map((s, i) => ({
  siteId: `site-${s.host.replace(/\./g, "-")}`,
  rank: i + 1,
  host: s.host,
  departmentName: s.departmentName,
  faviconUrl: `https://www.google.com/s2/favicons?domain=${s.host}&sz=64`,
  isGov: true,
  country: "mx",
  overallGrade: s.overall,
  webScore: s.web,
  agenticScore: s.agentic,
  webGrade: gradeFromScore(s.web),
  agenticGrade: s.agentic === null ? null : gradeFromScore(s.agentic),
  penaltyRaw: s.penaltyRaw,
  agenticStatus: s.agenticStatus,
  partialCoverage: s.partial ?? false,
  trend: s.trend ?? "flat",
  topFinding: s.topFinding ?? null,
  lastScanAt: new Date(Date.now() - i * 3_600_000).toISOString(),
}));

/** The star contrast row (SAT) — handy for component stories/tests. */
export const satRow: RankingRow =
  rankingFixture.find((r) => r.host === "sat.gob.mx") ?? rankingFixture[0];
