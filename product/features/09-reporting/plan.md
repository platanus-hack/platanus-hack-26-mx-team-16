---
feature: reporting
type: plan
status: pending
coverage: 0
audited: 2026-06-20
spec: ./spec.md
sources: spec.md §1–§5 (el QUÉ de esta feature); 06-data-model/plan.md §2.4/§3; 12-api/plan.md §1/§4; 05-agent-team/plan.md §6; 07-scoring/plan.md; 03-agentic-surface/plan.md; 13-frontend/plan.md
---

# Owliver — Reporte "Owliver te explica" + PDF + link público redactado — plan de implementación (CÓMO)

> El entregable medular de esta feature **no** es UI: es el **ensamblado del
> reporte** y, sobre todo, la **frontera de redacción**. Concretamente: **(1)** un
> `ReportPresenter` que compone la capa ejecutiva (grado A–F + dos sub-scores +
> párrafo Opus + top-3 + inventario agéntico) con la capa técnica (`Finding[]` en
> acordeón) a partir de lo que ya persistió el worker; **(2)** un único
> `redact_finding()` determinista que decide **qué campo de `Finding` se oculta**
> en el reporte público `/r/[token]`; **(3)** el render server-side del **PDF** y
> el shell público sin login. Lo demás (gauges, route group, tokens) ya lo poseen
> features hermanas y aquí solo se *conectan*.
>
> Principio operativo: **la redacción es Python determinista, no una preferencia
> de UI.** El reporte autenticado y el público se sirven por el **mismo use case**
> ([12-api](../12-api/plan.md) `GetPublicReport`/`GetScan`); la única diferencia es
> un flag `public: bool` que enchufa `redact_finding()`. Un link público nunca
> debe poder reejecutar el ataque contra el sitio del usuario (spec §5).

## 0. Estado de las dependencias

Esta feature se monta **al final** del grafo: necesita que el scan ya haya
corrido, scoreado y persistido. Lo que **ya existe o lo poseen otras features** y
se reutiliza tal cual (no se reinventa aquí):

