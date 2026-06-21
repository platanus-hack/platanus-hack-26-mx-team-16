/**
 * Hall of Shame ranking fixture (§F4) — ~40 demo rows, WORST-FIRST
 * (overall grade F → A, penaltyRaw DESC tiebreak), matching the authoritative
 * order so screens never re-sort. Includes the star "Fabrikam: C web / F agéntico"
 * contrast row and a spread of agenticStatus / partialCoverage states.
 *
 * Hosts use fictional demo brands (Contoso, Fabrikam, Northwind, …) — the real
 * board is seeded server-side. Data is illustrative for the demo only.
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
  { host: "shop.contoso.com", departmentName: "Contoso Retail", web: 22, agentic: 12, overall: "F", penaltyRaw: 214, agenticStatus: "tested", trend: "down", topFinding: "TLS 1.0 habilitado + 3 inyecciones de prompt en el asistente" },
  { host: "portal.tailspintoys.com", departmentName: "Tailspin Toys", web: 18, agentic: 20, overall: "F", penaltyRaw: 198, agenticStatus: "tested", trend: "flat", topFinding: "SQL injection en el buscador del catálogo" },
  { host: "mediq-health.com", departmentName: "MediQ Health", web: 28, agentic: null, overall: "F", penaltyRaw: 176, agenticStatus: "detected_not_tested", trend: "down", topFinding: "Cabeceras de seguridad ausentes; chatbot detectado sin auditar" },
  { host: "app.wideworldhealth.com", departmentName: "Wide World Health", web: 31, agentic: 26, overall: "F", penaltyRaw: 168, agenticStatus: "tested", trend: "down", topFinding: "Jailbreak del asistente de soporte revela el prompt de sistema" },
  { host: "learn.adventureworks.com", departmentName: "Adventure Works Academy", web: 29, agentic: 38, overall: "F", penaltyRaw: 162, agenticStatus: "tested", trend: "up", topFinding: "XSS reflejado en el formulario de registro" },
  { host: "pay.citypowerlight.com", departmentName: "City Power & Light", web: 33, agentic: null, overall: "F", penaltyRaw: 154, agenticStatus: "no_surface", trend: "flat", topFinding: "Certificado caducado en el subdominio de pagos" },
  { host: "assets.northwind.com", departmentName: "Northwind Traders", web: 35, agentic: 30, overall: "F", penaltyRaw: 148, agenticStatus: "tested", trend: "down", topFinding: "Directorio expuesto con respaldos .sql" },
  { host: "portal.woodgrovebank.com", departmentName: "Woodgrove Bank", web: 37, agentic: null, overall: "F", penaltyRaw: 141, agenticStatus: "detected_not_tested", trend: "flat", topFinding: "Widget de IA detectado, sin auditar" },
  { host: "support.relecloud.com", departmentName: "Relecloud", web: 39, agentic: 34, overall: "F", penaltyRaw: 133, agenticStatus: "tested", trend: "up", topFinding: "CSRF en el panel de tickets de soporte" },
  { host: "help.proseware.com", departmentName: "Proseware, Inc.", web: 41, agentic: 28, overall: "E", penaltyRaw: 126, agenticStatus: "tested", partial: true, trend: "down", topFinding: "Cobertura parcial: ZAP no completó" },
  { host: "fabrikam.com", departmentName: "Fabrikam, Inc.", web: 72, agentic: 24, overall: "E", penaltyRaw: 119, agenticStatus: "tested", trend: "down", topFinding: "★ Fuga de system-prompt del asistente de compras (canary filtrado)" },
  { host: "www.vanarsdelltd.com", departmentName: "VanArsdel, Ltd.", web: 48, agentic: 44, overall: "E", penaltyRaw: 112, agenticStatus: "tested", trend: "flat", topFinding: "Cookies de sesión sin flag Secure" },
  { host: "secure.litware.com", departmentName: "Litware, Inc.", web: 44, agentic: null, overall: "E", penaltyRaw: 104, agenticStatus: "no_surface", trend: "up", topFinding: "Versiones de software reveladas en cabeceras" },
  { host: "online.lucernebank.com", departmentName: "Lucerne Bank", web: 51, agentic: 40, overall: "E", penaltyRaw: 98, agenticStatus: "tested", trend: "flat", topFinding: "Clickjacking posible (sin X-Frame-Options)" },
  { host: "chat.cohowinery.com", departmentName: "Coho Winery", web: 46, agentic: null, overall: "E", penaltyRaw: 92, agenticStatus: "detected_not_tested", trend: "down", topFinding: "Chatbot de atención detectado, sin auditar" },
  { host: "store.wingtiptoys.com", departmentName: "Wingtip Toys", web: 53, agentic: 47, overall: "E", penaltyRaw: 86, agenticStatus: "tested", trend: "up", topFinding: "Mixed content en la página de checkout" },
  { host: "book.blueyonderairlines.com", departmentName: "Blue Yonder Airlines", web: 49, agentic: 49, overall: "E", penaltyRaw: 81, agenticStatus: "tested", trend: "flat", topFinding: "HSTS no configurado" },
  { host: "www.alpineskihouse.com", departmentName: "Alpine Ski House", web: 55, agentic: null, overall: "E", penaltyRaw: 74, agenticStatus: "no_surface", trend: "up", topFinding: "Formulario sin protección anti-bot" },
  { host: "grid.fourthcoffee.com", departmentName: "Fourth Coffee", web: 58, agentic: 52, overall: "D", penaltyRaw: 68, agenticStatus: "tested", trend: "flat", topFinding: "Subdominios con certificados débiles" },
  { host: "book.margiestravel.com", departmentName: "Margie's Travel", web: 61, agentic: 48, overall: "D", penaltyRaw: 62, agenticStatus: "tested", trend: "down", topFinding: "El asistente de reservas expone rutas internas" },
  { host: "app.consolidatedmessenger.com", departmentName: "Consolidated Messenger", web: 60, agentic: null, overall: "D", penaltyRaw: 57, agenticStatus: "detected_not_tested", trend: "flat", topFinding: "IA detectada, sin auditar" },
  { host: "secure.treyresearch.net", departmentName: "Trey Research", web: 64, agentic: 55, overall: "D", penaltyRaw: 51, agenticStatus: "tested", trend: "up", topFinding: "TLS bien configurado; cabeceras parciales" },
  { host: "careers.humongousinsurance.com", departmentName: "Humongous Insurance", web: 63, agentic: 59, overall: "D", penaltyRaw: 46, agenticStatus: "tested", trend: "flat", topFinding: "Cookie de sesión sin SameSite" },
  { host: "shop.tailwindtraders.com", departmentName: "Tailwind Traders", web: 66, agentic: null, overall: "D", penaltyRaw: 41, agenticStatus: "no_surface", trend: "up", topFinding: "Versión del CMS expuesta" },
  { host: "www.graphicdesigninstitute.com", departmentName: "Graphic Design Institute", web: 68, agentic: 61, overall: "D", penaltyRaw: 36, agenticStatus: "tested", trend: "flat", topFinding: "Recursos sin Subresource Integrity" },
  { host: "stay.lakeviewhotels.com", departmentName: "Lakeview Hotels & Resorts", web: 69, agentic: 57, overall: "D", penaltyRaw: 32, agenticStatus: "tested", partial: true, trend: "down", topFinding: "Cobertura parcial: testssl agotó tiempo" },
  { host: "help.firstupconsultants.com", departmentName: "First Up Consultants", web: 71, agentic: null, overall: "C", penaltyRaw: 28, agenticStatus: "detected_not_tested", trend: "up", topFinding: "Asistente de ayuda detectado, sin auditar" },
  { host: "www.bellowscollege.com", departmentName: "Bellows College", web: 74, agentic: 66, overall: "C", penaltyRaw: 24, agenticStatus: "tested", trend: "flat", topFinding: "Cabecera Referrer-Policy ausente" },
  { host: "data.wideworldimporters.com", departmentName: "Wide World Importers", web: 76, agentic: 70, overall: "C", penaltyRaw: 21, agenticStatus: "tested", trend: "up", topFinding: "Buen TLS; un endpoint sin rate-limit" },
  { host: "track.parcelpoint.com", departmentName: "ParcelPoint", web: 73, agentic: 72, overall: "C", penaltyRaw: 18, agenticStatus: "tested", trend: "flat", topFinding: "Formulario de rastreo verboso en errores" },
  { host: "app.fabrikamfiber.com", departmentName: "Fabrikam Fiber", web: 78, agentic: null, overall: "C", penaltyRaw: 15, agenticStatus: "no_surface", trend: "up", topFinding: "Cabeceras casi completas" },
  { host: "www.adatum.com", departmentName: "Adatum Corporation", web: 79, agentic: 75, overall: "C", penaltyRaw: 12, agenticStatus: "tested", trend: "flat", topFinding: "CSP en modo report-only" },
  { host: "book.seaside-resorts.com", departmentName: "Seaside Resorts", web: 81, agentic: 74, overall: "B", penaltyRaw: 9, agenticStatus: "tested", trend: "up", topFinding: "Configuración sólida; cookie menor" },
  { host: "www.southridgevideo.com", departmentName: "Southridge Video", web: 83, agentic: 80, overall: "B", penaltyRaw: 7, agenticStatus: "tested", trend: "flat", topFinding: "Asistente robusto ante inyecciones básicas" },
  { host: "www.thephone-company.com", departmentName: "The Phone Company", web: 85, agentic: null, overall: "B", penaltyRaw: 5, agenticStatus: "no_surface", trend: "up", topFinding: "TLS A; CSP presente" },
  { host: "app.bestforyouorganics.com", departmentName: "Best For You Organics", web: 86, agentic: 82, overall: "B", penaltyRaw: 4, agenticStatus: "tested", trend: "flat", topFinding: "Endurecimiento casi completo" },
  { host: "www.schooloffineart.net", departmentName: "School of Fine Art", web: 88, agentic: 85, overall: "B", penaltyRaw: 3, agenticStatus: "tested", trend: "up", topFinding: "Buen manejo de errores y cabeceras" },
  { host: "www.lamnahealthcare.com", departmentName: "Lamna Healthcare", web: 91, agentic: 88, overall: "A", penaltyRaw: 2, agenticStatus: "tested", trend: "flat", topFinding: "Sin hallazgos altos; asistente resistente" },
  { host: "www.coolrevolution.net", departmentName: "Cool Revolution", web: 93, agentic: null, overall: "A", penaltyRaw: 1, agenticStatus: "no_surface", trend: "up", topFinding: "Configuración ejemplar" },
  { host: "www.bestcloudservices.com", departmentName: "Best Cloud Services", web: 94, agentic: 90, overall: "A", penaltyRaw: 0, agenticStatus: "tested", trend: "flat", topFinding: "TLS A+, CSP estricta, asistente endurecido" },
];

export const rankingFixture: RankingRow[] = SEEDS.map((s, i) => ({
  siteId: `site-${s.host.replace(/\./g, "-")}`,
  rank: i + 1,
  host: s.host,
  departmentName: s.departmentName,
  faviconUrl: `https://www.google.com/s2/favicons?domain=${s.host}&sz=64`,
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

/** The star contrast row (Fabrikam) — handy for component stories/tests. */
export const heroRow: RankingRow =
  rankingFixture.find((r) => r.host === "fabrikam.com") ?? rankingFixture[0];
