# Consistency review — `product/design-prompt.md` vs subspecs

> Auditoría multi-agente (14/14 auditores + crítico transversal). **112 hallazgos** — 20 high · 45 medium · 47 low.

Documento bajo revisión: `product/design-prompt.md` (brief de UI). Fuente autoritativa: cada subspec. "Fix" = qué archivo cambiar.

> **Nota de verificación (revisión manual sobre la salida cruda).** Las 112 filas
> de abajo son la salida sin filtrar de los 14 auditores + crítico. Tras
> verificar contra los specs, esta sección de arriba prioriza lo **real** y marca
> los **falsos positivos**. Si hay conflicto, manda esta sección.

## ✅ Estado de aplicación (correcciones ya aplicadas)

Tras la verificación, se aplicaron estos cambios (ver `git diff`):

**`design-prompt.md` (brief alineado a specs cerrados):**
- §3.2 — `.gob.mx` + activo pasa a advertencia **no bloqueante** (botón habilitado
  tras atestar); se eliminó el bloqueo/error inline. (#A1)
- §3.1 / §3.4 / §3.9 — **un solo** grado letra A–F (`overall_grade`); las dos
  dimensiones muestran **sub-score numérico 0–100**. Fila SAT reescrita a
  *"grado E · web 68 / agéntico 24"*. (#A2)
- §3.3 — los dos carriles se anotan como coordinados por el **orquestador Opus**. (#A3)
- §3.1 — leaderboard incluye cualquier scan pasivo (gov = framing héroe); badge
  "cobertura parcial" anota el **cap en C**; copy añade **Shodan**. (#B8, #B7, edit.)
- §3.2 — micro-copy de registro de consentimiento; §3.7 — rutas de auth añadidas.

**Specs extendidos / reconciliados:**
- **#A1 propagado a TODA la cadena** (gov activo = no bloqueante, solo refuerza
  copy + resultado privado): `01-legal-ethics` (ya lo decía) + `01-legal-ethics/plan.md`
  (marcado **RESUELTO 2026-06-20**) + `12-api` (eliminado el `is_gov→422`; el único
  422 es atestación faltante) + `02-attack-levels` §4 (gov activo por usuario atestado
  **sí** recibe tools activas) + `13-frontend` §F (L137/142/254: copy no bloqueante,
  422 = atestación) + `product/spec.md` (L197/243: "gate de atestación", no `is_gov→422`).
  `02-attack-levels` §3.1 — básico marcado *anónimo, sin permisos*.
- `10-realtime-live-view` §2 — añadido campo **`progress?` 0–100** (barra del
  theater); `done` documenta `outcome: success | cancelled`. (#B6, cancel)
- `12-api` — añadido **`PATCH /watchlist/{id}` `{monitor}`** (toggle de monitoreo). (#B4)

**Resultaron NO ser gaps (verificado):** tendencia ▲▼ + histórico (computable de
`scans` por fecha + `findings.first_seen/last_seen`); cancelación (ya respaldada
por `scans.status=cancelled` + `POST /scans/{id}/cancel` + `done{outcome}`); tokens
de color / escala A–F / SOC / radio (definidos en `13-frontend §F2`, no en el
boilerplate Doxiq que miró el auditor).

**✅ Decisiones abiertas — RESUELTAS y aplicadas (2026-06-20):**
- **Preferencias de canal de alerta → por-usuario (global).** Nuevo
  `notification_prefs(user_id PK, email_enabled DEFAULT true, slack_webhook_url NULL,
  updated_at)` en `06-data-model` §3.6 (el email al owner siempre, Slack opcional);
  endpoints `GET/PUT /me/alerts` en `12-api`; `08-ranking-watchlists` §5.1 ata los
  canales a esas prefs; brief §3.8 aclara "a nivel cuenta".
- **Grados por dimensión → letra display-only.** `07-scoring` §5.1/§6: se deriva un
  grado-letra por dimensión aplicando las **mismas bandas** a `web_score`/`agentic_score`,
  **solo para display** (no se persiste ni ordena); `overall_grade` sigue siendo el
  único autoritativo. Brief §3.1/§3.4/§3.9 restauran "🛡️ C web / 🤖 F agéntico"
  (ej. web 72→C / agéntico 24→F / global E).

## ⭐ Inconsistencias reales (verificadas, priorizadas)

### A) El brief contradice un spec ya cerrado → corregir `design-prompt.md`

1. **[ALTA] `.gob.mx` + activo NO debe bloquearse.** El brief §3.2 dice que el
   activo sobre `.gob.mx` está *"prohibido; solo se permite pasivo"* con un error
   inline bloqueante. Los specs lo contradicen: `01-legal-ethics` §1 declara
   **descartada** la propuesta `is_gov → 422 hard` y §2.4 dice *"el usuario **puede
   proceder** bajo su responsabilidad… refuerzo **no bloqueante**"*; `02-attack-levels`
   §3 permite activo sobre cualquier URL detrás del gate. → Cambiar el brief: el
   botón queda **habilitado** tras atestar; la advertencia gov es enfática pero
   no-bloqueante. *(Ojo: los specs entre sí no están del todo reconciliados —
   `02-attack-levels` §4 L98 dice que a un target gov el `owasp_agent` solo recibe
   tools pasivas; alinear esa frase con `01-legal-ethics` §2.4.)*

2. **[ALTA] Grado por dimensión.** El brief muestra **dos grados-letra** ("C web /
   F agéntico" §3.1; "grado al centro" de cada gauge §3.4). `07-scoring` §5.1/§6
   define **un solo** `overall_grade` derivado del `overall_score`; las dimensiones
   tienen sub-score numérico 0–100, **no** letra. → Decisión de producto: o el brief
   muestra número por gauge + **una** letra global, o `07-scoring` añade grados por
   dimensión (el contraste "C web / F agéntico" es buen gancho — quizá conviene
   extender el spec).

3. **[MEDIA] No se ve el orquestador.** El brief §3.3 modela el equipo como **dos
   carriles**. `05-agent-team` define un **Team de 3**: Opus orquestador + 2
   subagentes Sonnet. → Decidir si el orquestador tiene presencia visible (un 🦉
   coordinador / header) o es invisible por diseño; documentarlo.

### B) El brief expone un hueco en un spec → extender el spec (o recortar el brief)

4. **[ALTA] Alertas de watchlist + toggle de monitoreo sin API.** El brief §3.8
   pide *"ajustes de alertas (email / Slack)"* y activar monitoreo por fila.
   `12-api` solo tiene `GET/POST/DELETE /watchlist` (monitor solo se fija al crear,
   sin canales de alerta). → Añadir endpoints (`PATCH /watchlist/{id}`, config de
   alertas) o recortar el brief.

5. **[MEDIA] Tendencia de grado (▲▼) + gráfico histórico** (§3.1, §3.6) sin
   respaldo en `06-data-model` (no hay puntero al scan previo ni delta). → Computar
   tendencia (query del scan anterior por sitio) o persistir delta.

6. **[MEDIA] Barra de progreso 0–100** (§3.3): el esquema de eventos de
   `10-realtime-live-view` tiene `phase` con mensaje pero **sin** campo numérico de
   progreso. → Añadir progreso numérico al evento o cambiar el brief a solo-fase.

7. **[MEDIA] Cap de "cobertura parcial" en C** no está en el brief. `07-scoring`
   §5.1 capa el grado en **C** con `status=partial` y **nunca** muestra A. El brief
   menciona el badge pero no el cap. → Añadir al brief que las filas parciales no
   pueden mostrar A/B.

8. **[MEDIA] Alcance del leaderboard.** El brief lo enmarca como **solo `.gob.mx`**;
   `08-ranking-watchlists` dice que cualquier scan pasivo de usuario entra también
   al ranking global. → Aclarar en el brief (gov es el framing héroe, no el filtro).

### C) Bajas / editoriales
- **Cancelar (live-view):** el brief tiene "Cancelar (mata el escaneo)" + estado
  `cancelado`. El *evento* SSE no tiene `cancel`, **pero** sí está respaldado:
  `06-data-model` tiene `scans.status=cancelled` y `12-api` `POST /scans/{id}/cancel`.
  → Solo falta una señal terminal de cancelación en el stream; menor.
- **Rutas de auth:** las 4 pantallas del brief §3.7 no citan rutas; `13-frontend`
  §F3 sí (`/login`, `/login/check-email`, `/auth/callback`). No es contradicción
  (el brief es visual); opcional añadir refs.
- **Shodan** omitido en el copy *"equivalente a Observatory / SSL Labs"* (los specs
  citan también Shodan). Editorial.
- **Taxonomía LLM01–LLM10:** el brief la usa como eje de categorías; `03-agentic-surface`
  solo mapea LLM01/LLM02/LLM06. Consistente a nivel UI (`13-frontend` L162 también
  usa LLM01–LLM10); nota: el motor solo emite un subconjunto hoy.
- **"anónimo, sin permisos"** en Básico (§3.2) no está en `02-attack-levels`; gap menor.

## ⚠️ Falsos positivos (NO son inconsistencias — el auditor miró el archivo equivocado)

- **Tokens de color, escala A–F, paleta SOC, radio** (filas product-overview
  H13/H14/H15 abajo): el auditor los comparó contra `DESIGN.md`/`globals.css` (que
  siguen siendo el boilerplate **"Doxiq"**). El dueño real es **`13-frontend §F2`**,
  que define **exactamente** los mismos valores: `--ow-accent: oklch(0.78 0.15 75)`
  (coincide al dígito con el ámbar del brief), la paleta SOC (`--soc-bg/grid/live/tool/hit`),
  la escala A–F y `--radius 0.75rem`. **`design-prompt.md §2` es consistente con `13-frontend`.**
- **Único residual real (no es del brief):** los archivos raíz `DESIGN.md` /
  `globals.css` aún están marca **Doxiq**, sin los tokens Owliver/SOC/grados. Es
  boilerplate sin re-brandear, no una divergencia brief↔spec.

---

## Resumen (excluye notas de alineación)

| # | Sev | Tipo | Dominio | Hallazgo |
|---|-----|------|---------|----------|
| 1 | high | contradiction | 01-legal-ethics | Para hosts .gob.mx el brief afirma que el escaneo activo está PROHIBIDO y solo se permite pasiv… |
| 2 | high | drift | 03-agentic-surface | The brief uses the full LLM01-LLM10 OWASP-for-LLM taxonomy as the category set for agentic find… |
| 3 | high | gap-in-prompt | 05-agent-team | Brief models the agent team as exactly two lanes side-by-side ("Dos carriles de agente lado a l… |
| 4 | high | gap-in-spec | 06-data-model | Brief §3.1 (Leaderboard rows) and §3.6 (Histórico del sitio: 'gráfico de tendencia del grado', … |
| 5 | high | contradiction | 07-scoring | Brief §3.4 Capa 1 specifies 'dos gauges semicirculares: 🛡️ Web y 🤖 Agéntico, con el score num… |
| 6 | high | gap-in-prompt | 08-ranking-watchlists | The brief frames the Hall of Shame leaderboard exclusively as a ranking of .gob.mx government s… |
| 7 | high | gap-in-prompt | 08-ranking-watchlists | The brief §3.1 lists a 'cobertura parcial' badge but never states that partial-coverage rows ha… |
| 8 | high | contradiction | 10-realtime-live-view | The Theater defines a 'cancelado' state and a 'Botón Cancelar (mata el escaneo)' that kills the… |
| 9 | high | gap-in-spec | 10-realtime-live-view | Theater header shows a 'barra de progreso 0–100 con fase legible' — a numeric 0-100 progress ba… |
| 10 | high | gap-in-spec | 12-api | El brief §3.8 exige un control de alertas: "Ajustes de alertas (email / Slack)" en la watchlist… |
| 11 | high | gap-in-spec | 12-api | El brief §3.8 exige un "toggle de monitoreo (re-escaneo periódico)" por dominio que el usuario … |
| 12 | high | gap-in-prompt | 13-frontend | The brief describes the magic-link auth flow as 4 screens (1. Pedir email, 2. 'Revisa tu correo… |
| 13 | high | contradiction | product-overview | design-prompt §2 introduces an amber/gold accent "los ojos del búho" oklch(0.78 0.15 75) used "… |
| 14 | high | drift | product-overview | design-prompt §2 gives the amber accent the value oklch(0.78 0.15 75). |
| 15 | high | gap-in-spec | product-overview | design-prompt §2 defines a full A–F grade color scale (A oklch(0.72 0.16 150), B oklch(0.75 0.1… |
| 16 | high | drift | product-overview | design-prompt is fully Owliver-branded (owl mascot 🦉 with 3 states 'dormido/vigilando/alerta' … |
| 17 | high | contradiction | cross-cutting | Brief §3.2: gob.mx + active level is BLOCKED — reinforced red warning 'el escaneo activo automá… |
| 18 | high | contradiction | cross-cutting | Brief §3.3 defines a 'cancelado' Theater state and 'Botón Cancelar (mata el escaneo)'. The 10-r… |
| 19 | high | drift | cross-cutting | The product-overview auditor raised SIX findings (amber not a token / amber value drifts / A-F … |
| 20 | high | contradiction | cross-cutting | Brief §3.4/§3.1 show per-dimension letter grades — 'dos gauges … con el score numérico + grado … |
| 21 | medium | drift | 01-legal-ethics | El copy de defensa legal del leaderboard cita 'equivalente a Mozilla Observatory / SSL Labs. No… |
| 22 | medium | gap-in-spec | 01-legal-ethics | El brief exige que el reporte público (/r/[token]) renderice findings técnicos con los exploits… |
| 23 | medium | gap-in-spec | 02-attack-levels | Brief §3.2 describes Básico with attributes 'anónimo, sin permisos' ('Básico — pasivo, no intru… |
| 24 | medium | gap-in-prompt | 02-attack-levels | Brief §3.2 / §4.2 treats the attestation gate as a single boundary triggered by 'nivel activo' … |
| 25 | medium | gap-in-prompt | 02-attack-levels | Brief never surfaces that automatic/seeded scans (the Hall of Shame ranking in §3.1, populated … |
| 26 | medium | drift | 03-agentic-surface | The brief names the Agentic Surface Auditor lane phases as exactly 'detección → inventario → so… |
| 27 | medium | contradiction | 03-agentic-surface | The brief presents the star finding as a single technique: 'El finding agéntico estrella: syste… |
| 28 | medium | gap-in-prompt | 03-agentic-surface | The brief surfaces confidence as a generic per-finding attribute only: 'nivel de confianza' lis… |
| 29 | medium | contradiction | 04-scanning-engine | The OWASP Scanner agent lane lists tool chips as "(nuclei, zap, testssl, nikto, sqlmap…)". The … |
| 30 | medium | gap-in-prompt | 04-scanning-engine | The OWASP Scanner chip row enumerates only "nuclei, zap, testssl, nikto, sqlmap…" (5 chips with… |
| 31 | medium | contradiction | 04-scanning-engine | The Live Pentest Theater header shows a generic timer that "tranquiliza: '< 90s'", implying eve… |
| 32 | medium | gap-in-prompt | 05-agent-team | Brief §3.4 Report shows the "Owliver te explica" plain-language paragraph + Top 3 riesgos as st… |
| 33 | medium | drift | 05-agent-team | Brief §3.3 OWASP lane shows tool chips "nuclei, zap, testssl, nikto, sqlmap…" — the named examp… |
| 34 | medium | gap-in-prompt | 05-agent-team | Brief §3.3 gives the OWASP lane a row of tool chips that light up/turn off, but gives the Agent… |
| 35 | medium | drift | 06-data-model | Brief §3.3 OWASP Scanner tool chips list 'nuclei, zap, testssl, nikto, sqlmap…' and §2 telemetr… |
| 36 | medium | gap-in-spec | 06-data-model | Brief §3.4 Capa 2 requires references rendered as 'CWE/OWASP' refs, and §3.4 lists 'nivel de co… |
| 37 | medium | gap-in-prompt | 06-data-model | Brief §3.4 Capa 2 accordion header is 'chip de severidad + categoría OWASP/LLM + título' and of… |
| 38 | medium | gap-in-prompt | 07-scoring | Brief §3.4 shows two gauges 🛡️ Web + 🤖 Agéntico and §3.1 a 'Doble medidor lado a lado: 🛡️ We… |
| 39 | medium | gap-in-prompt | 07-scoring | Brief §3.1 lists 'cobertura parcial' only as a row badge (line 113) and §3.3/§3.4 as a banner/b… |
| 40 | medium | gap-in-spec | 07-scoring | Brief §2 Motion (lines 86-88) and §3.1/§3.4 require numeric scores presented as count-up grades… |
| 41 | medium | gap-in-spec | 08-ranking-watchlists | The brief §3.1 specifies three leaderboard filters: 'por grado, por peor dimensión (web/agéntic… |
| 42 | medium | gap-in-spec | 08-ranking-watchlists | The brief §3.1 specifies a per-row 'Doble medidor lado a lado: 🛡️ Web vs 🤖 Agéntico', with a … |
| 43 | medium | drift | 08-ranking-watchlists | The brief §3.1 designs only a single combined trend arrow per row ('Valor de penalización cruda… |
| 44 | medium | drift | 09-reporting | Brief §3.4 (Capa 2 técnica) lists the finding filters as 'Filtros por severidad / dimensión / c… |
| 45 | medium | drift | 09-reporting | Brief §3.5 says the public report shows 'tipo, severidad, impacto, remediación' for technical f… |
| 46 | medium | gap-in-prompt | 09-reporting | Brief §3.4/§3.5 list Export PDF and Share actions but never specify toast feedback for them or … |
| 47 | medium | gap-in-prompt | 10-realtime-live-view | The brief never names the realtime transport; §3.3 only says 'diséñalo asumiendo replay' and li… |
| 48 | medium | drift | 10-realtime-live-view | design-prompt §4.3 (flujo 'Ver el ataque en vivo + recargar') states reload repaints 'completo … |
| 49 | medium | gap-in-prompt | 11-auth-magic-link | design-prompt §4.2 'Escaneo activo con atestación' only shows the level 'Avanzado' triggering t… |
| 50 | medium | gap-in-prompt | 11-auth-magic-link | design-prompt §3.7 screen 3 ('Verificando') defines exactly three callback states: 'verificando… |
| 51 | medium | gap-in-spec | 11-auth-magic-link | design-prompt §3.7 screen 2 ('Revisa tu correo') requires a 'cooldown visible' — i.e. the UI mu… |
| 52 | medium | gap-in-spec | 12-api | El brief §3.1 especifica tres filtros en el leaderboard: "por grado, por peor dimensión (web/ag… |
| 53 | medium | gap-in-spec | 12-api | El brief §3.2 muestra el "host detectado" al validar la URL y §3.3 muestra el chatbot detectado… |
| 54 | medium | drift | 12-api | El brief §3.5 describe el reporte público /r/[token] con dos estados de error: link inexistente… |
| 55 | medium | gap-in-prompt | 13-frontend | The brief's component inventory (§6) lists 9 reusable components: GradeBadge, SeverityChip, Gau… |
| 56 | medium | gap-in-spec | product-overview | design-prompt §2(B) defines a dark 'Live-view / theater / SOC war-room' palette (near-black okl… |
| 57 | medium | drift | cross-cutting | Four auditors raised 'cobertura parcial' findings as if undefined/one-dimensional: 08-ranking (… |
| 58 | medium | drift | cross-cutting | Several auditors raised brief 'gaps' actually covered by 13-frontend (the surface spec) but che… |
| 59 | medium | contradiction | cross-cutting | ORPHAN flagged by 09-reporting auditor (LOW gap-in-spec): the Report Card / OG share image (bri… |
| 60 | medium | contradiction | cross-cutting | Brief §3.4 finding-panel filters are 'por severidad / dimensión / categoría' (line 188). The 09… |
| 61 | medium | drift | cross-cutting | Brief §6 lists report public-error states as '404/410/422'. Both 06-data-model and 09-reporting… |
| 62 | medium | drift | cross-cutting | Brief §3.3/§3.4 chips/panels use the full taxonomy '(OWASP A01–A10 / LLM01–LLM10)'. The 03-agen… |
| 63 | medium | drift | cross-cutting | INTERNAL design-prompt contradiction: §2/§3.1 make the PRIMARY CTA amber ('CTA primario (ámbar)… |
| 64 | medium | gap-in-prompt | cross-cutting | INTERNAL design-prompt inconsistency: §6 'Entregables' names exactly 9 reusable components but … |
| 65 | medium | drift | cross-cutting | INTERNAL design-prompt inconsistency on active-level→session trigger. §4 flow 2 names ONLY 'Ava… |
| 66 | low | gap-in-prompt | 01-legal-ethics | El gate de atestación del brief (§3.2) muestra checkbox de autorización + 'aceptar términos', p… |
| 67 | low | terminology | 02-attack-levels | Brief consistently labels the levels 'Básico / Intermedio / Avanzado' (and §3.2 line 125 'Básic… |
| 68 | low | gap-in-prompt | 03-agentic-surface | The brief shows two agentic-surface badges for detected-but-not-tested coverage: 'IA detectada,… |
| 69 | low | gap-in-spec | 03-agentic-surface | The brief introduces a 'cobertura parcial' badge/state shown on ranking rows (§3.1), in the rep… |
| 70 | low | terminology | 03-agentic-surface | The brief shows the no-model-detected label as 'modelo no expuesto' (§3.4: 'modelo inferido o "… |
| 71 | low | drift | 04-scanning-engine | Tool chips have three states: encendido (ámbar, pulsando) while running; apagado verde = ok; ro… |
| 72 | low | terminology | 04-scanning-engine | Brief uses the chip labels "testssl" and "zap". |
| 73 | low | gap-in-spec | 04-scanning-engine | Brief §3.3 specifies two phase labels for the progress bar ("Detectando tecnologías…", "Sondean… |
| 74 | low | drift | 05-agent-team | Brief §3.3 describes the Agentic lane phases as "detección → inventario → sondas". |
| 75 | low | terminology | 06-data-model | Brief §3.1 leaderboard row uses the badge label 'cobertura parcial' and a separate scan state '… |
| 76 | low | gap-in-prompt | 06-data-model | Brief §3.5 designs the public link states 'inexistente → 404' and 'expirado/revocado → Este enl… |
| 77 | low | terminology | 07-scoring | Brief §3.1 calls the tie-break/leaderboard value 'Valor de penalización cruda' (line 114) and p… |
| 78 | low | gap-in-prompt | 07-scoring | Brief §3.1 row spec (lines 107-114) shows position + overall grade + dual gauges + raw penalty,… |
| 79 | low | drift | 08-ranking-watchlists | The brief §6 deliverables require an empty state for every screen ('Estados de cada pantalla: l… |
| 80 | low | gap-in-spec | 09-reporting | Brief §3.9 specifies a shareable 'Report Card' image (boletín de calificaciones: grado A–F + me… |
| 81 | low | drift | 09-reporting | Brief §3.5 maps states as 'link inexistente → 404; link expirado/revocado → pantalla "Este enla… |
| 82 | low | gap-in-prompt | 09-reporting | Brief §3.4 presents 'Exportar PDF · Compartir' as firm, always-present report actions with no f… |
| 83 | low | gap-in-spec | 10-realtime-live-view | Theater defines an 'en cola (🦉 dormido)' queued state shown before the scan is running (design… |
| 84 | low | gap-in-prompt | 11-auth-magic-link | design-prompt has no logout UI or session/account indicator anywhere; §3.7's four screens cover… |
| 85 | low | gap-in-prompt | 11-auth-magic-link | design-prompt §3.7 is the only screen group that gives NO route paths (every other §3 section n… |
| 86 | low | terminology | 12-api | El brief §3.2 nombra el control legal como "Checkbox obligatorio: Declaro tener autorización pa… |
| 87 | low | gap-in-prompt | 12-api | El brief §3.2 dice que para gov + nivel activo se muestra un error inline "Los sitios gob.mx so… |
| 88 | low | gap-in-prompt | 12-api | El brief §3.2 trata el envío como un solo resultado: "al enviar → redirige a la pantalla de esc… |
| 89 | low | terminology | 13-frontend | The brief names the scan progress component generically: 'barra de progreso de escaneo' (§6) / … |
| 90 | low | drift | 13-frontend | The brief lists OWASP theater tool chips as 'nuclei, zap, testssl, nikto, sqlmap…' (§3.3) and t… |
| 91 | low | gap-in-prompt | 13-frontend | The brief's scan form (§3.2) only sketches the gate appearing 'SOLO si el nivel es activo' and … |
| 92 | low | drift | product-overview | design-prompt §2 states 'Radio base ~12px' and components imply ~12px corners across cards/badg… |
| 93 | low | drift | cross-cutting | ORPHAN copy/number: brief §3.1 hero counter '128 sitios auditados · 41 reprobados (grado F)' — … |
| 94 | low | drift | cross-cutting | ORPHAN: brief §3.3 timer copy '< 90s' (a general 'tranquiliza' timer). The 04-scanning auditor … |
| 95 | low | gap-in-spec | cross-cutting | ORPHAN: brief §2 OwlMascot with three states (dormido/vigilando/alerta), listed in §6 as a deli… |
| 96 | low | terminology | cross-cutting | DEDUP/severity note: the legal-ethics auditor's finding #2 (LOW drift) says the leaderboard leg… |

---

## Detalle por dominio

### 01-legal-ethics

#### ❌ Contradicción · **high**
- **Ubicación:** design-prompt §3.2 (gate de atestación, viñeta '.gob.mx') vs spec §1 (párrafo 'descartada') y §2.4 (líneas 96-102)
- **Brief:** Para hosts .gob.mx el brief afirma que el escaneo activo está PROHIBIDO y solo se permite pasivo: advertencia reforzada en rojo 'Sitio del Estado: el escaneo activo automático está prohibido; solo se permite pasivo' y, para gov + activo, un error inline bloqueante 'Los sitios gob.mx solo admiten escaneo pasivo.' (implica que el usuario NO puede lanzar activo sobre gob.mx).
- **Spec:** El spec dice lo contrario: §2.4 'Advertencia reforzada (no bloqueo) para dominios sensibles' — la advertencia es más enfática (copy en rojo) pero 'el usuario **puede proceder** bajo su responsabilidad. Es un refuerzo **no bloqueante**'. §1 declara explícitamente DESCARTADA la propuesta de bloquear gov con 'is_gov → 422 hard'. is_gov solo afecta el copy y la visibilidad por defecto, NO la posibilidad de lanzar el activo.
- **Fix:** Corregir product/design-prompt.md §3.2: el activo sobre .gob.mx NO debe bloquearse. Eliminar el error inline bloqueante 'Los sitios gob.mx solo admiten escaneo pasivo.' y cambiar el copy reforzado a uno enfático pero no-bloqueante (p. ej. 'Sitio del Estado: el escaneo activo es de tu entera responsabilidad legal; por defecto solo publicamos resultados pasivos.'). El botón debe permanecer habilitado tras atestar. La restricción 'solo pasivo' aplica al ranking público (§2.3) y a los disparos automáticos (§2.2), no al usuario que atesta.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.1 (micro-copy de defensa legal) vs spec §2.2 (línea 74) y §3 (líneas 137-139)
- **Brief:** El copy de defensa legal del leaderboard cita 'equivalente a Mozilla Observatory / SSL Labs. No intrusivo.' (§3.1), omitiendo Shodan.
- **Spec:** El spec ancla la defensa legal del ranking gov en 'equivalente a lo que hacen públicamente Mozilla Observatory / SSL Labs / Shodan' (§2.2, §3, líneas 73-74 y 137-139). Shodan es parte explícita del paralelo.
- **Fix:** Decisión editorial: si se busca fidelidad al spec, ampliar el copy del leaderboard en product/design-prompt.md §3.1 a 'equivalente a Mozilla Observatory / SSL Labs / Shodan'. Si se mantiene la omisión por concisión de UI, anotarlo en el spec; no es un error de UI pero el set de referencias diverge.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.5 (reporte público, payload redactado) vs spec §2.3 (líneas 84-94) — no cubierto
- **Brief:** El brief exige que el reporte público (/r/[token]) renderice findings técnicos con los exploits redactados/ocultos — 'muestra tipo, severidad, impacto, remediación; **nunca** el payload crudo', con un estado visual 'exploit redactado' (candado + 'Oculto en el reporte público').
- **Spec:** El spec de legal-ethics §2.3 solo establece que el ranking público muestra únicamente resultados pasivos y que un activo de usuario es privado salvo que genere link público explícito (/r/{token}). NO define ninguna regla de redacción/ocultamiento del payload crudo en el reporte público. La redacción del exploit es una invariante legal/ética relevante que el spec no cubre (puede vivir en 08-ranking-watchlists o 12-api, pero no está fijada como contrato legal).
- **Fix:** Extender product/features/01-legal-ethics/spec.md (o referenciar explícitamente la feature dueña) para fijar el invariante: en cualquier reporte público (/r/{token}) el payload crudo del exploit NUNCA se expone; solo tipo/severidad/impacto/remediación. Hoy el brief asume una regla legal que el spec no respalda.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.2 (gate de atestación) y §4 flujo 2 vs spec §2.1 (líneas 51-58)
- **Brief:** El gate de atestación del brief (§3.2) muestra checkbox de autorización + 'aceptar términos', pero no comunica que el consentimiento se registra/persiste ni con qué identidad.
- **Spec:** El spec §2.1 exige persistir 'authorized=true' + 'authorized_at' + 'requested_by' en la tabla scans, y que 'Sin consentimiento el job no se encola'. El flujo §4.2 del brief sí enruta a magic-link 'si no hay sesión', lo cual es consistente con requested_by, pero el gate no deja claro que la atestación queda registrada a nombre del usuario autenticado.
- **Fix:** Opcional pero recomendable: añadir en product/design-prompt.md §3.2 un micro-copy de responsabilidad/registro (p. ej. 'Esta autorización quedará registrada a tu nombre y con fecha.') para que el diseño refleje que el consentimiento es un registro persistido, no un checkbox de honor (spec §2.1 / §5).

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.2 vs spec §2.1 (líneas 53-58)
- **Brief:** El brief reproduce literalmente el copy legal nuclear: advertencia '...hacerlo sin autorización es ilegal' y checkbox 'Declaro tener autorización para auditar este dominio.', y muestra el gate SOLO para niveles activos.
- **Spec:** Coincide exacto con spec §2.1 (líneas 53-57): misma advertencia con {host}, mismo checkbox, gate 'para activos'. Alineación fuerte del control legal central.
- **Fix:** Mantener este copy literal en ambos docs; cualquier cambio futuro de wording debe sincronizarse entre product/design-prompt.md §3.2 y product/features/01-legal-ethics/spec.md §2.1.

### 02-attack-levels

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.2 line 125; spec.md §3.1 lines 50-52, §2 line 34
- **Brief:** Brief §3.2 describes Básico with attributes 'anónimo, sin permisos' ('Básico — pasivo, no intrusivo, anónimo, sin permisos. (default)') that the level card must display as plain-language copy.
- **Spec:** Spec §3.1 defines básico as 'pasivo, no intrusivo' and as 'el único que Owliver dispara sin un humano atestando', but never characterizes it as 'anónimo' or 'sin permisos'. The 'no requires login / no ownership verification' framing is implied (§2: 'sin verificación de propiedad del dominio') but the user-facing 'anónimo / sin permisos' descriptors are not stated as level attributes.
- **Fix:** Extend product/features/02-attack-levels/spec.md §3.1 to explicitly state básico is anonymous (no login required) and requires no permission/ownership, so the UI card copy ('anónimo, sin permisos') has an authoritative source. Otherwise the designer's copy is unverifiable against the spec.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.2 lines 126-128; spec.md §3.2 (lines 62-73), §3.3 (lines 75-83), §6 (lines 106-116)
- **Brief:** Brief §3.2 / §4.2 treats the attestation gate as a single boundary triggered by 'nivel activo' and does not distinguish Intermedio vs Avanzado in tool intensity, robots.txt handling, or the ~8-min budget; level cards only show one line of plain-language copy each.
- **Spec:** Spec §3.2 vs §3.3 / §6 differentiate the two active levels substantively: Intermedio = active suave/rate-limited (ZAP baseline, Nikto, katana, ffuf/gobuster, CORS/cookie/clickjacking) while Avanzado = explotación (ZAP full active + Nuclei fuzzing + sqlmap over 1 known param, budget ~8 min). Spec §8.4 also notes both are 'nunca automáticos'.
- **Fix:** Extend design-prompt §3.2 so the Intermedio and Avanzado level cards convey their distinct intensity (e.g. Intermedio = spider/crawl/dir-enum suave; Avanzado = explotación dirigida, sqlmap, ~8 min) rather than a single generic line each, so the UI communicates the escalating-intrusiveness ladder the spec mandates.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.1 (lines 98-117) and §3.2; spec.md §2 line 36, §3.1 line 52, §8.3 line 135
- **Brief:** Brief never surfaces that automatic/seeded scans (the Hall of Shame ranking in §3.1, populated 'desde el segundo cero') are restricted to passive/Básico only — the leaderboard cards just show grades without indicating the scan was forcibly passive.
- **Spec:** Spec §2 (line 36) and §3.1 (line 52) and §8.3 state básico is 'el único camino automático' and that 'los escaneos automáticos (seed/cron del ranking gov) son SOLO pasivos'. The public gov ranking is therefore always a passive/básico result.
- **Fix:** Extend design-prompt §3.1 to note the Hall of Shame grades come from passive/Básico scans only (e.g. a 'medido en modo pasivo' label or tooltip), so users don't read a gov F-grade as the result of an active/intrusive scan — which the spec explicitly forbids for automatic and gov scans.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.2 (lines 124-128); spec.md §2 (line 34), §3 table (lines 42-46), §3.1-§3.3 (lines 50-83)
- **Brief:** Brief §3.2 defines the level selector as exactly 3 cards named 'Básico', 'Intermedio', 'Avanzado' with semantics: Básico = pasivo/no intrusivo (default); Intermedio = activo suave, rate-limited; Avanzado = explotación, requiere autorización.
- **Spec:** Spec §2-§3 and §3.1-§3.3 define exactly three levels with the same names and same semantics: básico (pasivo, no intrusivo), intermedio (activo suave, rate-limited), avanzado (activo/explotación, requiere autorización). Number, names, and per-level intent match exactly.
- **Fix:** No change needed. Strong alignment on the count, names, and semantics of the three attack levels.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.2 (lines 129, 134-136); spec.md §3.2 line 73, §3.3 + §8.4 line 136, §4 lines 90-98
- **Brief:** Brief §3.2: the attestation gate 'aparece SOLO si el nivel es activo'; i.e. only Intermedio and Avanzado trigger it, and gob.mx + activo is blocked ('Los sitios gob.mx solo admiten escaneo pasivo').
- **Spec:** Spec §3.2/§3.3/§8.4 mark intermedio and avanzado as 'activos → requieren gate de atestación, nunca automáticos'; §4 enforces a gov whitelist where active is disabled for .gob.mx and only passive runs. The activo set and the gov restriction match.
- **Fix:** No change needed. The 'gate only for active levels' trigger and the gov-passive-only restriction are consistent.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §3.2 line 125; spec.md §2 line 36, §3 table line 43, §3.1 heading line 50, §4 line 90
- **Brief:** Brief consistently labels the levels 'Básico / Intermedio / Avanzado' (and §3.2 line 125 'Básico — pasivo, no intrusivo').
- **Spec:** Spec uses the compound forms 'básico/pasivo', 'básico (pasivo, no intrusivo)' and frequently refers to the lowest level as 'pasivo' as a near-synonym (e.g. §4 'is_gov/básico', §2 'escaneos automáticos ... SOLO pasivos'). A designer reading both could be unsure whether 'Pasivo' is a fourth label or a synonym of 'Básico'.
- **Fix:** In product/features/02-attack-levels/spec.md, standardize on 'Básico (pasivo)' as the canonical label and note 'pasivo' is a property, not a separate level, so the brief's card name 'Básico' is unambiguously the same thing. No UI label change needed in the brief.

### 03-agentic-surface

#### ⚠️ Drift · **high**
- **Ubicación:** design-prompt §3.3 (live feed chip) and §3.4 (Capa 2 panel header); spec §1 line 18, §5.1 line 125, §8 line 163
- **Brief:** The brief uses the full LLM01-LLM10 OWASP-for-LLM taxonomy as the category set for agentic findings: '+ categoría (OWASP A01–A10 / LLM01–LLM10)' (§3.3) and 'categoría OWASP/LLM' for the technical accordion (§3.4).
- **Spec:** The spec only ever names a small subset — §1 'LLM01 Prompt Injection, LLM02 Insecure Output Handling, LLM06 Sensitive Info Disclosure, etc.' and §5.1 / §8.4 'Mapeo a LLM01 / LLM06 según la técnica'. There is no LLM03/04/05/07/08/09/10 category produced by any specified technique; the three judged techniques (canary, system-prompt leak, jailbreak) map only to LLM01 and LLM06.
- **Fix:** If the product intends to surface the entire LLM01–LLM10 range in the UI category filter/chips, extend product/features/03-agentic-surface/spec.md to define which LLM categories the engine can emit beyond LLM01/LLM02/LLM06. Otherwise correct the brief to '(OWASP A01–A10 / LLM01–LLM10)' → reflect only the categories the engine produces (e.g. LLM01/LLM02/LLM06) so the category filter in §3.4 doesn't show empty buckets.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.3 (Agentic Surface Auditor 'fases: detección → inventario → sondas'); spec §8 lines 160-163, §2.1-§2.2
- **Brief:** The brief names the Agentic Surface Auditor lane phases as exactly 'detección → inventario → sondas' (§3.3).
- **Spec:** The spec's canonical flow (§8) is a 5-step pipeline: 1) Detección, 2) Decisión de estado (no_surface / detected_not_tested / tested), 3) Ataque (sondas), 4) Juicio (LLM-juez), 5) Demo. The detection itself is two passes ('1ª pasada fingerprints deterministas → 2ª pasada LLM', §2/§8.1) and 'inventario' is the persisted output of detection, not a distinct phase between detection and probing. The brief's three-phase label omits the 'estado/decisión' step and the 'juicio' step that the live theater would naturally show.
- **Fix:** Reconcile the lane phase labels in product/design-prompt.md §3.3 with the spec's pipeline. Either align the brief to the spec's named steps (detección [2 pasadas] → inventario/estado → sondas → juicio) or add a note in the spec §3/§8 that the UI groups these into the three user-facing phases the brief shows.

#### ❌ Contradicción · **medium**
- **Ubicación:** design-prompt §3.4 (Capa 2, 'El finding agéntico estrella') and §5 (momentos wow #2 'el finding agéntico estrella con su canary'); spec §5 lines 115-117, §8.5 line 164
- **Brief:** The brief presents the star finding as a single technique: 'El finding agéntico estrella: system-prompt leak del chatbot con su canary (token secreto filtrado)' (§3.4) — i.e. it treats the canary as a property of the system-prompt-leak finding.
- **Spec:** The spec (§5) defines CANARY and SYSTEM-PROMPT LEAK as two SEPARATE techniques with different confidence and evidence: CANARY = an injected unique secret token, regex/judge verifies it appears in the response → deterministic leak, confidence 'alta', evidence = the token (this is what gives 'evidencia incontestable'). SYSTEM-PROMPT LEAK = a rubric judgment ('reveals instructions/role/rules/tools'), confidence 'media' (LLM judgment). The 'incontestable evidence' demo finding in the spec is the CANARY technique (§5 line 115, §8.5 bot plantado con secreto en system-prompt), not the rubric-based system-prompt-leak.
- **Fix:** Clarify in product/design-prompt.md §3.4 that the star demo finding is the CANARY technique (deterministic leak where evidence = the leaked secret token), and that the canary token is what appears in the highlighted monospace block. Either keep 'system-prompt leak' wording but state the canary is the evidence type, or relabel to match the spec's CANARY technique with confidence 'alta'.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.4 (Capa 2 panel body, 'nivel de confianza'); spec §5 lines 113-117, §5.1 lines 123, 129
- **Brief:** The brief surfaces confidence as a generic per-finding attribute only: 'nivel de confianza' listed among technical panel fields (§3.4).
- **Spec:** The spec §5/§5.1 makes confidence load-bearing and binary by technique: 'confidence: alta si canary/regex, media si juicio LLM' and §5 stresses the distinction matters ('el canary distingue "el bot repitió la instrucción" de "fue comprometido de verdad"'). The deterministic canary finding (alta) vs rubric findings (media) is the credibility backbone of the differentiator screen, but the brief gives no UI treatment distinguishing high-confidence (canary/regex) from medium-confidence (LLM judgment) agentic findings.
- **Fix:** Extend product/design-prompt.md §3.4 to specify a visible confidence indicator on agentic findings that distinguishes 'alta (canary/regex, determinista)' from 'media (juicio LLM)', so the star canary finding reads as irrefutable vs. rubric judgments.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.1 (ranking row badges) and §3.4 (Capa 1 badges); spec §7 lines 142-154
- **Brief:** The brief shows two agentic-surface badges for detected-but-not-tested coverage: 'IA detectada, sin auditar' and 'cobertura parcial' (§3.1, §3.4), implying these cover the agentic detection states.
- **Spec:** The spec §7 defines THREE persisted agentic_status states (no_surface, tested, detected_not_tested) and binds the badge 'IA detectada, sin auditar' specifically to detected_not_tested. The state 'tested' (audited, with findings or clean) and 'no_surface' (legitimate N/A) have no badge/visual treatment in the brief, and the badge label there is not tied to the agentic_status state machine.
- **Fix:** Extend product/design-prompt.md §3.1/§3.4 to render all three agentic_status states from the spec: detected_not_tested → 'IA detectada, sin auditar' badge, tested → audited indicator (the dual web/agentic medidor), no_surface → an explicit 'sin superficie de IA' / N/A treatment so a missing badge isn't ambiguous.

#### ➕ Falta en spec · **low**
- **Ubicación:** design-prompt §3.1, §3.3, §3.4, §6 ('cobertura parcial'); spec §7 lines 146-154 (only three states, no partial-coverage)
- **Brief:** The brief introduces a 'cobertura parcial' badge/state shown on ranking rows (§3.1), in the report executive layer (§3.4 'Badges: ... / cobertura parcial'), and as a live-theater state and required deliverable state (§3.3 'cobertura parcial (banner)', §6 'cobertura parcial').
- **Spec:** Not covered. The spec §7 enumerates exactly three agentic states (no_surface, tested, detected_not_tested) and the only badge it names is 'IA detectada, sin auditar'. There is no 'cobertura parcial' concept defined for the agentic surface — neither what triggers it (e.g. some payloads timed out, multiple chatbots where only one was probed, cap-of-8/20 hit) nor how it differs from detected_not_tested.
- **Fix:** Add a definition of 'cobertura parcial' to product/features/03-agentic-surface/spec.md (§7) specifying its trigger conditions (e.g. payload cap reached, partial probe failure, multi-chatbot partial coverage) and how it relates to/differs from detected_not_tested, so the badge in the brief maps to a real engine state.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §3.4 (Inventario de superficie agéntica); spec §6 line 140
- **Brief:** The brief shows the no-model-detected label as 'modelo no expuesto' (§3.4: 'modelo inferido o "modelo no expuesto"').
- **Spec:** The spec §6 specifies the exact string as 'NULL + "modelo no expuesto (buena práctica)"' — the parenthetical '(buena práctica)' is part of the intended copy because it reframes a missing model as a positive security posture, not a gap.
- **Fix:** Update the literal copy in product/design-prompt.md §3.4 (and anywhere the inferred-model fallback is shown) to 'modelo no expuesto (buena práctica)' to match the spec's intended framing.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.3, §3.4; spec §2.3 line 56, §1 table 'Básico' line 22
- **Brief:** Brief §3.3/§3.4 require showing the detected chatbot's 'vendor + modelo inferido' in both the live auditor lane and the report's 'Inventario de superficie agéntica'.
- **Spec:** Strongly aligned: spec §2.3 persists the inventory '(vendor, modelo inferido, confianza, selectores/endpoint capturados)' and §1/§22 (básico) reports 'presencia, vendor y modelo inferido'. The vendor + inferred-model surfacing matches the detection output exactly.
- **Fix:** No change needed; confirm the UI sources vendor/inferred_model/confidence from the agentic_surface table fields named in spec §2.3 and 06-data-model.

### 04-scanning-engine

#### ❌ Contradicción · **medium**
- **Ubicación:** design-prompt §3.3 (line 151, OWASP Scanner chips) vs spec §3 (lines 63-72), §4.2 table (lines 124-125), §9 footnote (lines 233-239), §11 (line 283)
- **Brief:** The OWASP Scanner agent lane lists tool chips as "(nuclei, zap, testssl, nikto, sqlmap…)". The chip "zap" is shown inline with the light CLIs in the same chip row.
- **Spec:** Spec §3 / §9 / §11 classify ZAP as a HEAVY container that runs via the sibling/DooD helper run_tool() (ZAP baseline 120s, ZAP full active 240s), NOT as a light subprocess CLI. The light subprocess CLIs are "nuclei, testssl, whatweb, nikto, katana, ffuf, sqlmap, subfinder, dnsx" plus security-headers/Observatory (§3, §9 footnote, §4.2). ZAP is the only heavy web container in the OWASP set.
- **Fix:** In product/design-prompt.md §3.3, keep zap in the chip row but mark it as the heavy/slow chip (longer-running, distinct timeout up to 240s vs ~90s for the light CLIs) so the ToolChip timing/animation can differ. Optionally annotate the chip set as a representative subset and note ZAP runs longer than the light CLIs.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.3 (line 151) vs spec §9 table (lines 217-230), §3 (lines 63-66), §4.2 table (lines 116-123)
- **Brief:** The OWASP Scanner chip row enumerates only "nuclei, zap, testssl, nikto, sqlmap…" (5 chips with an ellipsis).
- **Spec:** Spec §9 / §3 / §4.2 define a much larger guaranteed OWASP toolset that the chip row should be able to represent: whatweb (fingerprint), katana (crawler), ffuf/gobuster (fuzzing), subfinder/dnsx (DNS recon), and security-headers/Mozilla Observatory (headers). These are all light subprocess CLIs in the scanners image and each has its own timeout in §4.2.
- **Fix:** In product/design-prompt.md §3.3, expand or explicitly genericize the ToolChip example set so a designer renders chips for the full battery (add whatweb, katana, ffuf, subfinder/dnsx, observatory/security-headers). Note the row is data-driven and the active set changes per attack level (basic vs intermedio vs avanzado).

#### ❌ Contradicción · **medium**
- **Ubicación:** design-prompt §3.3 (line 148, "timer (tranquiliza: '< 90s')") vs spec §4.1 (lines 104-106), §4.2 (lines 108-111, ~8 min budget), §10 (lines 253-256)
- **Brief:** The Live Pentest Theater header shows a generic timer that "tranquiliza: '< 90s'", implying every scan finishes in under 90 seconds.
- **Spec:** Spec §4.1 says <90s is the target for the BASIC level only, run concurrently. §4.2/§4.3 establish a budget global ~8 min for scans generally, and §10 explicitly states "el `<90s` es exclusivo del perfil demo". Higher levels (intermedio/avanzado with ZAP full 240s, sqlmap 120s, garak 180s) can run up to the ~8 min global budget, so a fixed "< 90s" timer would mislead users on non-basic scans.
- **Fix:** In product/design-prompt.md §3.3, make the timer/expectation level-aware: show "< 90s" only for nivel Básico (or the demo profile), and a higher estimate (up to ~8 min global budget) for intermedio/avanzado. State the timer should reflect the per-level expectation rather than a hardcoded 90s.

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §3.3 (lines 151-152, ToolChip states) and §6 (line 266, ToolChip component) vs spec §4.3 (lines 132-148)
- **Brief:** Tool chips have three states: encendido (ámbar, pulsando) while running; apagado verde = ok; rojo = falló/timeout. This is a 3-state model with no pending or aborted state.
- **Spec:** Spec §4.3 establishes that each tool runs in its own try/except and on failure/timeout emits a meta Finding "tool X no completó" and CONTINUES (partial failure is normal, especially ZAP active / sqlmap / nikto). It also implies a not-yet-started state and a watchdog that ABORTS the remaining battery when the global ~8 min budget is exhausted — so some tools never run, distinct from "falló/timeout".
- **Fix:** In product/design-prompt.md §3.3/§6, add a pending/queued ToolChip state (neutral gray, not started) and an "abortada por watchdog/budget" state distinct from rojo=falló. Map rojo specifically to per-tool timeout/failure.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §3.3 (line 151) vs spec §9 table (lines 218, 220)
- **Brief:** Brief uses the chip labels "testssl" and "zap".
- **Spec:** Spec canonical names are "testssl.sh" (§9) and "OWASP ZAP" (§9). The chip labels should be confirmed against the canonical tool names / the short tool ids the worker actually emits in scan_events.
- **Fix:** In product/design-prompt.md §3.3, confirm chip labels match the identifiers the worker emits (likely short ids like testssl/zap/nuclei). If the backend emits canonical names, align the chips; otherwise note chip labels are short tool ids mapped from the §9 canonical names. Low priority.

#### ➕ Falta en spec · **low**
- **Ubicación:** design-prompt §3.3 (lines 147-148, 153) vs spec §6 (line 180), §9 footnote (lines 233-239)
- **Brief:** Brief §3.3 specifies two phase labels for the progress bar ("Detectando tecnologías…", "Sondeando chatbot…") and the Agentic lane phases "detección → inventario → sondas".
- **Spec:** The scanning-engine spec does not define human-readable scan phase labels — it defers the live-view to [10-realtime-live-view] (§6) and the agentic surface to [05-agent-team] (§9 footnote, §10.1). "Detectando tecnologías…" maps loosely to whatweb/Wappalyzer fingerprint (§9) but the spec never names UI phase strings.
- **Fix:** No change needed in 04-scanning-engine spec (correctly out of scope; it defers to 10-realtime-live-view). Reconcile the phase-label vocabulary in design-prompt §3.3 against 10-realtime-live-view / 05-agent-team so "Detectando tecnologías…" / "Sondeando chatbot…" match the emitted phase/event names there.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.3 (lines 149-153) vs spec §9 footnote (lines 233-239), §10.1 (lines 266-278)
- **Brief:** Brief §3.3 splits the live view into two agent lanes: "🛡️ OWASP Scanner" (light + ZAP tools) and "🤖 Agentic Surface Auditor" (chatbot detection + probes), with separate partial scores.
- **Spec:** Spec §9 footnote cleanly separates the same two domains: light CLIs + ZAP/hexstrike are the OWASP/web scanners, while Playwright, garak and promptfoo "pertenecen a la superficie agéntica". The brief's two-lane split aligns with the spec's tool partitioning.
- **Fix:** No change. Confirm the agentic lane shows Playwright (conversation bridge) as the base path and garak/promptfoo only as opt-in fallback chips — per spec §10.1 they are fallback-only, so they should not always render.

### 05-agent-team

#### ➕ Falta en brief · **high**
- **Ubicación:** design-prompt §3.3 "Dos carriles de agente lado a lado" (line 149); spec §1 lines 16-18, §1.1 lines 77-83, §5 step 4 line 131
- **Brief:** Brief models the agent team as exactly two lanes side-by-side ("Dos carriles de agente lado a lado", §3.3), with no third actor. There is no orchestrator surfaced anywhere in the Theater or report.
- **Spec:** Spec §1 defines a THREE-model Agno Team in mode `coordinate`: an Opus **Orquestador** that coordinates the two Sonnet subagents in parallel and then redacts the executive summary, plus the two subagents (§1 lines 16-20; Team(mode="coordinate", model=Claude("opus"), members=[...]) lines 77-83). Worker flow §5 step 4 has Opus generate the executive summary as a distinct phase after merge/dedup/scoring (line 131).
- **Fix:** Extend product/design-prompt.md §3.3 to surface the Opus orchestrator as a coordinating element (e.g. a header/owl state "Owliver coordinando…" above the two lanes) and add a final synthesis state ("Owliver redactando el reporte…") between the two lanes finishing and the "Ver reporte completo →" CTA, reflecting that scoring (Python) + Opus executive-summary synthesis happen after the lanes complete.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.4 Capa 1 "Párrafo 'Owliver te explica'" + "Top 3 riesgos" (lines 175-177); spec §3 lines 112-118, §5 step 4 line 131
- **Brief:** Brief §3.4 Report shows the "Owliver te explica" plain-language paragraph + Top 3 riesgos as static report content, with no indication of who/what produces it or that it is generated after scanning.
- **Spec:** Spec §3 and §5 specify the "Owliver te explica" paragraph and the top-3 riesgos are written by Opus from a compact summary (<2k tokens), explicitly as the only LLM-authored text in the pipeline; scoring/dedup are deterministic Python and Opus does NOT compute scores (§3 lines 116-118; §5 step 4 line 131).
- **Fix:** No visual contradiction, but the Theater (§3.3) should reflect this generation step so the report does not appear instantly without a synthesis phase. Tie this to the orchestrator gap above (add an Opus synthesis/redaction state in design-prompt §3.3). No spec change needed.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.3 (line 151); spec §1.1 lines 60-61, §2.2 lines 102-110
- **Brief:** Brief §3.3 OWASP lane shows tool chips "nuclei, zap, testssl, nikto, sqlmap…" — the named examples emphasize nikto and sqlmap, which the spec deprioritizes.
- **Spec:** Spec §1.1 lists the full OWASP tool set as run_nuclei, run_zap, run_testssl, run_security_headers, run_whatweb, run_nikto, run_katana, run_ffuf, run_sqlmap, run_subfinder, hexstrike_mcp (lines 60-61, 86). The prioritized high-value parsers are Nuclei, testssl, security-headers/Observatory, with ZAP baseline 4th; nikto/sqlmap are explicitly best-effort "o se cortan" (§2.2 lines 102-110).
- **Fix:** Edit product/design-prompt.md §3.3 tool-chip example list to lead with the prioritized/most-likely-present tools (nuclei, zap, testssl, security-headers) so the designed chip row reflects what will actually light up in the demo, keep the "…" to signal the set is dynamic, and optionally note nikto/sqlmap may be absent (best-effort/cut).

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.3 Agentic lane (line 153); spec §1.1 lines 68-74, §5 step 3 line 130
- **Brief:** Brief §3.3 gives the OWASP lane a row of tool chips that light up/turn off, but gives the Agentic lane only abstract phases ("detección → inventario → sondas") with NO tool chips.
- **Spec:** Spec §1.1 gives the Agentic Surface Auditor concrete runnable tools: crawl_site, classify_dom_llm, fingerprint_vendors, run_promptfoo, run_garak (lines 68-74); the worker emits the same tool_start/tool_end events for them (§5 step 3 line 130). So agentic tools are first-class runnable tools, not just phase labels.
- **Fix:** Extend product/design-prompt.md §3.3 so the Agentic lane can also render tool chips (e.g. garak, promptfoo, crawl, fingerprint) that light up, matching the OWASP lane's ToolChip pattern — restoring symmetry and reflecting that both subagents emit tool_start/tool_end events.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.3 (lines 149-153); spec §1 lines 19-20, §1.1 lines 58-75
- **Brief:** Brief §3.3 names the two agent lanes "🛡️ OWASP Scanner" and "🤖 Agentic Surface Auditor".
- **Spec:** Spec §1 names the two Sonnet subagents exactly: name="OWASP Scanner" (line 19) and name="Agentic Surface Auditor" (line 20); pseudocode Agent(name="OWASP Scanner"...) line 59 and Agent(name="Agentic Surface Auditor"...) line 68.
- **Fix:** No change. Confirm both docs keep these exact strings as the canonical lane/agent display names so the live-view UI labels match worker-emitted agent_status events verbatim.

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §3.3 (line 153) and §3.4 inventory (lines 178-179); spec §1.1 lines 43-49
- **Brief:** Brief §3.3 describes the Agentic lane phases as "detección → inventario → sondas".
- **Spec:** Spec models agentic progression via agentic_status enum no_surface | detected_not_tested | tested (AgenticResult, §1.1 line 48). The inventory fields are type, vendor (None for generic surface), inferred_model (NULL if "modelo no expuesto") (§1.1 lines 46-49).
- **Fix:** Minor: align the Theater agentic phase labels with the spec's status semantics so the "detected_not_tested" state (the "IA detectada, sin auditar" badge the brief already uses) is reachable as a terminal lane state, not only "sondas". Add a note in design-prompt §3.3 that the agentic lane can end detected-but-not-tested. No spec change needed.

### 06-data-model

#### ➕ Falta en spec · **high**
- **Ubicación:** design-prompt §3.1 (line 114), §3.6 (lines 205-209) / spec §3.1 sites (lines 81-88), §3.2 scans (lines 112-116)
- **Brief:** Brief §3.1 (Leaderboard rows) and §3.6 (Histórico del sitio: 'gráfico de tendencia del grado', 'cómo cambió el grado') require a per-scan grade trend arrow ('▲ ▼ vs el escaneo previo') and a grade-over-time line chart. The brief §3.1 explicitly shows 'Valor de penalización cruda + tendencia (▲ ▼ vs el escaneo previo).'
- **Spec:** The model persists penalty_raw (§3.2) and overall_grade per scan, plus latest_scan_id on sites, and first_seen/last_seen on findings. But there is NO stored 'previous scan' pointer or trend/delta field; the spec never defines how the UI gets 'vs el escaneo previo' delta. Trend must be derived by querying prior scans of the same site_id; the data model does not name this query/contract or a delta column.
- **Fix:** In product/features/06-data-model/spec.md §3.1/§3.2, add a note that the per-site trend (▲▼ and the grade-over-time series) is computed by ordering scans WHERE site_id=? ORDER BY finished_at, and clarify whether the previous scan's grade/penalty_raw is read live or stored as a delta. Tie to 08-ranking-watchlists if the ordering/diff query lives there.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.3 (line 152) / spec §3.2 (lines 109-110)
- **Brief:** Brief §3.3 OWASP Scanner tool chips list 'nuclei, zap, testssl, nikto, sqlmap…' and §2 telemetry implies arbitrary tool keys; the live tool-status UI binds chip on/off/ok/failed/timeout state to these tool names.
- **Spec:** spec §3.2 documents tools_status example as '{nuclei:\'done\', zap:\'running\', testssl:\'queued\'}' and coverage as '[{tool, status: ok|failed|timeout}]', but only ever names nuclei/zap/testssl as the base scanners; nikto/sqlmap are not enumerated anywhere in the data-model spec. tools_status per-tool status enum (queued|running|done) vs coverage status enum (ok|failed|timeout) are two different vocabularies the chip UI must map.
- **Fix:** In 06-data-model spec §3.2, enumerate the canonical tool keys that may appear in tools_status/coverage (or point to 04-scanning-engine for the authoritative list) and explicitly state the two status vocabularies (tools_status: queued|running|done vs coverage: ok|failed|timeout) so the ToolChip can map states. Confirm nikto/sqlmap are valid tool keys or remove them from the brief.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.4 (line 184) / spec §3.3 (line 134), §5.1 (line 216)
- **Brief:** Brief §3.4 Capa 2 requires references rendered as 'CWE/OWASP' refs, and §3.4 lists 'nivel de confianza' per finding panel.
- **Spec:** spec §3.3/§5.1 define references jsonb / list[str] as opaque 'enlaces de referencia' with no structure distinguishing CWE vs OWASP. The brief implies typed/labeled references (CWE id + OWASP category) the model does not model. (confidence is fully covered as alta|media|baja.)
- **Fix:** In 06-data-model spec §3.3, clarify the shape of references jsonb (e.g. [{type:'cwe'|'owasp', id, url}]) so the report UI can render CWE vs OWASP refs distinctly, or state explicitly that references is a flat list of URLs and the brief should not promise typed CWE/OWASP labels.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.4 (lines 181-190) / spec §3.3 (line 135), §5 first_seen/last_seen (line 137)
- **Brief:** Brief §3.4 Capa 2 accordion header is 'chip de severidad + categoría OWASP/LLM + título' and offers filters by severity/dimension/category, but never surfaces the finding.status (open|fixed|accepted) lifecycle.
- **Spec:** spec §3.3 / §5 define findings.status ENUM(open, fixed, accepted) as a first-class, site-level concept central to monitoring ('un finding que no reaparece pasa a fixed; accepted es un riesgo aceptado por el usuario'). The historical-trend section of the report (§3.4 'qué findings son nuevos/resueltos') needs this state but the brief never designs the open/fixed/accepted states or an 'accept risk' action.
- **Fix:** Extend design-prompt §3.4 to design the finding status states (open / fixed / accepted) and a 'marcar como riesgo aceptado' action, plus a visual treatment for 'nuevo' (first_seen=this scan) vs 'resuelto' (fixed) findings in the trend view, since the data model treats status as load-bearing for monitoring.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §3.1 (line 113), §3.3 (line 163), §6 (line 268) / spec §3.2 status partial + coverage (lines 99, 110)
- **Brief:** Brief §3.1 leaderboard row uses the badge label 'cobertura parcial' and a separate scan state 'cobertura parcial (banner)' in §3.3, while §3.5/§6 list error code 410 and 404 for share links.
- **Spec:** spec maps 'cobertura parcial' to TWO distinct model concepts that the brief conflates into one badge: scans.status='partial' (§3.2, a scan that lost ≥1 base scanner) AND coverage jsonb (the per-tool ok|failed|timeout list). A designer reading 'cobertura parcial' cannot tell whether the badge derives from status=partial or from coverage contents.
- **Fix:** In design-prompt, note that the 'cobertura parcial' badge is driven by scans.status='partial', and (optionally) that the per-tool detail comes from coverage; or add a glossary line in 06-data-model spec mapping the UI label 'cobertura parcial' to status='partial'.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.5 (lines 201-202), §6 (line 268) / spec §3.8 (lines 184-185)
- **Brief:** Brief §3.5 designs the public link states 'inexistente → 404' and 'expirado/revocado → Este enlace expiró', collapsing expiry and revocation into one screen.
- **Spec:** spec §3.8 distinguishes the underlying data (expires_at vs revoked_at) but maps BOTH to HTTP 410 Gone, and 404 only for non-existent token. So the brief's collapse of expired+revoked into one '410' screen is actually CORRECT per the model — but the brief's §6 deliverable lists '422' as an error state with no data-model counterpart for the public-report flow.
- **Fix:** Minor: in design-prompt §6, scope the 422 error state to the scan-submission flow (§3.2 validation), not the public report; the public-report flow only emits 404/410 per 06-data-model spec §3.8. No data-model change needed.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.5 (lines 193-202) / spec §3.8 (lines 178-185)
- **Brief:** Brief §3.5 specifies '/r/[token]', 'link inexistente → 404', 'expirado/revocado → Este enlace expiró', and public report shows executive layer + findings with exploits redacted ('nunca el payload crudo').
- **Spec:** spec §3.8 matches exactly: public_reports(token, scan_id, created_at, expires_at, revoked_at), GET /r/{token} returns 404 if missing, 410 Gone if expires_at<now OR revoked_at set, and exposes 'capa ejecutiva + findings sin payloads de explotación'.
- **Fix:** No change. Strong alignment between the public-share UI and the public_reports table; preserve the 404 vs 410 distinction in implementation.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.1 (lines 112-113), §3.4 (lines 173-180) / spec §3.2 (line 115), §3.4 (lines 145-149), §5.2 (lines 248-252)
- **Brief:** Brief §3.1/§3.4 'Doble medidor 🛡️ Web vs 🤖 Agéntico', badge 'IA detectada, sin auditar', and inventory 'vendor + modelo inferido / modelo no expuesto'.
- **Spec:** spec §3.2/§5.2 fully back this: web_score, agentic_score NULL, agentic_status ENUM(no_surface, detected_not_tested, tested) with the 'detected_not_tested' → badge 'IA detectada, sin auditar' mapping spelled out, and agentic_surface(vendor, inferred_model NULL = 'modelo no expuesto').
- **Fix:** No change. The dual-meter + agentic badges map cleanly onto agentic_status and agentic_surface fields.

### 07-scoring

#### ❌ Contradicción · **high**
- **Ubicación:** design-prompt §3.4 (line 174) and §3.1 (line 112) vs 07-scoring/spec.md §2, §5.1, §6
- **Brief:** Brief §3.4 Capa 1 specifies 'dos gauges semicirculares: 🛡️ Web y 🤖 Agéntico, con el score numérico + grado al centro' (line 174) — i.e. each dimension (Web AND Agéntico) gets its own A-F grade displayed in its gauge. The Hall of Shame row also implies per-dimension grades: 'SAT: "C web / F agéntico"' (line 112).
- **Spec:** The spec defines grade A-F as derived ONLY from overall_score (§5.1: 'El grado se deriva del overall_score'). There is exactly ONE overall_grade (§6: 'La columna de grado se llama overall_grade en todas partes'). web_score/agentic_score are 0-100 numeric sub-scores (§2) with NO per-dimension grade defined anywhere. A 'C web / F agéntico' pair of grades has no formula in the spec.
- **Fix:** Resolve in product/features/07-scoring/spec.md: either (a) add a normative rule projecting web_score and agentic_score each to their own A-F grade (reusing the §5.1 scale), making the brief's 'C web / F agéntico' and per-gauge grades valid; or (b) if only overall_grade exists, change product/design-prompt.md §3.4/§3.1 so per-dimension gauges show numeric scores only (no letter grade) and the SAT example reads e.g. 'web 72 / agéntico 0'. This is the central two-dimension visual; the spec must say whether sub-grades exist.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.1 (lines 111-113) and §3.4 (lines 174-180) vs 07-scoring/spec.md §3 + §7 (lines 44-51, 109-113)
- **Brief:** Brief §3.4 shows two gauges 🛡️ Web + 🤖 Agéntico and §3.1 a 'Doble medidor lado a lado: 🛡️ Web vs 🤖 Agéntico' for every row, with no guidance for when the agentic dimension was not testable. It only mentions the badge 'IA detectada, sin auditar' generically (§3.1 line 113, §3.4 line 180).
- **Spec:** §3 + §7 table define THREE agentic_status states that must render differently: no_surface ('overall = web_score (no penaliza)'), detected_not_tested ('No se promedia y no se premia con 100: badge "IA detectada, sin auditar"'), and tested (valid agentic_score). The agentic gauge has three distinct presentations, not one.
- **Fix:** Extend product/design-prompt.md §3.1/§3.4 to specify the agentic gauge's THREE states: no_surface → 'Sin superficie IA' / N/A (not penalized); detected_not_tested → 'IA detectada, sin auditar' badge with the gauge NOT showing a clean/100 score; tested → numeric agentic_score. Currently the brief conflates no_surface and detected_not_tested into one generic badge.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.1 (line 113), §3.3 (line 162), §3.4 (line 180) vs 07-scoring/spec.md §4 (line 60) + §5.2 (line 79)
- **Brief:** Brief §3.1 lists 'cobertura parcial' only as a row badge (line 113) and §3.3/§3.4 as a banner/badge state, with no statement that partial coverage forces a maximum grade.
- **Spec:** §4 + §5.2 (lines 60, 79): with partial coverage 'El grado se capa en C — nunca A/B con cobertura parcial, independientemente del score numérico'. This is a hard grade cap, not merely a label.
- **Fix:** Add to product/design-prompt.md §3.1/§3.4 that when 'cobertura parcial' is present, the displayed GradeBadge is capped at C (never A/B) regardless of the numeric gauges. Designers otherwise risk rendering an A grade alongside a 'cobertura parcial' badge, which the spec forbids.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §2 (lines 86-88) + §3.4 (line 174) vs 07-scoring/spec.md §2 (line 30)
- **Brief:** Brief §2 Motion (lines 86-88) and §3.1/§3.4 require numeric scores presented as count-up grades and gauges that 'animan de 0 al valor' with 'el score numérico + grado al centro' — i.e. the UI surfaces the 0-100 numeric web_score/agentic_score directly to end users in gauges and the leaderboard.
- **Spec:** §2 defines sub_score = max(0, 100 − min(100, penalty_raw)) as a 0-100 value 'con cap, para mostrar 0–100' (line 30), confirming the numeric scores are display values. The spec does NOT specify whether the numeric overall_score / sub-scores are surfaced to users in the report/leaderboard UI or only the letter grade; presentation is deferred to 13-frontend.
- **Fix:** In product/features/07-scoring/spec.md add a one-line note (or defer explicitly to 13-frontend) confirming that the numeric 0-100 sub-scores are intended to be displayed to users (gauge center), since the brief's count-up gauge presentation depends on it. Minor, but makes the brief's reliance on visible numeric scores authoritative.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §2 (lines 70-79) vs 07-scoring/spec.md §5.1 (line 70)
- **Brief:** Brief §2 grade scale: 'A (≥90) ... B (≥80) ... C (≥70) ... D (≥60) ... E (≥40) ... F (<40)' (lines 73-78), with E as a distinct band and F for the Hall of Shame.
- **Spec:** §5.1: 'Grado: A ≥90 · B ≥80 · C ≥70 · D ≥60 · E ≥40 · F <40' — exact match, including the E (40-59) step explicitly added for the populated gov leaderboard zone.
- **Fix:** No change needed. Thresholds, band count, and the E step are perfectly aligned. Confirm color tokens stay mapped to these exact six bands.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §3.1 (line 114) vs 07-scoring/spec.md §2 (line 39) + §6 (lines 89-92)
- **Brief:** Brief §3.1 calls the tie-break/leaderboard value 'Valor de penalización cruda' (line 114) and pairs it with 'tendencia (▲ ▼ vs el escaneo previo)'.
- **Spec:** §2/§6 name this field `penalty_raw` ('penalización cruda', persisted sin cap, used for '(overall_grade ASC, penalty_raw DESC)'). §6 also says the row 'muestra penalty_raw (o el conteo ponderado)'. Same concept, but the brief's free-text Spanish label never ties to the canonical field name penalty_raw.
- **Fix:** In product/design-prompt.md §3.1, annotate 'Valor de penalización cruda' as the canonical field `penalty_raw` so the designer/dev maps the column correctly, and confirm the row sorts by (overall_grade ASC, penalty_raw DESC) per spec §6 — the brief's 'peores primero' ordering depends on it but never states the tie-break.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.1 (lines 98, 107-114) vs 07-scoring/spec.md §6 (lines 86-94)
- **Brief:** Brief §3.1 row spec (lines 107-114) shows position + overall grade + dual gauges + raw penalty, ordered 'peores primero' (line 98), but never states the tie-break rule between two F rows.
- **Spec:** §6 (lines 86-94) is the authority of order: leaderboard is NOT sorted by overall_score but by '(overall_grade ASC, penalty_raw DESC)' — worst first with raw-penalty tie-break, and the row must show penalty_raw 'para que el contraste entre dos sitios ambos en F sea visible'.
- **Fix:** Add to product/design-prompt.md §3.1 that rows tied on grade (e.g. many F's) sort by penalty_raw DESC, and that the displayed penalty value is what makes two-F contrast visible — this is exactly the demo's first-screen concern in spec §6.

### 08-ranking-watchlists

#### ➕ Falta en brief · **high**
- **Ubicación:** design-prompt §3.1 (lines 96-104) vs spec §2.2 (lines 41-43) and §6 table row 'Usuario envía URL en nivel pasivo/básico → Entra al ranking público' (line 141)
- **Brief:** The brief frames the Hall of Shame leaderboard exclusively as a ranking of .gob.mx government sites ('ranking de sitios .gob.mx, peores primero'; counter '128 sitios auditados · 41 reprobados (grado F)'), with no mention that user-submitted passive scans also populate it.
- **Spec:** spec §2.2 (Invariante de solo-pasivo): 'Cualquier URL que un usuario envíe en nivel pasivo/básico entra también al ranking global'. So the public board includes any passive scan, not only gov sites; only active (intermedio/avanzado) and owner-scoped scans are excluded (visibility=private).
- **Fix:** Edit product/features/08-ranking-watchlists/spec.md to resolve the internal tension between §2.1 ('leaderboard de sites WHERE is_gov=true') and §2.2 ('cualquier URL pasiva entra al ranking global'): state whether non-gov passive scans appear in the same '/' board or a separate public list. Then update design-prompt.md §3.1 to show whichever is canonical (e.g. a 'gob.mx' filter/tab vs a mixed public list), since the brief currently only designs the gov-only view.

#### ➕ Falta en brief · **high**
- **Ubicación:** design-prompt §3.1 lines 112-113 ('Badges cuando aplique: ... "cobertura parcial"') vs spec §2.1 line 39
- **Brief:** The brief §3.1 lists a 'cobertura parcial' badge but never states that partial-coverage rows have their grade capped at C, nor that an A grade is impossible with partial coverage. It implies grades are shown as computed.
- **Spec:** spec §2.1 (line 39): 'El ranking nunca muestra A con cobertura parcial: cuando scans.status="partial" el grado se capa en C y la fila lleva la etiqueta "cobertura parcial"'.
- **Fix:** Edit product/design-prompt.md §3.1 to specify that rows with 'cobertura parcial' display a grade capped at C (never A/B) and pair the capped GradeBadge with the 'cobertura parcial' label, so the designer renders the cap visually instead of an uncapped score.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.1 line 115 vs spec §2.1 line 31
- **Brief:** The brief §3.1 specifies three leaderboard filters: 'por grado, por peor dimensión (web/agéntico), por país (MX)'.
- **Spec:** spec §2.1 (line 31) only covers a country filter: '... filtrable por país (MX)'. 'Por grado' and 'por peor dimensión (web/agéntico)' are not covered anywhere in the spec.
- **Fix:** Extend product/features/08-ranking-watchlists/spec.md §2.1 to enumerate the supported leaderboard filters (grade, worst-dimension web/agéntico, country MX) and define how 'peor dimensión' maps to the persisted Web vs Agéntico sub-grades, so the filter the brief draws has a backing data contract.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.1 lines 110-112 vs spec §2.1 lines 33-39 and §2.4 line 58
- **Brief:** The brief §3.1 specifies a per-row 'Doble medidor lado a lado: 🛡️ Web vs 🤖 Agéntico', with a star row 'SAT: C web / F agéntico'.
- **Spec:** spec §2 (ranking) never defines that the leaderboard row shows separate Web vs Agéntico meters/grades; §2.1 consumes only '(overall_grade, penalty_raw)'. The double-score per row is only referenced as a fixtures narrative example ('SAT con C web / F agéntico', §2.4 line 58), not as a required leaderboard row component.
- **Fix:** Extend product/features/08-ranking-watchlists/spec.md §2.1 to state that each leaderboard row exposes the two dimension grades (Web, Agéntico) in addition to overall_grade/penalty_raw, naming the persisted fields the row reads, so the brief's double-meter row is backed by the ranking spec rather than only by the fixtures example.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.1 line 114 vs spec §4.2 lines 99-104
- **Brief:** The brief §3.1 designs only a single combined trend arrow per row ('Valor de penalización cruda + tendencia (▲ ▼ vs el escaneo previo)'), tied to grade/penalty change.
- **Spec:** spec §4.2 (lines 86-104) defines change detection at site level via dedupe_key/first_seen with two distinct signals — grade drop AND new critical finding — and §4.2/§2.1 distinguish overall_grade movement from penalty_raw. The brief collapses 'vs el escaneo previo' onto penalty only and does not surface a 'new critical' signal in the row.
- **Fix:** Edit product/design-prompt.md §3.1 to clarify the trend arrow reflects overall_grade change vs the previous scan (not just penalty_raw), and consider a secondary indicator for 'nuevo critical', matching the two site-level signals defined in spec §4.2.

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §3.1 line 117 and §6 line 268 vs spec §2.4 lines 54-61
- **Brief:** The brief §6 deliverables require an empty state for every screen ('Estados de cada pantalla: loading ..., vacío, ...'), implicitly including the leaderboard; §3.1 designs only a loading skeleton for it.
- **Spec:** spec §2.4 (Estrategia de fixtures pre-horneados, lines 54-61) mandates the board is seeded with 30-50 pre-baked rows so it 'never appears empty' ('la primera pantalla del demo nunca aparezca vacía'; 'el board siempre tenga 30-50 filas'). So the leaderboard has no empty state by design.
- **Fix:** Edit product/design-prompt.md §3.1 to note the leaderboard is never empty (fixture-seeded) and only needs the loading skeleton, so the designer does not produce a leaderboard empty state that contradicts the fixtures strategy.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.8 lines 220-225 vs spec §5.1 lines 108-115 and §3 lines 64-69
- **Brief:** Brief §3.8 watchlist alert channels: 'Ajustes de alertas (email / Slack)'; and §3.8 monitoring toggle 'toggle de monitoreo (re-escaneo periódico)' + no in-app notification center.
- **Spec:** spec §5.1 (lines 108-115): channels are 'Resend (email) y/o Slack webhook', with 'Alertas in-app = recorte' (no in-app notification center). Brief §3.8 correctly shows only email/Slack and no in-app inbox; monitoring toggle matches spec §3 monitor=true + §4 cron re-scan. Strong alignment.
- **Fix:** No change needed. Keep user-facing copy as 'email / Slack'; confirm the brief does not add an in-app notification center, consistent with the §5.1 recorte.

### 09-reporting

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.4 (Capa 2 — Técnica, 'Filtros por severidad / dimensión / categoría') vs 09-reporting/spec.md §2.2, line 47
- **Brief:** Brief §3.4 (Capa 2 técnica) lists the finding filters as 'Filtros por severidad / dimensión / categoría'.
- **Spec:** Spec §2.2 lists 'Filtros por severidad / source / categoría' (the middle facet is `source`, not 'dimensión').
- **Fix:** Reconcile the facet name. The data field is `source` (per the spec/data model). Either change design-prompt §3.4 to 'por severidad / source / categoría' (matching the field), OR if 'dimensión' (Web/Agéntico) is the intended user-facing label, add it to 09-reporting/spec.md §2.2 as the display alias for the `source` filter so designer and dev agree. Note 'dimensión' (Web vs Agéntico) and 'source' may be two different facets — clarify whether the panel filters by one or both.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.5 ('muestra tipo, severidad, impacto, remediación') vs 09-reporting/spec.md §5, line 85
- **Brief:** Brief §3.5 says the public report shows 'tipo, severidad, impacto, remediación' for technical findings (and elsewhere 'muestra tipo, severidad, impacto, remediación').
- **Spec:** Spec §5 (line 85) enumerates what is SHOWN in the public report as 'tipo de finding, categoría OWASP/LLM, severidad, `impact`, `remediation`, `references`, `confidence`' — i.e. it explicitly also shows categoría, references and confidence.
- **Fix:** Update design-prompt §3.5 to list the full shown set: 'tipo, categoría OWASP/LLM, severidad, impacto, remediación, referencias y confianza' so the public-report panels are designed with category/references/confidence visible (only the raw exploit payload is redacted). Keeping the short list risks a designer dropping the OWASP category chip and references from the public view.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.4 ('Exportar PDF · Compartir') / §3.5 vs 09-reporting/spec.md §3 line 60 and §5.2 line 103
- **Brief:** Brief §3.4/§3.5 list Export PDF and Share actions but never specify toast feedback for them or for consuming an expired/revoked link.
- **Spec:** Spec §3 (line 60) and §5.2 (line 103) require Toasts via `sonner` for 'compartir generado, PDF listo, errores 403/410' — i.e. success toasts on share-link generated and PDF-ready, and error toasts for 403/410 when consuming a link.
- **Fix:** Add a 'Toast / feedback' note to design-prompt §3.4 and §3.5 (and to the §6 component list) covering: 'link público generado', 'PDF listo', and error toasts for 403/410. Provide the es-MX copy so the toast component is designed, not improvised.

#### ➕ Falta en spec · **low**
- **Ubicación:** design-prompt §3.9 (Report Card compartible) and §3.5 ('Banner para compartir en redes (ver Report Card, 3.9)') vs 09-reporting/spec.md §4–§5 (no coverage)
- **Brief:** Brief §3.9 specifies a shareable 'Report Card' image (boletín de calificaciones: grado A–F + medidores 🛡️/🤖 + nombre de dependencia + marca Owliver) shown as the social preview when pasting a /r/[token] link, and §3.5 references it as the share banner.
- **Spec:** 09-reporting/spec.md does not cover a Report Card / social share-card artifact at all; §5 (public report) and §4 (delivery/export) describe only the in-app/public page and PDF export.
- **Fix:** Extend 09-reporting/spec.md (a new subsection under §4 Entrega, e.g. §4.2 'Report Card / OG image') to specify the share-card contract: which fields it renders, that it is the og:image for /r/[token], how it is generated, and that it follows the same redaction rule (executive grade only, no exploits). Otherwise the Report Card is unowned and the public-link social preview is unspecified.

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §3.5 (states) / §6 ('404/410/422') vs 09-reporting/spec.md §5.1 lines 92–93 and §5.2 line 103
- **Brief:** Brief §3.5 maps states as 'link inexistente → 404; link expirado/revocado → pantalla "Este enlace expiró"' without naming the HTTP status for the expired case; §6 deliverables lists error states as '404/410/422'.
- **Spec:** Spec §5.1 (lines 92–93) is explicit: token inexistente → 404; token with expires_at<now() OR revoked_at not null → 410 Gone with copy 'Este enlace expiró'. §5.2 adds 403/410 toasts on consumption.
- **Fix:** Align §3.5 explicitly with the spec: 404 = inexistente, 410 Gone = expirado/revocado ('Este enlace expiró'). Also note that §6 lists 422 while the reporting spec mentions 403 (not 422) for the public link; clarify which status the report public-link error screen must render so the designer maps the right state.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.4 ('Acciones: Exportar PDF · Compartir') vs 09-reporting/spec.md §4.1 lines 70–72
- **Brief:** Brief §3.4 presents 'Exportar PDF · Compartir' as firm, always-present report actions with no fallback note.
- **Spec:** Spec §4.1 (M3, line 70–72) states PDF export and share are RECORTABLE under time pressure; if cut, the demo runs on the in-app report page with redaction already applied. The redaction behavior (§5) is NOT cuttable even though its vehicle (the public link) is.
- **Fix:** Add a note in design-prompt §3.4 that Export PDF / Compartir may be deferred (M3, recortable) and the in-app report (with redaction) is the imprescindible piece — so the layout degrades gracefully if those actions are absent, rather than designing the report header around two mandatory buttons.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.4 (star finding) vs 09-reporting/spec.md §2.3, lines 50–52
- **Brief:** Brief §3.4 specifies the agentic 'star finding' as a system-prompt leak with its canary in a highlighted monospace block as 'evidencia incontestable', visually emphasized.
- **Spec:** Spec §2.3 matches: the agentic star finding carries 'prueba con canario' as a Layer-2 technical finding with destacado visual treatment, and its exploit payload is redacted in the public report (§5).
- **Fix:** No change needed. Confirm the designer treats the canary block as in-app-only evidence (the same redaction rule of §5 applies to its payload in the public /r/[token] view).

### 10-realtime-live-view

#### ❌ Contradicción · **high**
- **Ubicación:** design-prompt §3.3 (Botón Cancelar + Estados list); spec §2 (event type enum, lines 41-44) and line 57 (done/error terminal).
- **Brief:** The Theater defines a 'cancelado' state and a 'Botón Cancelar (mata el escaneo)' that kills the scan (design-prompt §3.3: 'Botón Cancelar (mata el escaneo)' and 'Estados: ... cancelado').
- **Spec:** The typed event schema's discriminator enum has NO cancel/cancelled value. §2 lists exactly: 'agent_status | tool_start | tool_end | finding | phase | score | done | error', and §2 explicitly names only 'done' (cierre exitoso) and 'error' (cierre con error) as the terminal types: 'Ambos son terminales para el stream.' There is no terminal event the front can render as 'cancelado', and no cancel transport/endpoint is defined.
- **Fix:** Extend product/features/10-realtime-live-view/spec.md §2: add a 'cancelled' (or 'canceled') terminal discriminator to the type enum and state it is terminal alongside done/error, so the UI 'cancelado' state has a backing event. Also note (or cross-ref 12-api) the cancel action endpoint that emits it, since the brief's Cancelar button 'mata el escaneo'.

#### ➕ Falta en spec · **high**
- **Ubicación:** design-prompt §3.3 ('barra de progreso 0–100 con fase legible'); spec §2 event schema (lines 32, 39-51) — 'phase' has no percent field.
- **Brief:** Theater header shows a 'barra de progreso 0–100 con fase legible' — a numeric 0-100 progress bar plus a phase label (design-prompt §3.3 Header).
- **Spec:** The event schema (§2) defines a 'phase' discriminator carrying only { message, ts, ... } and a generic 'payload?'. There is NO numeric progress field (no percent/0-100, no total/current) anywhere in the typed schema. The spec gives the phase TEXT but no data to drive a 0-100 bar.
- **Fix:** Extend product/features/10-realtime-live-view/spec.md §2 to specify how the 0-100 progress is transported (e.g. a 'percent'/'progress' field on the 'phase' event payload, or a dedicated 'progress' type), or explicitly state the bar is derived client-side from phase ordering. Otherwise the brief's progress bar has no source of truth.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.3 / §4.3 (no transport named); spec title + §3 (SSE), §3.2, §4.
- **Brief:** The brief never names the realtime transport; §3.3 only says 'diséñalo asumiendo replay' and lists live behaviors (findings cayendo, chips encendiéndose) without committing to SSE vs WebSocket.
- **Spec:** § title and §3 mandate SSE specifically: endpoint 'GET /scans/{id}/stream', browser 'EventSource', SSE 'id:' = seq, 'Last-Event-ID' reconnection, §3.2 heartbeat (':' comment every ~20s) and compression disabled. Auth is cookie-based because 'EventSource no permite headers custom' (§4).
- **Fix:** Add a one-line transport note to design-prompt §3.3 (or §2 Motion) stating the live view is SSE-driven with auto-reconnect/replay, so the designer accounts for SSE reconnection UX (transient drop → silent reconnect, not a manual refresh) and the cookie-auth (no header) constraint.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §4.3 ('se repinta completo desde el inicio (replay)') and §3.3 ('se repinta completo'); spec §3 step 1-2 + §3.1 idempotency.
- **Brief:** design-prompt §4.3 (flujo 'Ver el ataque en vivo + recargar') states reload repaints 'completo desde el inicio (replay)' — implying replay always starts from scan start (seq 0).
- **Spec:** §3 replay is cursor-based: 'todos los eventos con seq > cursor', and the cursor comes from Last-Event-ID/?since_seq=; full replay from the start (cursor 0) happens ONLY 'Si no hay cursor'. A hard reload recreates EventSource with no Last-Event-ID so it IS full replay — but an in-tab SSE auto-reconnect resumes from lastSeq, not from the start.
- **Fix:** Tighten design-prompt §4.3 wording to 'al recargar la página (sin cursor) el progreso se repinta completo; en una reconexión transitoria se reanuda desde el último evento visto', matching the spec's cursor semantics so the designer doesn't assume every reconnect blanks-and-replays the whole timeline.

#### ➕ Falta en spec · **low**
- **Ubicación:** design-prompt §3.3 (Estados: 'en cola (🦉 dormido)'); spec §2 enum (no queued/running-start signal).
- **Brief:** Theater defines an 'en cola (🦉 dormido)' queued state shown before the scan is running (design-prompt §3.3 Estados; §3.7/flows reference owl idle).
- **Spec:** The spec models the stream as empty-replay-then-tail; there is no explicit 'queued'/'en cola' marker or event. A queued scan simply yields an empty replay with no events, and no event type signals 'queued' vs 'running has not emitted yet'.
- **Fix:** In product/features/10-realtime-live-view/spec.md, clarify how the front distinguishes 'en cola' (queued, owl asleep) from 'corriendo' — e.g. an initial 'agent_status'/'phase' event on worker start, or document that empty stream = queued. Keeps the OwlMascot idle→running transition data-backed.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.3/§4.3; spec §1, §3 (steps 1-3), §3.1.
- **Brief:** design-prompt §3.3 + §4.3 require 'Al recargar la página, el progreso se repinta completo (no queda vacío) — diséñalo asumiendo replay.'
- **Spec:** Fully supported and is the spec's central thesis: §1 'La verdad vive en Postgres' (scan_events authoritative), §3 replay-then-tail emits all events with seq>cursor on connect, §3.1 client dedupes by seq. The 'no queda vacío on reload' guarantee is exactly what the spec engineers.
- **Fix:** No change. Strong alignment — confirm the front consumes id:/Last-Event-ID per spec §3 so the brief's replay promise holds in implementation.

### 11-auth-magic-link

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §4.2 (and §3.2 level selector); spec §1 'Superficies que exigen sesión' bullets + §4
- **Brief:** design-prompt §4.2 'Escaneo activo con atestación' only shows the level 'Avanzado' triggering the magic-link login: 'formulario → elige "Avanzado" → aparece el gate ... → (si no hay sesión) magic-link → de vuelta al escaneo'. The companion form §3.2 lists three levels (Básico/Intermedio/Avanzado) but never indicates that Intermedio also requires a session.
- **Spec:** Spec §1 ('Superficies que exigen sesión: Scans activos (intermedio/avanzado)') and §4 ('Scans activos (intermedio/avanzado): ... crea scans private con owner_user_id = el usuario de la sesión') state that BOTH intermedio AND avanzado require a session, and both also need the authorization gate (checkbox authorized=true).
- **Fix:** Edit product/design-prompt.md §4.2 (and the §3.2 level-card copy) to make the magic-link gate apply to BOTH 'Intermedio' and 'Avanzado' (active levels), not only 'Avanzado'. E.g. 'elige un nivel activo (Intermedio o Avanzado) → aparece el gate → (si no hay sesión) magic-link → de vuelta al escaneo'. This keeps the auth-trigger condition consistent with the attack-level surface decision.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §3.7 screen 3; spec §3 'Canje (GET /auth/callback?token=)' steps 2–3
- **Brief:** design-prompt §3.7 screen 3 ('Verificando') defines exactly three callback states: 'verificando / ok / token inválido o expirado'. The single error bucket 'token inválido o expirado' is the only failure state designed.
- **Spec:** Spec §3 (Canje, step 2 and 3) distinguishes three distinct failure conditions that all currently collapse into one UI state: (a) token not found / SHA256 mismatch (invalid), (b) expired (expires_at <= now), and (c) ALREADY CONSUMED — 'un segundo canje del mismo token falla por este chequeo' (consumed_at IS NOT NULL). A user who clicks an already-used link hits a real, separate path.
- **Fix:** Edit product/design-prompt.md §3.7 screen 3 to either (a) explicitly state the single error state must also cover an already-used/consumed link (e.g. 'token inválido, expirado o ya utilizado'), or (b) add an 'enlace ya usado' variant. As written a designer would not account for the one-use replay case.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.7 screen 2 ('reenvío + cooldown visible'); spec §2.2 + §3
- **Brief:** design-prompt §3.7 screen 2 ('Revisa tu correo') requires a 'cooldown visible' — i.e. the UI must display a concrete countdown/duration for the resend button being disabled.
- **Spec:** Spec §2.2 confirms the cooldown exists ('el botón de reenviar queda deshabilitado durante el cooldown para no permitir spam de correos') but gives NO numeric value. The spec specifies the token TTL (10 min, §3) but never the resend cooldown duration, so a designer cannot render the visible countdown the brief asks for.
- **Fix:** Extend product/features/11-auth-magic-link/spec.md §2 (or §3) to fix a concrete resend-cooldown duration (e.g. 60s) so the brief's 'cooldown visible' has a value to display. Note: the 10-min figure in §3 is the token TTL, not the resend cooldown — keep them distinct.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.7 / §3.8; spec §3 ('POST /auth/logout', 'GET /auth/me')
- **Brief:** design-prompt has no logout UI or session/account indicator anywhere; §3.7's four screens cover login only, and §3.8 watchlist (requires session) does not mention sign-out.
- **Spec:** Spec §3 specifies 'POST /auth/logout limpia la cookie' and 'GET /auth/me devuelve el usuario actual de la sesión', implying an authenticated app needs a way to sign out and surface the current user.
- **Fix:** Add a logout affordance + current-user indicator to product/design-prompt.md (most naturally in §3.8 watchlist or an authenticated app-shell note), so the session lifecycle defined by the spec (logout/me) has a UI home.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.7 (no routes listed); spec §2 'route-group (public)' + '/api/auth/*'
- **Brief:** design-prompt §3.7 is the only screen group that gives NO route paths (every other §3 section names a route, e.g. /scan, /scans/[id], /watchlist, /r/[token]).
- **Spec:** Spec §2 places the 4 auth screens in the route-group '(public)' (logo Owliver + CTA 'Escanear mi sitio', no sidebar) and ties them to the BFF pattern '/api/auth/*' (/api/auth/magic-link, /api/auth/callback). The callback specifically is GET /auth/callback?token=.
- **Fix:** Add the auth route paths and the '(public)' layout note (logo + 'Escanear mi sitio' CTA, no sidebar) to product/design-prompt.md §3.7 so the auth screens match the layout context the other screens already declare.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.7 screens 1–2; spec §2.1 + §3 'Emisión'
- **Brief:** design-prompt §3.7 screen 2 ('Revisa tu correo' — confirmation) shows a single confirmation with no 'este email no existe' error, and screen 1 only asks for an email + 'Enviar enlace'.
- **Spec:** Spec §2.1 and §3 require exactly this: 'El endpoint solo envía el correo; no abre sesión ni revela si el email existe' / 'La respuesta al cliente es indistinguible exista o no el email'. The brief's design correctly preserves account-enumeration privacy.
- **Fix:** No change. Confirm the design keeps a uniform 'Revisa tu correo' confirmation regardless of whether the email exists (no error branch on screen 1/2).

### 12-api

#### ➕ Falta en spec · **high**
- **Ubicación:** design-prompt §3.8 (líneas 220-225) vs 12-api/spec.md líneas 205-214 (Watchlist — CRUD)
- **Brief:** El brief §3.8 exige un control de alertas: "Ajustes de alertas (email / Slack)" en la watchlist, y el flujo 5 lo trata como parte de la vigilancia.
- **Spec:** El spec (sección "Watchlist — CRUD", líneas 205-214) solo define GET /watchlist, POST /watchlist {url, monitor} y DELETE /watchlist/{id}. No existe ningún endpoint para configurar canales de alerta (email/Slack) ni preferencias de notificación.
- **Fix:** Extender product/features/12-api/spec.md con un endpoint de configuración de alertas (p. ej. PUT/PATCH /watchlist/{id}/alerts {email_enabled, slack_webhook} o un recurso /alerts), cruzado con 08-ranking-watchlists. Si no es MVP, declararlo explícito y marcar el affordance del brief como fuera de alcance.

#### ➕ Falta en spec · **high**
- **Ubicación:** design-prompt §3.8 (líneas 220-224) y flujo 5 (línea 246) vs 12-api/spec.md líneas 209-214
- **Brief:** El brief §3.8 exige un "toggle de monitoreo (re-escaneo periódico)" por dominio que el usuario activa/desactiva tras agregar el sitio (flujo 5: "agrega dominio → activa monitoreo").
- **Spec:** El spec solo permite fijar el flag monitor en la creación: POST /watchlist {url, monitor} (línea 209). No hay PATCH/PUT /watchlist/{id} ni endpoint para alternar monitor en una fila existente; DELETE solo elimina.
- **Fix:** Añadir a 12-api/spec.md un PATCH /watchlist/{id} {monitor} (o equivalente) para que el toggle de la UI persista cambios. Sin esto, el toggle del brief no tiene endpoint de respaldo.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.1 (línea 115) vs 12-api/spec.md línea 32 y sección Paginación (líneas 236-243)
- **Brief:** El brief §3.1 especifica tres filtros en el leaderboard: "por grado, por peor dimensión (web/agéntico), por país (MX)".
- **Spec:** El spec documenta GET /ranking?country=mx (línea 32) y paginación por cursor, pero solo nombra el filtro country. No menciona query params para filtrar por grado (A-F) ni por dimensión (web/agéntico).
- **Fix:** Añadir en 12-api/spec.md los query params del ranking que el brief implica, p. ej. GET /ranking?country=mx&grade=F&worst_dimension=agentic. Si el filtrado es client-side sobre la página actual, decirlo explícitamente (afecta paginación).

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §3.2 (líneas 124, 130) vs 12-api/spec.md líneas 22, 71-116
- **Brief:** El brief §3.2 muestra el "host detectado" al validar la URL y §3.3 muestra el chatbot detectado (vendor + modelo inferido); el formulario quiere previsualizar/validar el host antes de encolar.
- **Spec:** El spec solo expone POST /scans {url, level, authorized} (líneas 22, 71-73), que ya encola el job. No hay endpoint de validación/preview de URL ni de detección de host previo al encolado.
- **Fix:** El parseo de host puede ser client-side, pero si la UI necesita confirmar is_gov/host normalizado antes del gate de atestación, documentar en 12-api/spec.md cómo se obtiene (derivado en POST /scans con 422, o GET /scans/preview?url=). Confirmar si no se requiere endpoint nuevo.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.5 (líneas 202-203) y §6 (línea 268) vs 12-api/spec.md líneas 224-226, 259-260
- **Brief:** El brief §3.5 describe el reporte público /r/[token] con dos estados de error: link inexistente → 404; link expirado/revocado → pantalla "Este enlace expiró", colapsando ambos bajo un solo copy.
- **Spec:** El spec distingue dos códigos: token inexistente → 404; token expirado o revocado → 410 Gone (líneas 224-226, 259-260), reservando 410 para expirado/revocado. El brief §6 sí lista 404/410/422 en deliverables, pero §3.5 no separa el copy por código.
- **Fix:** En design-prompt §3.5 separar los dos estados: 404 ("Este enlace no existe") vs 410 ("Este enlace expiró"), alineando el copy con el código HTTP del spec para que el dev mapee el status correctamente.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §3.2 (líneas 129-136) vs 12-api/spec.md líneas 22, 73, 84
- **Brief:** El brief §3.2 nombra el control legal como "Checkbox obligatorio: Declaro tener autorización para auditar este dominio" (concepto: atestación/autorización).
- **Spec:** El spec nombra ese dato como el campo authorized del body POST /scans {url, level, authorized} (líneas 22, 73), y aclara que en gov+activo el endpoint responde 422 "ignorando el checkbox authorized" (línea 84).
- **Fix:** Anotar en design-prompt §3.2 que el checkbox de atestación mapea al campo de request authorized, para evitar que el dev invente otro nombre (attested/consent) al cablear el formulario al endpoint.

#### ➕ Falta en brief · **low**
- **Ubicación:** 12-api/spec.md líneas 81-84, 116 vs design-prompt §3.2 (línea 136)
- **Brief:** El brief §3.2 dice que para gov + nivel activo se muestra un error inline "Los sitios gob.mx solo admiten escaneo pasivo", como validación de UI.
- **Spec:** El spec especifica que ese caso es un 422 del backend que ignora el checkbox authorized (is_gov && level != basico → 422, líneas 81-84, 116, 258). El brief no menciona que el backend re-aplica la regla con 422 aunque la UI la deje pasar.
- **Fix:** En design-prompt §3.2 añadir el estado de error servidor 422 (gov+activo) como respuesta posible del submit, no solo la validación client-side, para que la UI maneje el rechazo del backend tras un bypass del formulario.

#### ➕ Falta en brief · **low**
- **Ubicación:** 12-api/spec.md líneas 110-116, 261-262 vs design-prompt §3.2 (línea 138) y flujo 1 (líneas 236-237)
- **Brief:** El brief §3.2 trata el envío como un solo resultado: "al enviar → redirige a la pantalla de escaneo en vivo".
- **Spec:** El spec define dos éxitos para POST /scans: 201 (scan nuevo encolado) y 200 (hit idempotente: ya existía un scan queued/running para (site_id, level), devuelve el scan_id existente) (líneas 110-116, 261-262). La UI debe manejar el caso idempotente.
- **Fix:** En design-prompt §3.2 documentar que un re-submit del mismo (host, nivel) puede devolver un scan ya en curso (200 idempotente) y la UI debe redirigir al theater existente, no asumir siempre un scan nuevo.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.3 (líneas 163-164) y flujo 3 (líneas 242-243) vs 12-api/spec.md líneas 160-176
- **Brief:** El brief §3.3 describe que "al recargar la página, el progreso se repinta completo (no queda vacío) — diséñalo asumiendo replay", reforzado por el flujo 3.
- **Spec:** El spec respalda esto: GET /scans/{id}/stream es replay-then-tail — lee el cursor Last-Event-ID/?since_seq=, hace replay desde Postgres de los scan_events con seq > cursor y luego hace tail del canal (líneas 160-176). La verdad vive en Postgres.
- **Fix:** Sin cambios: el replay del brief está respaldado endpoint-a-endpoint. Confirmar que la UI use el cursor SSE (Last-Event-ID / since_seq) como describe el spec.

### 13-frontend

#### ➕ Falta en brief · **high**
- **Ubicación:** design-prompt §3.7 ('Magic-link · Auth (4 pantallas)') vs spec §F3 (lines 91-93) and §F10 (lines 229-236)
- **Brief:** The brief describes the magic-link auth flow as 4 screens (1. Pedir email, 2. 'Revisa tu correo', 3. Verificando/callback, 4. Sesión iniciada) but assigns NO route paths to any of them.
- **Spec:** §F3 route table + §F10 assign explicit routes: `/login` (pedir email), `/login/check-email` (revisa tu correo), `/auth/callback` (verify/callback). Screen 4 'Sesión iniciada' is a post-login redirect, not a standalone route.
- **Fix:** Edit product/design-prompt.md §3.7 to add the route paths next to each screen: `/login`, `/login/check-email`, `/auth/callback`, and clarify that 'Sesión iniciada' (screen 4) is a redirect outcome of the callback (no own route). This prevents a designer from inventing route paths that diverge from the spec/router.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §6 (Entregables, mini design system) vs spec §F13 (line 270)
- **Brief:** The brief's component inventory (§6) lists 9 reusable components: GradeBadge, SeverityChip, Gauge, ToolChip, AgentLane, FindingFeedItem, AttestationGate, OwlMascot, barra de progreso de escaneo. It omits StatusBadge as a named component even though §3.1/§3.4 repeatedly reference the badges 'IA detectada, sin auditar' and 'cobertura parcial'.
- **Spec:** §F13 component table defines **StatusBadge** (custom) explicitly for '"IA detectada, sin auditar", "cobertura parcial"'.
- **Fix:** Edit product/design-prompt.md §6 to add StatusBadge to the named reusable component list, so the two recurring badges become a documented, reusable component rather than ad-hoc per-screen styling.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §6 and §3.3 vs spec §F13 (line 277)
- **Brief:** The brief names the scan progress component generically: 'barra de progreso de escaneo' (§6) / 'barra de progreso 0-100' (§3.3).
- **Spec:** §F13 names this component **LiveProgress** (custom) = 'barra 0–100 + current_phase + timer'.
- **Fix:** Edit product/design-prompt.md §6 to name the component 'LiveProgress' so design and dev share one component name; the spec already binds it to the phase label + timer composition.

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §3.3 (OWASP Scanner chip list / Agentic Surface Auditor) vs spec §F6 (lines 160-161, 181)
- **Brief:** The brief lists OWASP theater tool chips as 'nuclei, zap, testssl, nikto, sqlmap…' (§3.3) and the agentic auditor references 'cada probe lanzado', but the brief never names garak/promptfoo for the agentic lane, while it shows nikto/sqlmap on the web lane.
- **Spec:** §F6 lists the same web tools 'nuclei, zap, testssl, nikto, sqlmap…' (matches), and §F6 'Wow' references 'garak full' as a heavy tool shown from pre-baked results. The agentic lane in §F6 is described by phases (detección → inventario → sondas), not by named ToolChips — consistent with the brief.
- **Fix:** Low-priority: optionally align by noting in design-prompt §3.3 that the agentic lane uses phase indicators (not ToolChips) and that heavy tools (ZAP full, garak) appear from pre-baked results — matching spec §F6 'demo-level' guidance. The web tool list itself already matches; no contradiction.

#### ➕ Falta en brief · **low**
- **Ubicación:** design-prompt §3.2 (Formulario de escaneo) vs spec §F5 (line 138)
- **Brief:** The brief's scan form (§3.2) only sketches the gate appearing 'SOLO si el nivel es activo' and inline gov error, but does not mention that an active level requires a session (redirect to magic-link saving pending destination).
- **Spec:** §F5 (line 138): 'Nivel activo requiere sesión → si no hay, redirige a magic-link guardando el destino pendiente (§F10).' The brief covers this only in flow §4.2, not in the §3.2 screen spec itself.
- **Fix:** Edit product/design-prompt.md §3.2 to add the 'active level requires session → magic-link redirect with pending destination' behavior to the form screen states, so the form's auth-gating state is designed (not only implied by flow §4.2).

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §3.1–3.8 vs spec §F3 (lines 85-94)
- **Brief:** Brief routes match the spec route table exactly: leaderboard `/` (§3.1), scan `/scan` or modal (§3.2), theater `/scans/[id]` (§3.3), report `/scans/[id]/report` (§3.4), public report `/r/[token]` (§3.5), site history `/sites/[id]` (§3.6), watchlist `/watchlist` (§3.8).
- **Spec:** §F3 route table (lines 85-94) defines identical paths and the 'or modal en /' note for `/scan`.
- **Fix:** No change needed — strong alignment on all primary route paths including the `/scan`-or-modal note. Confirm router scaffolding uses these exact segments.

### product-overview

#### ❌ Contradicción · **high**
- **Ubicación:** design-prompt §2 (palette block, line 'Acento (ámbar, ojos del búho): oklch(0.78 0.15 75)') and §3.1 'CTA primario (ámbar)'; DESIGN.md §2 Primary + Named Rules, §6 Don'ts; frontend/src/app/globals.css L198-199, L215.
- **Brief:** design-prompt §2 introduces an amber/gold accent "los ojos del búho" oklch(0.78 0.15 75) used "para CTAs y acentos vivos", and §3.1 specifies the primary CTA "Audita cualquier URL →" as amber ("CTA primario (ámbar)").
- **Spec:** DESIGN.md §2 / §6 'The One Light Rule': the single primary-action color is Doxiq Teal (oklch(0.59 0.095 180.54)); primary buttons are 'solid Doxiq Teal'. The closest amber token in the live system is --warning oklch(0.77 0.18 75.998), explicitly 'used to draw a reviewer's eye, not to alarm' — never a CTA/identity accent. There is no amber accent token in globals.css (--accent is teal-tint oklch(0.951 0.018 186.07)).
- **Fix:** Reconcile the brand accent in the design system. If amber 'owl-eyes' is intentional for Owliver, add it as a first-class token (e.g. --accent-owl) to frontend/src/app/globals.css and document it in DESIGN.md §2, AND decide whether it (not teal) is the primary CTA color — currently the live system forbids non-teal CTAs. Otherwise change design-prompt §2/§3.1 to make the primary CTA teal and demote amber to an accent only.

#### ⚠️ Drift · **high**
- **Ubicación:** design-prompt §2 line 55 (amber accent); frontend/src/app/globals.css L215 (--warning); DESIGN.md frontmatter 'warning'.
- **Brief:** design-prompt §2 gives the amber accent the value oklch(0.78 0.15 75).
- **Spec:** The live amber-family token is --warning oklch(0.77 0.18 75.998) (globals.css L215) with readable shade --warning-deep oklch(0.47 0.1 65). DESIGN.md frontmatter warning: oklch(0.77 0.18 75.998). The brief's lightness (0.78), chroma (0.15) and hue (75) all differ from the live amber.
- **Fix:** Pick one amber value. Either update design-prompt §2 to the live oklch(0.77 0.18 75.998), or, if a distinct owl-eye amber is wanted, register the exact value in globals.css + DESIGN.md so designers/devs don't ship two near-identical ambers.

#### ➕ Falta en spec · **high**
- **Ubicación:** design-prompt §2 (grade scale block, lines 70-79) and §6 deliverables (GradeBadge); frontend/src/app/globals.css :root (no grade vars); DESIGN.md §2 Colors.
- **Brief:** design-prompt §2 defines a full A–F grade color scale (A oklch(0.72 0.16 150), B oklch(0.75 0.15 130), C oklch(0.80 0.14 90), D oklch(0.72 0.16 55), E oklch(0.66 0.19 35), F oklch(0.58 0.22 25)) as 'única fuente de color para chips, gauges y filas', plus components GradeBadge/Gauge that depend on it.
- **Spec:** Not covered. globals.css defines no grade tokens (only --chart-1..5, --success, --warning, --destructive). The brief's A-green (0.72 0.16 150) differs from --success oklch(0.626 0.139 155.038) and F-red (0.58 0.22 25) differs from --destructive oklch(0.579 0.214 27.166), so they are genuinely new tokens, not reuses. DESIGN.md does not mention an A-F scale.
- **Fix:** Add the 6 A–F grade tokens to frontend/src/app/globals.css (e.g. --grade-a..--grade-f) and document them as a named scale in DESIGN.md §2, so the design system is the single source rather than the brief. Confirm whether grade-A reuses --success and grade-F reuses --destructive or stays independent.

#### ⚠️ Drift · **high**
- **Ubicación:** design-prompt §1-§2 (whole brand + mascot section); DESIGN.md frontmatter 'name: Doxiq' + §1; PRODUCT.md §Product Purpose, §Brand Personality.
- **Brief:** design-prompt is fully Owliver-branded (owl mascot 🦉 with 3 states 'dormido/vigilando/alerta' in §2, north star 'La mesa de inspección', anti-references) and is the brief designers will build from.
- **Spec:** The live design system root files have NOT been rebranded from the boilerplate: DESIGN.md frontmatter 'name: Doxiq', §1 'Doxiq is a workstation for examining documents', signature component is 'Confidence & Provenance' for 'extracted values'; PRODUCT.md describes 'Doxiq (by Llamitai)… document review'. Neither mentions an owl mascot or pentesting. globals.css is product-agnostic so its tokens still apply.
- **Fix:** Rebrand PRODUCT.md and DESIGN.md to Owliver via the /impeccable skill: rename, replace the document-review narrative with the pentest/inspection-bench framing, and add the OwlMascot (3 states) as a documented signature component so the design system matches the brief designers are handed.

#### ➕ Falta en spec · **medium**
- **Ubicación:** design-prompt §2(B) (SOC block, lines 58-68) and §3.3 Live Pentest Theater; frontend/src/app/globals.css .dark L233-276; DESIGN.md (no SOC section).
- **Brief:** design-prompt §2(B) defines a dark 'Live-view / theater / SOC war-room' palette (near-black oklch(0.16 0.02 250), scanlines oklch(0.24 0.02 250), cyan oklch(0.80 0.13 195), amber oklch(0.80 0.14 75), red oklch(0.64 0.22 25)) that 'conviven' with the light shell and is explicitly NOT a user toggle, applied only to the live-scan screen.
- **Spec:** Not covered as a SOC palette. globals.css has a generic .dark theme (--background oklch(0.178 0.02 253.03)) intended as a standard dark mode, not a one-screen SOC theater; its background differs from the brief's near-black oklch(0.16 0.02 250) and it defines no cyan/scanline/neon tokens. DESIGN.md describes only the light bench.
- **Fix:** Extend the design system: add a dedicated SOC/theater token group to globals.css (scoped to the live-view route, not the global .dark) and document it in DESIGN.md as a separate mode, so the theater palette has an authoritative home. Align the near-black to one value (brief 0.16 vs .dark 0.178).

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §2 line 89 ('Radio base ~12px'); frontend/src/app/globals.css L210 (--radius) and L170-176 (radius ramp); DESIGN.md §5 Components (rounded-md/rounded-xl).
- **Brief:** design-prompt §2 states 'Radio base ~12px' and components imply ~12px corners across cards/badges/buttons.
- **Spec:** globals.css --radius: 0.75rem (12px) confirms the base, BUT DESIGN.md §5 sets cards to rounded-xl (16px) and buttons/inputs/badges to rounded-md (10px); no top-level surface uses a literal 12px. The brief's flat '~12px base' could lead a designer to round everything to 12px and lose the 10/16 step the live system uses.
- **Fix:** In design-prompt §2, note that 12px is the --radius base and that components step around it (buttons/inputs/badges ~10px, cards ~16px) per DESIGN.md §5, rather than a single 12px applied everywhere.

#### ✅ Alineado · **low**
- **Ubicación:** design-prompt §1-§2; PRODUCT.md §Brand Personality/§Anti-references; DESIGN.md §1/§3; product/spec.md §17 line 258; globals.css L180-192.
- **Brief:** design-prompt §1-§2 brand personality 'afilada, confiable, cercana', north star 'La mesa de inspección (the inspection bench)', anti-references (plantillas SaaS genéricas / look IA trendy y morado / enterprise legacy), tagline 'Owliver vigila la seguridad del Estado y de tu IA — lo que nadie más está midiendo', plus Figtree + Geist Mono typography.
- **Spec:** Strongly aligned: PRODUCT.md 'sharp, trustworthy, approachable' + identical anti-references; DESIGN.md 'The Inspection Bench' + same three rejected looks + Figtree/Geist Mono; spec.md §17 closing line matches the tagline verbatim; globals.css --font-sans Figtree / --font-geist-mono Geist Mono. Core tokens primary/ink/surface/card match exactly.
- **Fix:** No change needed — confirm these stay locked; the only brand gap is the Doxiq→Owliver rename and the amber/grade/SOC token additions noted above.

### cross-cutting

#### ❌ Contradicción · **high**
- **Ubicación:** design-prompt §3.2 (lines 134-136) vs 01-legal-ethics §2.4 (lines 96-100) AND §1 (lines 39-40); vs 02-attack-levels §3 (line 36) AND §4 (lines 94-98); vs 12-api §116 (line 116) AND §258 (line 258)
- **Brief:** Brief §3.2: gob.mx + active level is BLOCKED — reinforced red warning 'el escaneo activo automático está prohibido; solo se permite pasivo' + a blocking inline error 'Los sitios gob.mx solo admiten escaneo pasivo.' The 01-legal-ethics auditor flagged this as WRONG (gov+active should be non-blocking).
- **Spec:** The two specs that own this rule CONTRADICT EACH OTHER. 01-legal-ethics §2.4 + §1 'descartada' say gov+active is NON-blocking ('puede proceder bajo su responsabilidad'). 02-attack-levels §3 line 36 agrees. BUT 12-api §116/§258 says gov+active = hard 422 ('is_gov && level != basico → 422, ignorando el checkbox authorized') and 02-attack-levels §4 lines 94-98 says the worker whitelist gives a gov target ONLY passive tools so it 'ni siquiera tiene la opción de lanzar un activo'. So 02-attack-levels contradicts ITSELF (§3 non-blocking vs §4 tool-deny), and 01-legal vs 12-api directly disagree on whether gov+active is blockable.
- **Fix:** MISSED CROSS-SPEC CONFLICT. The 01-legal-ethics auditor's finding #1 (which tells you to REMOVE the brief's blocking error) is unsafe to act on because 12-api makes gov+active a hard 422 and 02-attack §4 denies the tools. Reconcile the specs FIRST: decide whether USER-initiated gov+active is (a) blocked at the API (422, matching brief + 12-api + 02-attack §4) or (b) allowed under user responsibility (matching 01-legal + 02-attack §3). Edit 01-legal-ethics §1/§2.4 and 02-attack-levels §3 vs §4 to agree, then make the brief match the winner. The brief's blocking UI is currently CONSISTENT with 12-api, so do NOT delete it before the specs are aligned. Supersedes legal-ethics finding #1.

#### ❌ Contradicción · **high**
- **Ubicación:** design-prompt §3.3 (lines 160-162) vs 10-realtime §2 (lines 42-43, 57); reconciled by 13-frontend §F6 (line 167) + 06-data-model (line 102) + 12-api (line 180)
- **Brief:** Brief §3.3 defines a 'cancelado' Theater state and 'Botón Cancelar (mata el escaneo)'. The 10-realtime auditor flagged this HIGH (no 'cancelled' value in the SSE event-type enum) and recommended ADDING a 'cancelled' terminal discriminator to 10-realtime §2.
- **Spec:** The 'cancelado' state IS already backed; the 10-realtime auditor missed the reconciliation. 06-data-model line 35/102 has scans.status ENUM(...,cancelled); 12-api line 29/180 defines POST /scans/{id}/cancel; and 13-frontend §F6 line 167 RESOLVES the transport: cancel emits a terminal 'done' event with {outcome:'cancelled'}, NOT a new event type. So the 10-realtime auditor's proposed fix (add a 'cancelled' discriminator) CONTRADICTS 13-frontend's already-chosen contract (reuse 'done' + outcome field).
- **Fix:** Do NOT add a 'cancelled' discriminator to 10-realtime §2 as that auditor suggested — it would diverge from 13-frontend §F6 which specifies cancel = terminal 'done' event carrying {outcome:'cancelled'}. Instead fix the real gap: 10-realtime §2 must document the 'outcome' field on the 'done' event (completed | cancelled) so the typed schema matches 13-frontend. The brief's 'cancelado' UI state is correct; its source of truth is done.outcome, not a new event type.

#### ⚠️ Drift · **high**
- **Ubicación:** design-prompt §2 (lines 45-89) vs 13-frontend §F2 (lines 23, 45-72); the auditor cited DESIGN.md/globals.css instead
- **Brief:** The product-overview auditor raised SIX findings (amber not a token / amber value drifts / A-F scale not covered / SOC palette not covered / Doxiq-not-Owliver / radius) by checking design-prompt §2 against DESIGN.md + frontend/src/app/globals.css.
- **Spec:** The product-overview auditor checked the WRONG owning spec. Owliver's tokens are owned by 13-frontend §F2, NOT the boilerplate DESIGN.md/globals.css. 13-frontend §F2 lines 45-72 ALREADY define: --ow-accent oklch(0.78 0.15 75) ('ámbar — ojos del búho, CTAs vivos') EXACT match to brief line 55; the full SOC group --soc-bg oklch(0.16 0.02 250) … --soc-hit oklch(0.64 0.22 25) EXACT match to brief §2(B); and the complete A–F grade scale with identical oklch values + the grade-C 'cap de cobertura parcial' note. 13-frontend §F2 line 23 EXPLICITLY states DESIGN.md/globals.css are 'del boilerplate Doxiq, no de Owliver'. So brief and 13-frontend AGREE; the boilerplate divergence is already acknowledged.
- **Fix:** Down-scope 5 of 6 product-overview findings: amber, SOC, and grade-scale are NOT gaps-in-spec — they are owned and value-matched by 13-frontend §F2. The real cross-cutting issue is IMPLEMENTATION drift: globals.css/DESIGN.md still ship Doxiq tokens, so 13-frontend §F2's --ow-*/--soc-*/--grade-* tokens are not yet materialized in code. Keep the Doxiq→Owliver rebrand finding (real, 13-frontend §F2 line 23 calls for it); reframe amber/SOC/grade as 'implement 13-frontend §F2 tokens in globals.css', not 'add to DESIGN.md'.

#### ❌ Contradicción · **high**
- **Ubicación:** design-prompt §3.4 (line 174) + §3.1 (line 111) vs 07-scoring §5.1 (line 70) + §6 (line 92) vs 13-frontend §F7 (line 191) + 08-ranking §2.4 (line 58)
- **Brief:** Brief §3.4/§3.1 show per-dimension letter grades — 'dos gauges … con el score numérico + grado al centro' and the SAT row 'C web / F agéntico'. The 07-scoring and 13-frontend auditors touched this but neither flagged the cross-spec conflict.
- **Spec:** 07-scoring §5.1 line 70 derives the A–F grade ONLY from overall_score, and §6 line 92 says 'La columna de grado se llama overall_grade en todas partes' — exactly ONE grade; web_score/agentic_score have NO per-dimension grade formula. BUT 13-frontend §F7 line 191 renders the gauge 'Label central con score + grado' and 08-ranking §2.4 line 58 bakes the fixture 'SAT con C web / F agéntico'. So 13-frontend + fixtures ASSUME per-dimension sub-grades that 07-scoring does not define.
- **Fix:** Resolve in 07-scoring (the grade authority): add a normative rule projecting web_score and agentic_score each onto the §5.1 A–F scale, validating 'C web / F agéntico' (13-frontend §F7 + 08-ranking fixture + brief). If NO sub-grades are intended, then 13-frontend §F7 line 191, 08-ranking line 58, AND brief §3.4/§3.1 must all drop per-dimension letters and show numbers only. This is ONE decision that must propagate to 3 specs + the brief.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.1/§3.3/§3.4 vs 06-data-model line 99, 07-scoring §4/§5.2, 08-ranking §2.1 line 39, 13-frontend §F2 line 69 + §F4 line 116
- **Brief:** Four auditors raised 'cobertura parcial' findings as if undefined/one-dimensional: 08-ranking (HIGH: brief never states grade capped at C), 07-scoring (MEDIUM: no max-grade), 06-data-model (LOW: status=partial vs coverage jsonb), 03-agentic (LOW: not defined for agentic surface).
- **Spec:** The concept is fully and consistently defined across specs. 06-data-model line 99 scans.status='partial' = '≥1 scanner base faltó'; 07-scoring §4/§5.2 lines 60/79 caps grade at C; 08-ranking §2.1 line 39 'nunca muestra A con cobertura parcial … se capa en C'; 13-frontend §F4 line 116 'Badge cobertura parcial cuando aplica el cap-C' + §F2 line 69 ties grade-C to the cap. Only the 03-agentic angle (partial coverage of the AGENTIC surface, distinct from scanner-partial) is genuinely uncovered.
- **Fix:** DEDUP these four into ONE: 'cobertura parcial' = scans.status='partial' → grade capped at C, already in 06/07/08/13. The brief only needs the visual cap (badge paired with a C-or-worse GradeBadge, never A/B), which 13-frontend §F4 line 116 already states — so the gap is brief-side only. Keep ONLY the 03-agentic question (separate 'partial AGENTIC coverage'?) as a real gap-in-spec. The 08-ranking HIGH and 07-scoring MEDIUM are severity-inflated since 13-frontend §F4 already designs the cap.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.1 vs 13-frontend §F4 (lines 112-121); auditors checked 08-ranking §2.1 / 07-scoring §2 / 12-api §32 only
- **Brief:** Several auditors raised brief 'gaps' actually covered by 13-frontend (the surface spec) but checked against contract specs only: 08-ranking 'filters not in spec' (MEDIUM), 08-ranking 'double-meter row not in spec' (MEDIUM), 08-ranking 'empty state contradicts fixtures' (LOW), 07-scoring 'numeric scores displayed not confirmed' (MEDIUM), 12-api 'leaderboard filters have no query params' (MEDIUM).
- **Spec:** 13-frontend §F4 lines 112-121 OWNS the leaderboard surface: filters 'por grado, por source peor (web/agéntico), por país (MX)' (line 119) match the brief; per-row dual meter 🛡️/🤖 (lines 113-115); 'empty solo teórico (fixtures garantizan poblado)' (line 121) matches fixtures, NOT a contradiction; gauges with 'score + grado' = numeric scores displayed. 12-api §32 documents only ?country=mx.
- **Fix:** Reconcile across the 3 layered specs: 13-frontend §F4 already draws grade + worst-dimension + country filters, so the real residual gap is that 12-api §32 only documents ?country=mx — add one line to 12-api §32 stating where grade/worst-dimension filtering happens (backend params vs client-side over cursor page). DROP the 08-ranking 'empty state' finding (13-frontend line 121 confirms fixtures = never empty). Downgrade the 07-scoring numeric-display finding to ok-note (satisfied by 13-frontend §F7 line 191).

#### ❌ Contradicción · **medium**
- **Ubicación:** design-prompt §3.9 (lines 227-232) + §3.5 (line 203) vs 13-frontend §F14-1 (line 285); 09-reporting auditor said 'no coverage'
- **Brief:** ORPHAN flagged by 09-reporting auditor (LOW gap-in-spec): the Report Card / OG share image (brief §3.9, referenced by §3.5) is 'unowned'.
- **Spec:** It is NOT unowned — the 09-reporting auditor missed that 13-frontend §F14-1 line 285 FULLY owns it: '🎴 Report Card compartible (OG image) … vía next/og (opengraph-image.tsx en /r/[token] y /sites/[id]) … con la F roja bien visible. Hook viral #1. Recorte: tras §F8.' It has a home, mechanism, fields, two routes, and cut-priority. The only un-fixed detail is restating the redaction rule on the OG image.
- **Fix:** Correct the 09-reporting finding: the Report Card IS owned by 13-frontend §F14-1, not orphaned. Residual gap is narrow: add one line to 13-frontend §F14-1 (or cross-ref 09-reporting) confirming the OG image follows the redaction rule (executive grade only, no exploit payloads). Also note brief §3.9 attaches the card only to /r/[token] while 13-frontend §F14-1 also attaches it to /sites/[id] — align the brief to mention /sites/[id].

#### ❌ Contradicción · **medium**
- **Ubicación:** design-prompt §3.4 (line 188) vs 09-reporting §2.2 line 47 vs 13-frontend §F4 line 119 vs 06-data-model line 123
- **Brief:** Brief §3.4 finding-panel filters are 'por severidad / dimensión / categoría' (line 188). The 09-reporting auditor flagged this as drift vs its spec's 'severidad / source / categoría'.
- **Spec:** Two specs disagree on the middle facet name AND it collides with the leaderboard facet. 09-reporting §2.2 line 47 says 'source'; 13-frontend §F4 line 119 leaderboard filter is 'por source peor (web/agéntico)' — treating Web/Agéntico (the user-facing 'dimensión') as a presentation of `source`; 06-data-model line 123 confirms findings.source ∈ owasp|agentic IS the Web-vs-Agéntico dimension. So 'dimensión' (brief), 'source' (09-reporting), and 'source peor → web/agéntico' (13-frontend) are the SAME facet under three labels.
- **Fix:** Standardize one term across all three: persisted field is findings.source (06-data-model), user-facing label is the Web/Agéntico 'dimensión'. Say 'por dimensión (source: Web/Agéntico)' consistently — update 09-reporting §2.2 to add the 'dimensión' alias and keep the brief's 'dimensión'. One terminology fix spanning 09-reporting + 13-frontend + brief, not a per-domain drift.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §6 (line 268) + §3.5 vs 12-api §259-260, 06-data-model §3.8 line 185, 09-reporting §5.1 lines 92-93 + §5.2 line 103, reconciled by 13-frontend §F16 line 254
- **Brief:** Brief §6 lists report public-error states as '404/410/422'. Both 06-data-model and 09-reporting auditors separately flagged that 422 has no place in the public-report flow and that 403 (not 422) is the toast case.
- **Spec:** Three specs together pin the truth and the brief conflates two unrelated error sets. For /r/{token}: 12-api §259-260 + 06-data-model §3.8 line 185 + 09-reporting §5.1 lines 92-93 all agree — 404 (inexistente) and 410 Gone (expirado/revocado). 422 belongs ONLY to POST /scans (12-api §116/§258). 403 is the toast on consumption (09-reporting §5.2 line 103). 13-frontend §F16 line 254 ALREADY maps all four correctly: '422 (gov/validación → inline en el form), 404 …, 410 (token expirado), 403 (toast)'.
- **Fix:** DEDUP the 06-data-model and 09-reporting findings: the correct mapping already exists in 13-frontend §F16 line 254. Fix the BRIEF: in §3.5 split 404 ('Este enlace no existe') vs 410 ('Este enlace expiró'), and in §6 scope 422 to scan-submission and add 403 to the report-consumption toast — exactly as 13-frontend §F16 spells out. No spec change beyond making the brief mirror 13-frontend §F16.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §3.3 (line 156) + §3.4 (line 182) AND 13-frontend §F6 (line 162) vs 03-agentic §1 line 18 + §5.1 line 125
- **Brief:** Brief §3.3/§3.4 chips/panels use the full taxonomy '(OWASP A01–A10 / LLM01–LLM10)'. The 03-agentic auditor flagged this HIGH drift (engine only emits LLM01/LLM02/LLM06).
- **Spec:** Brief and 13-frontend AGREE on the full range, so this is not brief-vs-spec drift — it is a category-coverage question for the engine spec. 13-frontend §F6 line 162 independently uses 'categoría OWASP A01–A10 / LLM01–LLM10'; 03-agentic §1 line 18 names only 'LLM01, LLM02, LLM06, etc.' with §5.1 line 125 mapping techniques to LLM01/LLM06 only. So the UI (brief + 13-frontend) promises a 10-bucket filter the agentic engine can only partially fill.
- **Fix:** Needs a 03-agentic spec decision, not just a brief edit: either (a) 03-agentic enumerates which LLM categories the engine emits so the LLM01–LLM10 filter has real buckets, or (b) the brief AND 13-frontend §F6 both narrow the chip taxonomy to categories actually produced. The fix must touch BOTH the brief and 13-frontend §F6 (same string), which the single-domain 03-agentic finding did not flag.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §2 (lines 55, 66, 75) + §3.1 (line 105) internally; resolved by 13-frontend §F2 (lines 49, 59, 69)
- **Brief:** INTERNAL design-prompt contradiction: §2/§3.1 make the PRIMARY CTA amber ('CTA primario (ámbar)'), while §2 also assigns amber to grade-C ('C ámbar oklch(0.80 0.14 90)') AND to the SOC 'tool corriendo' state. Three ambers carry three meanings within one brief.
- **Spec:** 13-frontend §F2 distinguishes them with separate tokens: --ow-accent oklch(0.78 0.15 75) for CTAs (line 49), grade-C oklch(0.80 0.14 90) (line 69), --soc-tool oklch(0.80 0.14 75) for running tools (line 59). Near-identical hues, DIFFERENT roles — a designer reading only the brief could collapse them and make a C-grade chip look like a CTA, or a running-tool chip look like a grade.
- **Fix:** Add a note to design-prompt §2 (mirroring 13-frontend §F2) that the three ambers are SEPARATE tokens with non-overlapping roles: --ow-accent (CTA/owl-eyes), grade-C (only inside GradeBadge/gauge), --soc-tool (only inside ToolChip in the SOC theater). Otherwise the brief's own palette is internally ambiguous even though 13-frontend disambiguates it.

#### ➕ Falta en brief · **medium**
- **Ubicación:** design-prompt §6 (lines 264-266) vs design-prompt §3.1/§3.4/§3.9 internally; resolved by 13-frontend §F13 (lines 268-285)
- **Brief:** INTERNAL design-prompt inconsistency: §6 'Entregables' names exactly 9 reusable components but the §3 screens reference components §6 omits — the badges 'IA detectada, sin auditar' / 'cobertura parcial' (§3.1, §3.4) and the Report Card (§3.9).
- **Spec:** 13-frontend §F13 component table lines 268-285 names the missing pieces: StatusBadge (line 270, custom — the two badges), LiveProgress (line 277, = brief's 'barra de progreso'), and Report Card OG (§F14-1 line 285). So the brief's §6 inventory is incomplete relative to its own §3 screens and to 13-frontend §F13.
- **Fix:** Sync brief §6 with 13-frontend §F13: add StatusBadge (the two badges §3 already uses), rename 'barra de progreso de escaneo' to LiveProgress (13-frontend §F13 line 277), and list the Report Card as a deliverable component. Removes the §3-vs-§6 internal mismatch and aligns names with the dev-facing 13-frontend §F13 table.

#### ⚠️ Drift · **medium**
- **Ubicación:** design-prompt §4 flow 2 (lines 239-241) + §3.2 (lines 124-129) internally; vs 11-auth §header line 12 + 13-frontend §F5 line 138
- **Brief:** INTERNAL design-prompt inconsistency on active-level→session trigger. §4 flow 2 names ONLY 'Avanzado' as triggering magic-link, while §3.2 lists three levels and never says Intermedio needs a session. The 11-auth and 13-frontend auditors each flagged half.
- **Spec:** Both active levels require a session: 11-auth §header line 12 'scans activos (intermedio/avanzado) requieren sesión'; 13-frontend §F5 line 138 'Nivel activo requiere sesión → redirige a magic-link'; 02-attack-levels confirms intermedio+avanzado are the active set. So §4 flow 2's 'Avanzado'-only framing is internally inconsistent with §3.2's level set and understates the trigger.
- **Fix:** Edit design-prompt §4 flow 2 and §3.2 so the gate + magic-link apply to BOTH active levels: 'elige un nivel activo (Intermedio o Avanzado) → gate → (si no hay sesión) magic-link'. MERGE the 11-auth and 13-frontend single-domain findings — they describe the same brief defect from two sides.

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §3.1 (lines 101-102) vs 13-frontend §F4 line 109 + 08-ranking §2.4 (lines 54-61)
- **Brief:** ORPHAN copy/number: brief §3.1 hero counter '128 sitios auditados · 41 reprobados (grado F)' — no per-domain auditor checked whether these numbers are owned or consistent with fixtures.
- **Spec:** 13-frontend §F4 line 109 reproduces the exact copy as the leaderboard hero, sourcing the counter from fixtures (08-ranking §2.4 seeds 30-50 rows). So the copy is owned, but the literal '128/41' is illustrative and numerically inconsistent with the seed (08-ranking says 30-50, not 128).
- **Fix:** Minor: the hero counter must be data-driven from the actual ranking/fixture count, not hardcoded — 08-ranking §2.4 seeds 30-50 rows, so '128 sitios' is inconsistent. Note in brief §3.1 (and 13-frontend §F4) that the counter binds to GET /ranking totals; keep '128/41' only as placeholder copy.

#### ⚠️ Drift · **low**
- **Ubicación:** design-prompt §3.3 (line 148) vs 04-scanning §10 + 02-attack §3.1 line 60, reconciled by 13-frontend §F6 line 158
- **Brief:** ORPHAN: brief §3.3 timer copy '< 90s' (a general 'tranquiliza' timer). The 04-scanning auditor flagged it MEDIUM (contradiction: <90s is basic-only) but checked only 04-scanning.
- **Spec:** 13-frontend §F6 line 158 already scopes it correctly as 'el timeout demo <90s visible como tranquilizador' — demo-profile only, matching 04-scanning §10 ('<90s exclusivo del perfil demo') and 02-attack §3.1 line 60 (básico closes <90s). So the brief's bare '< 90s' is under-qualified, but 13-frontend §F6 already adds the 'demo' qualifier.
- **Fix:** Edit brief §3.3 to qualify the timer as the demo/basic expectation ('< 90s' in demo profile), matching 13-frontend §F6 line 158. The 04-scanning auditor's MEDIUM is slightly over-severe since 13-frontend already qualifies it; downgrade to LOW and treat as a brief copy fix.

#### ➕ Falta en spec · **low**
- **Ubicación:** design-prompt §2 (lines 83-85) + §6 (line 266) vs 13-frontend §F2 line 76 (states named, triggers not); 10-realtime §2 (no queued/finding trigger)
- **Brief:** ORPHAN: brief §2 OwlMascot with three states (dormido/vigilando/alerta), listed in §6 as a deliverable. No per-domain auditor (except product-overview, vs the wrong spec) owns the mascot's data-driven state mapping.
- **Spec:** 13-frontend §F2 line 76 owns the OwlMascot ('Estados: dormido (idle), vigilando (running), encontró algo (alerta)') and §F6 ties it to the theater, but NO spec maps the three states to concrete data/event triggers. 10-realtime §2 defines no 'queued' marker (empty replay = queued) and no finding-arrival trigger, so the idle→running→alerta owl transition has no explicit event source.
- **Fix:** Add a small mapping (in 13-frontend §F6 or 10-realtime) binding OwlMascot states to data: dormido = status queued / empty stream, vigilando = running (events flowing), alerta = a finding event with severity=critical arrives. The visual definition exists (13-frontend §F2); only this state→event binding is genuinely unowned.

#### 🔤 Terminología · **low**
- **Ubicación:** design-prompt §3.1 (line 104) + 13-frontend §F4 line 109 vs 01-legal-ethics §2.2 (line 74)
- **Brief:** DEDUP/severity note: the legal-ethics auditor's finding #2 (LOW drift) says the leaderboard legal micro-copy omits 'Shodan' ('equivalente a Mozilla Observatory / SSL Labs', no Shodan).
- **Spec:** 13-frontend §F4 line 109 reproduces the SAME shortened copy as the brief and cross-refs 01-legal-ethics. So brief and 13-frontend AGREE; only 01-legal-ethics §2.2 line 74 adds Shodan. The divergence is brief+13-frontend (2 references) vs 01-legal (3 references) — editorial, not a UI defect.
- **Fix:** Confirm legal-ethics finding #2 is correctly LOW. Since BOTH the brief and 13-frontend §F4 use the 2-reference copy, the cleanest fix is to align 01-legal-ethics §2.2's example down to match, OR add Shodan to both brief §3.1 and 13-frontend §F4. Pick one source and sync all three; no severity change.