- **Datos persistidos por el worker** ([06-data-model](../06-data-model/plan.md)):
  - `scans` con `web_score`, `agentic_score`, `overall_score`, `overall_grade`,
    `agentic_status`, `coverage`/`tools_status` (JSONB) — los **gauges y badges
    leen de aquí**, no recalculan ([07-scoring](../07-scoring/plan.md)).
  - `findings` (`FindingORM`): `source/severity/category/confidence`, `evidence`
    (**JSONB** — el campo que se redacta), `impact`, `remediation`, `references`,
    `dedupe_key`, `first_seen`/`last_seen` (tendencia histórica).
  - `agentic_surface` (`AgenticSurfaceORM`): inventario `type`/`vendor`/
    `location_url`/`inferred_model` para la sección "superficie agéntica detectada".
  - `public_reports` (`PublicReportORM`): `token` UNIQUE
    (`secrets.token_urlsafe(32)`), `scan_id`, `expires_at`, `revoked_at`. **La
    tabla, el índice UNIQUE y la generación del token ya son de 06** — aquí no se
    redefine; se consume.
  - Contratos congelados `src/scans/domain/contracts/finding.py`
    (`Finding`, `AgenticResult`) — definen el **shape verbatim** de un hallazgo
    crudo (spec §5.1: `source/tool/category/title/severity/cvss/confidence/
    description/evidence/affected_url/endpoint/param/impact/remediation/references`).
    **Atención al contrato congelado:** `Finding` **NO** lleva `status`, `first_seen`,
    `last_seen`, `dedupe_key` ni ids — esos viven en el **registro persistido**
    `FindingRecord`/`FindingORM` (`src/scans/.../models/finding.py`, "Finding
    persistido + ids/status/dedupe", [06-data-model](../06-data-model/plan.md) §2.4).
    Por eso **el presenter recibe el `FindingRecord` persistido, no el `Finding`
    crudo**: necesita `status`/`first_seen`/`last_seen` para la tendienia (§3.2) y un
    `getattr(finding, "first_seen")` sobre el contrato `Finding` puro **fallaría** (la
    tendencia §3.2 lee `first_seen`/`last_seen`/`status`; ver §4.1).
- **Resumen ejecutivo Opus** ([05-agent-team](../05-agent-team/plan.md) §6):
  `summary.py` ya define `ExecutiveSummary(BaseModel)` (`narrative` = párrafo
  "Owliver te explica", `top_risks: list[TopRisk]` con `title`/`severity`/
  `why_it_matters`) y `synthesize_summary(...)`. Es el **único** `output_schema`
  del producto. El worker lo persiste en `scans` (campo JSONB `summary`, ver §3.1);
  el reporte **lee** ese JSON, **no** vuelve a llamar a Opus al renderizar.
- **Endpoints HTTP** ([12-api](../12-api/plan.md) §1): `GET /scans/{id}` (detalle
  autenticado), `GET /scans/{id}/report.pdf`, `POST /scans/{id}/share`,
  `GET /r/{token}` (token inexistente→404, expirado/revocado→**410**) y los use
  cases `GetScan`/`GetScanReportPdf`/`CreatePublicShare`/`GetPublicReport`. **El
  contrato HTTP, los status codes y el ciclo de vida del token son de 12**; esta
  feature aporta el **cuerpo de presentación** (`ReportPresenter`,
  `PublicReportPresenter` con redacción) y el **render PDF** que esos use cases
  invocan.
- **Superficie de render frontend** ([13-frontend](../13-frontend/plan.md)): el
  route group, el layout `/r/[token]`, los tokens de color A–F del design system,
  y la **instalación net-new** de `accordion`, `sonner`, **`recharts`** y el
  `chart.tsx` (gauge). **Ninguno de estos existe hoy** (ver más abajo). Esta feature
  define **qué** pinta cada componente (contrato de datos), no el shell visual ni su
  instalación.
- **Infra reutilizable del fundamento SaaS** (verificada en repo):
  - **Presenter**: `Presenter[T]` (Protocol, `to_dict`) en
    `src/common/domain/interfaces/presenter.py`; convención camelCase.
  - **HTTP frontend**: `serverHttp` (`baseURL ${Settings.apiBaseUrl}/v1`) y
    `authHttp`/`localHttp` (`baseURL "/api"`) en
    `frontend/src/infrastructure/http/client.ts`; el proxy `frontend/src/proxy.ts`
    reescribe `/api/v1/*`→backend con `X-Api-Key`. El BFF es obligatorio (§5).
  - **Settings**: `backend/src/common/settings.py` — `BaseSettings` de
    pydantic-settings con `SettingsConfigDict(extra="ignore", env_ignore_empty=True,
    case_sensitive=True)`; **todos los campos tienen default**, así que **no** es
    fail-loud (un env ausente cae al default, no aborta el arranque). Aquí se añaden
    `DATA_DIR`, `STATIC_BASE_URL`, `PDF_ENGINE`, `SHARE_TTL_DAYS`, también con
    default seguro.

**Lo que NO existe hoy y esta feature (o su owner 13) debe crear:**

- *Backend (esta feature):* la **ruta estática de screenshots** de FastAPI
  (`/data/scans/{scan_id}/{n}.png`), el render PDF server-side, el
  `ReportPresenter`/`PublicReportPresenter` con `redact_finding()`.
- *Frontend net-new (instalación ownership [13-frontend](../13-frontend/plan.md);
  esta feature solo fija su contrato de datos):*
  - **`recharts`** — **NO está en `frontend/package.json` hoy** (las deps actuales
    relevantes son `next 16.1.3`, `next-intl`, `next-themes`, y `@playwright/test
    ^1.59.1` en devDependencies; **no hay recharts**). El gauge depende de
    `recharts`/`RadialBarChart`, así que `recharts` (`^3.6.0`) es **una dependencia a
    INSTALAR** vía 13, **no** "ya presente". Esto **corrige** la afirmación de la
    spec §3 y de versiones previas de este plan §2.2.
  - **`chart.tsx`** (`frontend/src/presentation/components/ui/chart.tsx`, base del
    gauge) — **NO existe**. El directorio `ui/` hoy trae `collapsible`, `badge`,
    `tabs`, `tooltip`, `scroll-area`, `skeleton`, etc., pero **no** `chart.tsx`. Es
    **net-new** (lo provee 13 junto con `recharts`).
  - **`accordion`** y **`sonner`** — tampoco están (solo `collapsible`); net-new vía
    `npx shadcn add accordion` / `sonner`.
- *Frontend (esta feature):* los componentes de reporte (página in-app autenticada +
  `/r/[token]` público) que **consumen** lo anterior.

## 1. Decisión de módulos — dónde vive el ensamblado del reporte

El reporte es **presentación derivada** del scan: no introduce tablas ni dominio
nuevos (06 ya posee `public_reports` y `findings`). Por eso su backend vive en la
capa `presentation/` del módulo `scans` (12 ya planificó ahí los endpoints), no en
un módulo nuevo:

| Pieza | Ruta | Dueño / razón |
|---|---|---|
| `ReportPresenter`, `PublicReportPresenter` | `src/scans/presentation/presenters/report.py` | Componen `scan`+`findings`+`agentic_surface`+`summary` → dict camelCase de dos capas. El público aplica `redact_finding`. |
| `redact_finding(finding, *, public) -> dict` | `src/scans/presentation/presenters/redaction.py` | **La frontera de seguridad** (§4). Python puro, determinista, testeado aislado. Único lugar que decide qué se oculta. |
| Render PDF | `src/scans/infrastructure/pdf/render.py` | `render_report_pdf(report_dict, base_url) -> bytes`. Infra (toca proceso externo / motor de render); lo invoca `GetScanReportPdf` (12). |
| Ruta estática de screenshots | mount en `backend/config/main.py` | `app.mount("/data", StaticFiles(directory=settings.DATA_DIR))`. Sirve `evidence` PNG; el PDF los embebe desde la misma URL. |
| Frontend reporte in-app | `frontend/src/presentation/views/report/` + `frontend/src/app/(protected)/scans/[id]/report/page.tsx` | Capa autenticada (evidence completa). |
| Frontend reporte público | `frontend/src/app/(public)/r/[token]/page.tsx` (server component) | Capa redactada, sin login. |
| BFF routes | `frontend/src/app/api/scans/[id]/share/route.ts`, `frontend/src/app/api/r/[token]/route.ts` | Regla obligatoria cliente→BFF→`serverHttp` (§5). |

> **Por qué un único presenter con flag `public` y no dos caminos.** Si el reporte
> público se compusiera por un camino separado, un cambio futuro en la capa
> ejecutiva podría olvidar redactar en uno de los dos. Con **una sola
> `ReportPresenter` que recibe `public: bool`** y delega cada finding a
> `redact_finding(f, public=public)`, la redacción es imposible de saltar: el
> presenter público y el autenticado comparten el 95% del código y difieren solo
> en ese flag. La regla "el link nunca filtra exploits" (spec §5) queda blindada
> por **un test del presenter público** (§6), no por disciplina.

## 2. Mapa de archivos a crear

### 2.1 Backend — presentación y render

```
backend/src/scans/
  presentation/presenters/
    report.py            # ReportPresenter, PublicReportPresenter (net-new)
    redaction.py         # redact_finding(finding, *, public) + REDACTED_FIELDS (net-new)
  infrastructure/pdf/
    render.py            # render_report_pdf(report: dict, *, base_url) -> bytes (net-new)
    template.html        # plantilla print (Jinja o f-string) capa ejecutiva+técnica
config/main.py           # + app.mount("/data", StaticFiles(...))  (edición)
src/common/settings.py   # + DATA_DIR, STATIC_BASE_URL, PDF_ENGINE, SHARE_TTL_DAYS  (edición)
```

**`ReportPresenter` — contrato de salida (dict camelCase de dos capas):**

| Bloque | Campos | Fuente |
|---|---|---|
| `executive` | `overallGrade` (A–F), `webScore`, `agenticScore` (`null` si no aplica), `narrative` (párrafo Opus), `topRisks[]` (`title`/`severity`/`whyItMatters`), `agenticSurface[]` (`type`/`vendor`/`locationUrl`), `badges[]` | `scan` + `scan.summary` (Opus) + `agentic_surface` |
| `technical` | `findings[]` (cada uno vía `redact_finding`), `filters` (severidades/sources/categorías disponibles), `trend` (nuevos/resueltos) | `findings` + dedupe a nivel site (06/08) |
| `meta` | `scanId`, `siteUrl`, `status`, `coveragePartial: bool`, `finishedAt` | `scan` |

- **Gauges**: el presenter **solo emite** `webScore`/`agenticScore`/`overallGrade`;
  la semántica del cálculo y el cap-a-C son de [07-scoring](../07-scoring/plan.md);
  el render del semicírculo es de [13-frontend](../13-frontend/plan.md). Aquí no se
  recalcula nada (principio: el LLM/render nunca escribe columnas calculadas).
- **Badges** (`badges[]`) se computan **en Python** a partir de columnas, no del
  LLM:
  - `"IA detectada, sin auditar"` ⇐ `scan.agentic_status == "detected_not_tested"`.
  - `"cobertura parcial"` ⇐ grado capado en C por cobertura (señal de 07; el
    presenter la lee de `scan.status == "partial"`; ver D4, cerrado en Opción A).
- **`PublicReportPresenter`** = `ReportPresenter(public=True)`: idéntica capa
  ejecutiva, capa técnica con `redact_finding(..., public=True)`. **No** incluye
  `meta.scanId` crudo enumerable más allá de lo necesario para el render.

### 2.2 Frontend — render del reporte (autenticado + público)

```
frontend/src/presentation/views/report/
  ReportView.tsx           # orquesta ExecutiveLayer + TechnicalLayer (net-new)
  ExecutiveLayer.tsx       # grado grande + 2 gauges + narrative + top-3 + inventario + badges
  TechnicalLayer.tsx       # Accordion de findings + filtros (severidad/source/categoría)
  FindingPanel.tsx         # 1 panel: header chip+categoría+título / body evidence|impact|remediation
  ScoreGauge.tsx           # wrapper sobre ui/chart.tsx (RadialBarChart) — 🛡️/🤖; chart.tsx + recharts son net-new (ownership 13)
  StarFinding.tsx          # tratamiento destacado del finding agéntico (§3.4)
frontend/src/app/(protected)/scans/[id]/report/page.tsx   # reporte autenticado (evidence completa)
frontend/src/app/(public)/r/[token]/page.tsx              # server component, sin login, redactado
frontend/src/app/api/scans/[id]/share/route.ts            # BFF → POST /scans/{id}/share
frontend/src/app/api/scans/[id]/report-pdf/route.ts       # BFF → GET /scans/{id}/report.pdf (stream bytes)
frontend/src/app/api/r/[token]/route.ts                   # BFF → GET /r/{token} (propaga 404/410)
```

- **Componentes base no opcionales** (spec §3) — **todos net-new, ninguno está hoy
  en el repo**; su **instalación/provisión** es ownership de
  [13-frontend](../13-frontend/plan.md), y esta feature los **consume** y fija qué
  renderizan:
  - `accordion` (`npx shadcn add accordion` — el repo trae `collapsible` pero **no**
    `accordion`).
  - `sonner` (toasts; **no** está en el repo).
  - **`recharts`** (`^3.6.0`) — **dependencia a instalar**, **NO "ya presente"**: no
    figura en `frontend/package.json` (corrige la afirmación de la spec §3). El gauge
    depende de su `RadialBarChart`.
  - `chart.tsx` (`frontend/src/presentation/components/ui/chart.tsx`), el wrapper del
    gauge sobre `RadialBarChart` — **NO existe** hoy; net-new (lo provee 13 con
    `recharts`).
  - Hoy `frontend/src/presentation/components/ui/` ya tiene `badge`, `tabs`,
    `tooltip`, `scroll-area`, `skeleton`, `collapsible` (reutilizables); **no** tiene
    `accordion` ni `chart.tsx`.
- `ScoreGauge` recibe `{score, grade, kind: "web"|"agentic"}` y, si
  `score === null` (sin superficie agéntica auditable), renderiza el badge "IA
  detectada, sin auditar" en lugar del número.

## 3. Ensamblado del reporte — qué se persiste vs. qué se compone

La regla de frontera: **se persiste lo caro/no determinista; se compone al vuelo
lo barato/derivado.** Así un re-render (in-app, PDF o `/r/[token]`) nunca vuelve a
llamar al LLM ni recalcula score.

### 3.1 Se PERSISTE (lo escribe el worker, una vez)

- **Sub-scores, grado, `agentic_status`, `coverage`** → columnas/JSONB de `scans`
  (06/07). Calculados en Python determinista por 07 **antes** de tocar la DB.
- **Resumen ejecutivo Opus** → `scans.summary` (JSONB) = el `ExecutiveSummary`
  serializado (`narrative` + `top_risks`) que produjo `synthesize_summary`
  ([05-agent-team](../05-agent-team/plan.md) §6). **Net-new columna** `summary
  JSONB nullable` en `ScanORM` — **la define y crea 06** (owner del esquema); 05
  la persiste y 09 la consume (decisión D1). Se persiste para que el
  reporte sea **idempotente y barato**: Opus corre 1 vez, el reporte se renderiza N
  veces (in-app + PDF + público) sin re-llamar a la API.
- **Findings** (`findings`) con `evidence` **completa** (incl. screenshots como
  paths `/data/scans/{id}/{n}.png`).

### 3.2 Se COMPONE al vuelo (en el presenter, por request)

- El **dict de dos capas** (§2.1): join `scan` + `findings` (orden severidad desc)
  + `agentic_surface` + `scan.summary`.
- Los **`filters`** disponibles (conjunto de severidades/sources/categorías
  presentes en `findings[]`).
- La **tendencia** (`nuevos`/`resueltos`): se deriva de `first_seen`/`last_seen`/
  `status` a nivel site (mecánica en [06-data-model](../06-data-model/plan.md) §3 y
  [08-ranking-watchlists](../08-ranking-watchlists/plan.md)); aquí solo se presenta
  (`new` si `first_seen == scan.finished_at`, `fixed` si `status == "fixed"`). **Estos
  tres campos son del `FindingRecord` persistido, no del contrato congelado `Finding`**
  (que no los tiene, §0/§4.1): el presenter opera sobre el registro, no sobre el shape
  crudo.
- La **redacción** (§4): se aplica por-finding en el presenter público; **nunca**
  se persiste una versión redactada (una sola fuente de verdad en `findings`).

### 3.3 Screenshots de `evidence` — ruta estática + PDF embebe

- FastAPI monta `/data` como `StaticFiles(directory=settings.DATA_DIR)` en
  `config/main.py`. El worker (04/05) escribe los PNG de evidencia en
  `{DATA_DIR}/scans/{scan_id}/{n}.png`.
- En el reporte **autenticado** el cliente carga la imagen vía la URL estática
  (a través del BFF/proxy si es privada — decisión D5).
- El **PDF** (§4.2) embebe la imagen **desde esa misma URL** (`base_url +
  /data/scans/...`), de modo que no se duplica el binario.
- En el reporte **público** los screenshots de evidencia que constituyan exploit
  (req/resp/payload renderizado) quedan **redactados** igual que el resto de
  `evidence` (§4): no se sirve la imagen del ataque, solo el metadato del finding.

### 3.4 El "star finding" agéntico (spec §2.3)

Cuando `finding.source == "agentic"` y el chatbot fue exitosamente
inyectado/jailbreakeado, el panel recibe tratamiento destacado (`StarFinding.tsx`):
es el clímax del pitch. Su `evidence` incluye la **prueba de canario** (que el
modelo del sitio ejecutó la instrucción inyectada). La detección y el formato del
canario son de [03-agentic-surface](../03-agentic-surface/plan.md); aquí solo se
**presenta**. En el reporte **público**, su payload de prompt-injection y el
system-prompt filtrado quedan **redactados** (§4) — se muestra "chatbot vulnerable
a prompt-injection (canario confirmado)" + impacto + remediación, **nunca** el
prompt de ataque.

## 4. La frontera de redacción — `redact_finding`

Esta es la pieza **no recortable** de la feature (spec §4.1, §5): aunque el link
público (su vehículo) sea recortable bajo presión de tiempo (M3), el
**comportamiento de redacción** define cómo se comporta el reporte al compartirse y
debe existir desde el reporte in-app.

### 4.1 Contrato

```python
# src/scans/presentation/presenters/redaction.py
from src.scans.domain.models.finding import FindingRecord   # el REGISTRO persistido,
# no el contrato crudo src/scans/domain/contracts/finding.py:Finding. FindingRecord
# (06 §2.4) = Finding + ids/status/dedupe/first_seen/last_seen; el presenter recibe
# SIEMPRE el registro persistido para poder leer los campos de tendencia (§3.2).

# Lo que SIEMPRE se muestra (público y autenticado):
SAFE_FIELDS = ("source", "category", "severity", "confidence",
               "impact", "remediation", "references", "title")

def redact_finding(finding: FindingRecord, *, public: bool) -> dict:
    """Proyecta un FindingRecord a dict camelCase. Si public=True, OMITE evidence cruda.

    La frontera: 'evidence' (payload de prompt-injection, request de sqlmap,
    system-prompt filtrado, req/resp reejecutables, screenshots del ataque)
    es lo único que se oculta. Tipo/categoría/severidad/impacto/remediación
    SIEMPRE se muestran. El link público nunca filtra un exploit reproducible.

    El parámetro es el FindingRecord PERSISTIDO, no el contrato congelado Finding:
    los campos de tendencia (status/first_seen/last_seen) que la capa técnica añade
    al dict viven solo en el registro; un getattr de esos campos sobre el Finding
    crudo fallaría. redact_finding en sí solo toca SAFE_FIELDS + affected_url +
    evidence (todos presentes en ambos), pero el contrato del presenter es el registro.
    """
    base = {f: getattr(finding, f) for f in SAFE_FIELDS}
    base["affectedUrl"] = finding.affected_url      # el sitio ya lo conoce su dueño;
                                                    # público: hostname ya es público
    if public:
        base["evidence"] = None                     # REDACTADO — no payload crudo
        base["evidenceRedacted"] = True             # bandera para la UI ("oculto")
    else:
        base["evidence"] = finding.evidence         # autenticado: evidence completa
    return base
```

- **El presenter recibe el `FindingRecord` persistido, no el contrato crudo
  `Finding`** ([06-data-model](../06-data-model/plan.md) §2.4): solo el registro
  expone `status`/`first_seen`/`last_seen` que la capa técnica usa para la tendencia
  (§3.2). El `Finding` congelado (spec §5.1) **no** tiene esos campos, así que tipar
  la frontera contra el registro evita un `getattr` que fallaría.
- **El único campo que cruza la frontera es `evidence`** (JSONB). Todo lo demás
  (`source`/`category`/`severity`/`impact`/`remediation`/`references`/`confidence`)
  es **siempre** visible: spec §5 enumera exactamente esto.
- `evidenceRedacted: true` le dice a la UI que pinte un placeholder ("Evidencia
  oculta en el reporte público") en lugar del bloque de evidencia — para que el
  destinatario entienda que hay evidencia, sin verla.
- **Donde se aplica**: `PublicReportPresenter` llama `redact_finding(f,
  public=True)`; `ReportPresenter` (autenticado) llama `public=False`. Es la
  **única bifurcación** entre ambos reportes.
- **Default seguro**: `redact_finding` es *deny-by-default* sobre `evidence` — solo
  los campos en `SAFE_FIELDS` (+ `affectedUrl` explícito) salen. Si 06 añade un
  campo nuevo al `Finding`/`FindingRecord`, **no** aparece en el público hasta que se
  agregue a `SAFE_FIELDS` a conciencia. Esto evita que un campo nuevo filtre exploit
  por descuido.

### 4.2 Render PDF — server-side (react-pdf/pdfjs fueron eliminados)

> **Decisión explícita (D2): el PDF se genera en el backend, no en el browser.**
> El frontend **eliminó `react-pdf` y `pdfjs-dist`** (confirmado en el historial
> git: `react-pdf ^10.3.0` + `pdfjs-dist 5.4.296` y sus scripts `postinstall`
> fueron removidos). No se reintroducen. El reporte ya se renderiza como HTML
> (capa ejecutiva + técnica); el PDF reusa ese mismo HTML.

- `render_report_pdf(report: dict, *, base_url) -> bytes`
  (`src/scans/infrastructure/pdf/render.py`):
  1. Renderiza `template.html` con el **mismo dict** del presenter (la versión
     **autenticada** para el dueño: `GET /scans/{id}/report.pdf` es owner-only en
     12, así que muestra evidence completa).
  2. Convierte HTML→PDF con el motor elegido por `settings.PDF_ENGINE`:
     - **Playwright print-to-PDF** (Chromium headless `page.pdf()`) — reusa
       `@playwright/test` que **ya está en `frontend/package.json`**; en backend se
       usa `playwright` python o un microservicio de print. **Plan A.**
     - **WeasyPrint** (HTML/CSS→PDF puro Python, sin navegador) — **Plan B**, más
       liviano pero CSS limitado. La spec §4 lista ambos; el flag permite cambiar
       sin tocar el caller.
  3. Embebe screenshots desde `base_url + /data/scans/{id}/{n}.png` (§3.3).
- El endpoint `GET /scans/{id}/report.pdf` (12) hace owner-check (404) y streamea
  `bytes` con `media_type="application/pdf"`. Si el scan aún está en curso (sin
  `finished_at`) → 409/425 (a confirmar con 12, su decisión D3).
- **Recortable (M3, spec §4.1)**: si el PDF se recorta, el **Plan B del demo** es
  la página in-app **con la redacción ya aplicada** — por eso `redact_finding` y el
  reporte in-app son lo imprescindible, el PDF no.

## 5. Frontend — BFF obligatorio y el shell público

Regla **obligatoria** del repo (CLAUDE.md): el browser **nunca** hace fetch directo
al backend. Toda la mecánica del reporte cumple cliente → `/api/...` → BFF route →
`serverHttp`:

- **Reporte autenticado** (`(protected)/scans/[id]/report/page.tsx`): es un
  **server component** que llama `serverHttp.get('/scans/{id}')` directamente (los
  server components y `route.ts` sí pueden usar `serverHttp`/`Settings.apiBaseUrl`).
  Pinta `ReportView` con evidence completa.
- **Compartir** (botón "Compartir"): client component → `fetch("/api/scans/{id}/share",
  {method:"POST"})` → BFF `app/api/scans/[id]/share/route.ts` (server) →
  `serverHttp.post('/scans/{id}/share', {ttlDays})` → devuelve `{token, url}`. El
  BFF inyecta cookie/`X-Api-Key`; el cliente muestra **toast `sonner`** "enlace
  generado" / errores 404/410 (spec §5.2).
- **PDF** (botón "Exportar PDF"): client → `fetch("/api/scans/{id}/report-pdf")` →
  BFF stream de bytes → `Blob` → descarga. Toast "PDF listo".
- **Reporte público** (`(public)/r/[token]/page.tsx`): **server component sin
  login** (spec §5). Llama al backend vía `serverHttp.get('/r/{token}')` **o** vía
  el BFF `app/api/r/[token]/route.ts`; renderiza la **capa ejecutiva completa** +
  la **capa técnica redactada** (`evidenceRedacted` ⇒ placeholder). Propaga los
  status del backend:
  - **404** (token inexistente) → `notFound()` (página 404 de Next).
  - **410** (expirado/revocado, lo da [12-api](../12-api/plan.md) §4) → pantalla
    **"Este enlace expiró"** (copy de spec §5.1), no la 404 genérica.
  - **200** → reporte redactado.
- El sistema visual (route group `(public)`, layout, tokens de color A–F,
  breakpoints) lo gobiernan [13-frontend](../13-frontend/plan.md) + `DESIGN.md` /
  `PRODUCT.md` (teal primario, Figtree + Geist Mono, near-flat). Esta feature
  **no** define tokens; pinta dentro de ese shell.

## 6. Suite de tests

Convención del repo: `tests/<área>/...`, pytest, librería **`expects`**, funciones
standalone, AAA, fixtures por función; frontend con **vitest/testing-library**. Los
tests de presenter son **puros** (no tocan DB: reciben entidades de dominio ya
construidas). Los tests E2E de los endpoints `/r/{token}`/`/share`/`report.pdf`
viven en [12-api](../12-api/plan.md) §8 (`tests/api/test_cancel_share.py`); aquí se
cubre **composición y redacción**.

| Archivo | Capa | Asserts |
|---|---|---|
| `backend/tests/scans/presentation/test_redaction.py` | dominio/presenter (puro) | `redact_finding(f, public=True)` ⇒ `evidence is None` y `evidenceRedacted is True`; `severity/category/impact/remediation/references/confidence` **presentes**; `public=False` ⇒ `evidence` íntegra. **Caso estrella**: un finding agéntico con payload de prompt-injection en `evidence` ⇒ el payload **no** aparece en ningún valor del dict público (assert recursivo sobre el dict). |
| `backend/tests/scans/presentation/test_redaction_deny_by_default.py` | presenter (puro) | añadir un campo sensible nuevo a `Finding` **no** lo expone en el dict público salvo que esté en `SAFE_FIELDS` (deny-by-default); `SAFE_FIELDS` no contiene `evidence`. |
| `backend/tests/scans/presentation/test_report_presenter.py` | presenter (puro) | `ReportPresenter` compone las dos capas: `executive` trae `overallGrade`/`webScore`/`agenticScore`/`narrative`/`topRisks`/`agenticSurface`; `technical.findings` ordenados por severidad desc; `badges` = `["IA detectada, sin auditar"]` cuando `agentic_status=detected_not_tested`, `["cobertura parcial"]` cuando el grado quedó capado en C; `agenticScore=null` ⇒ no se inventa número. |
| `backend/tests/scans/presentation/test_public_vs_authenticated.py` | presenter (puro) | mismo `scan`+`findings`: `PublicReportPresenter` y `ReportPresenter` producen **idéntica** capa ejecutiva; difieren **solo** en `technical.findings[*].evidence` (público=None). Blinda "un solo camino, una sola bifurcación". |
| `backend/tests/scans/infrastructure/test_pdf_render.py` | infra (mock motor) | `render_report_pdf` arma el HTML desde el dict del presenter, referencia screenshots por `base_url + /data/scans/{id}/{n}.png`, y respeta `PDF_ENGINE`; con el motor mockeado devuelve `bytes` no vacíos; falla limpio si falta `summary`. |
| `frontend/src/app/(public)/r/[token]/page.test.tsx` | frontend (vitest/RTL) | 200 ⇒ render capa ejecutiva + findings con placeholder "Evidencia oculta"; 410 ⇒ pantalla "Este enlace expiró"; 404 ⇒ `notFound()`. El payload de exploit **nunca** está en el DOM. |
| `frontend/src/presentation/views/report/ScoreGauge.test.tsx` | frontend | `score=null` ⇒ badge "IA detectada, sin auditar" en vez de número; `grade` se pinta en el `Label` central; `kind` elige 🛡️/🤖. |

## 7. Secuencia de build

1. **Settings + ruta estática**: `DATA_DIR`/`STATIC_BASE_URL`/`PDF_ENGINE`/
   `SHARE_TTL_DAYS` en `settings.py`; `app.mount("/data", StaticFiles(...))` en
   `config/main.py`. (Habilita screenshots de evidence.)
2. **`redaction.py`** (`redact_finding` + `SAFE_FIELDS`) + sus tests puros (§6).
   **Esto es lo no-recortable**; se hace y se blinda primero.
3. **`report.py`** (`ReportPresenter`/`PublicReportPresenter`) componiendo las dos
   capas desde `scan`+`findings`+`agentic_surface`+`scan.summary`; tests de
   composición y de público-vs-autenticado (§6). Requiere la columna
   `scans.summary` (D1; la define 06, la persiste 05).
4. **`pdf/render.py`** + `template.html`: HTML→PDF server-side (Plan A Playwright,
   Plan B WeasyPrint vía `PDF_ENGINE`); test con motor mockeado.
5. **Frontend in-app**: `ReportView`/`ExecutiveLayer`/`TechnicalLayer`/
   `FindingPanel`/`ScoreGauge`/`StarFinding`; instalar `accordion`+`sonner`
   (ownership 13) si aún no están. Tests de componentes.
6. **Frontend público + BFF**: `(public)/r/[token]/page.tsx` (server, 404/410/200),
   BFF routes `share`/`report-pdf`/`r/[token]`; toasts `sonner`. Test de la página
   pública (incl. assert "exploit nunca en DOM").
7. Los endpoints `/r/{token}`/`/share`/`report.pdf` (cuerpo HTTP + tokens + 410)
   los monta [12-api](../12-api/plan.md); esta feature les enchufa los presenters y
   el render.

La feature pasa a `implemented`/coverage>0 cuando: la redacción está blindada por
test, el reporte in-app renderiza las dos capas, el público sirve la versión
redactada con 404/410 correctos, y (si no se recortó en M3) el PDF se genera
server-side.

## 8. Decisiones y riesgos abiertos

1. **D1 — `scans.summary` (JSONB) persiste el `ExecutiveSummary` de Opus.**
   Resuelto: el reporte **lee** el resumen ya generado, no re-llama a Opus al
   render. La columna la **define 06** (owner del esquema) y **la persiste 05**;
   aquí se documenta su consumo. Riesgo: si 05 no la persiste, el reporte tendría que llamar a Opus por
   request (caro/no idempotente) — **bloquea**, hay que cerrarlo con 05.
2. **D2 — PDF server-side, no browser.** Resuelto: `react-pdf`/`pdfjs-dist` fueron
   eliminados del frontend (confirmado en git) y **no se reintroducen**. Motor por
   `PDF_ENGINE`: Playwright print-to-PDF (Plan A, reusa `@playwright/test` ya
   presente) o WeasyPrint (Plan B). Riesgo: Playwright en backend añade un Chromium
   pesado al contenedor; WeasyPrint es liviano pero su CSS es limitado y el reporte
   tiene gauges (SVG) — evaluar fidelidad antes de fijar el default.
3. **D3 — Redacción = `evidence` y solo `evidence`.** Resuelto y blindado: la
   frontera es deny-by-default sobre `SAFE_FIELDS`; el único campo que se oculta en
   público es `evidence` (payload/req-resp/system-prompt/screenshots del ataque).
   Tipo/categoría/severidad/impacto/remediación/refs siempre visibles (spec §5).
   Esto **no es recortable** aunque el link público sí lo sea (spec §4.1).
4. **D4 — Señal de "cobertura parcial" (cap a C).** **Cerrado (Opción A):** el
   presenter deriva el badge de `scan.status == "partial"` (06 persiste `status`
   como enum de primera clase; 07 ya capa el grado a C y `meta.coveragePartial` se
   computa de `scan.status`). **No** se añade `coverage_capped`: sería redundante
   con `status` y divergiría de 08/13, que ya usan `status=='partial'`.
5. **D5 — Screenshots privados.** Abierto: `/data` como `StaticFiles` es público;
   para scans `private` los screenshots de evidence no deben ser servibles sin
   auth. Opción: servir `/data/scans/{id}/...` solo a través de un endpoint con
   owner-check (no `StaticFiles` directo) para privados, y directo para públicos
   ya redactados (que no sirven screenshots de exploit en absoluto). A coordinar
   con 12 (AuthZ) y 04 (dónde escribe el worker).
6. **D6 — Token y 410 son de 12, no de aquí.** El ciclo de vida del token
   (`token_urlsafe(32)`, TTL 7d default, `revoked_at`, UNIQUE) lo poseen 06
   (tabla/índice) y 12 (endpoint/410). Esta feature **consume** el token y solo
   define la **semántica de redacción** del reporte que ese token sirve. Riesgo
   nulo si 12 cumple el contrato de 404/410.
