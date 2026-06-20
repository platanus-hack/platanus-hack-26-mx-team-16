# product/features — índice

> Organización **feature-first**: cada carpeta es una feature y contiene tanto el
> **QUÉ** (`spec.md` — PRD, comportamiento) como el **CÓMO** (`plan.md` y docs de
> plan con referencia a código). El overview de producto y el plan de 20h están en
> [`../spec.md`](../spec.md).
>
> Convención de archivos dentro de cada `features/<feature>/`:
> - `spec.md` — la spec (QUÉ). Frontmatter `status:` (`implemented` · `partial` ·
>   `pending` · `obsolete`) + `coverage:`.
> - `plan.md` — el plan de implementación (CÓMO); índice del CÓMO de la feature.
> - docs de plan específicos (p. ej. `backend-auth.md`, `proxy.md`) cuando aplica.

## Motor de pentest Owliver (features numeradas, `status: pending`)

Derivadas de [`../spec.md`](../spec.md) §3–§14 + `owliver-frontend.md`, fusionando
la profundidad de `spec-gaps.md`. El prefijo numérico marca el orden de lectura del
spec de Owliver. Aún no implementadas (`status: pending`), pero cada feature ya
reúne su `spec.md` (QUÉ) y su `plan.md` (CÓMO).

| # | Feature | Cubre |
|---|---------|-------|
| 01 | [legal-ethics](01-legal-ethics/spec.md) ([plan](01-legal-ethics/plan.md)) | Invariante legal/ética: atestación, automáticos solo pasivos, "pasivo" como whitelist verificable. |
| 02 | [attack-levels](02-attack-levels/spec.md) ([plan](02-attack-levels/plan.md)) | Los 3 niveles de intrusividad + subagente OWASP web + whitelist `(is_gov, level)`. |
| 03 | [agentic-surface](03-agentic-surface/spec.md) ([plan](03-agentic-surface/plan.md)) | **El diferenciador:** detección + puente Playwright + LLM-juez contra chatbots/widgets LLM. |
| 04 | [scanning-engine](04-scanning-engine/spec.md) ([plan](04-scanning-engine/plan.md)) | Ejecución de scanners en Docker, aislamiento, watchdog, cold-start, stack de herramientas. |
| 05 | [agent-team](05-agent-team/spec.md) ([plan](05-agent-team/plan.md)) | Agno Team (Opus + 2 Sonnet), parsers Python, LLM fuera del camino de datos. |
| 06 | [data-model](06-data-model/spec.md) ([plan](06-data-model/plan.md)) | Esquema Postgres del motor de pentest + contratos `Finding`/`AgenticResult`. |
| 07 | [scoring](07-scoring/spec.md) ([plan](07-scoring/plan.md)) | Doble sub-score → grado A–F, `penalty_raw`, cobertura parcial, `agentic_status` (3 estados). |
| 08 | [ranking-watchlists](08-ranking-watchlists/spec.md) ([plan](08-ranking-watchlists/plan.md)) | Leaderboard gov (solo pasivo), watchlists, monitoreo/alertas (SAQ cron + Resend/Slack). |
| 09 | [reporting](09-reporting/spec.md) ([plan](09-reporting/plan.md)) | Reporte "Owliver te explica" (2 capas), export PDF, `/r/[token]` con exploits redactados. |
| 10 | [realtime-live-view](10-realtime-live-view/spec.md) ([plan](10-realtime-live-view/plan.md)) | Live view por SSE: `scan_events` en Postgres, replay-then-tail, auth por cookie. |
| 12 | [api](12-api/spec.md) ([plan](12-api/plan.md)) | Superficie HTTP FastAPI: scans idempotentes, AuthZ anti-IDOR, SSE, watchlist, paginación. |
| 13 | [frontend](13-frontend/spec.md) ([plan](13-frontend/plan.md)) | Frontend Next.js completo: Hall of Shame, gate, Live Pentest Theater, reporte, auth. |

## Boilerplate SaaS (base ya construida sobre la que se monta Owliver)

| Feature | QUÉ | CÓMO |
|---|---|---|
| [data-model](data-model/spec.md) | [`spec.md`](data-model/spec.md) — modelo de datos del boilerplate | [`plan.md`](data-model/plan.md), [`app-context.md`](data-model/app-context.md) |
| [roles-permissions](roles-permissions/spec.md) | [`spec.md`](roles-permissions/spec.md) — roles y permisos | — |
| [auth](auth/plan.md) | — | [`plan.md`](auth/plan.md), [`backend-auth.md`](auth/backend-auth.md), [`frontend-auth.md`](auth/frontend-auth.md) |
| [tenants](tenants/plan.md) | — | [`plan.md`](tenants/plan.md), [`switch-tenant.md`](tenants/switch-tenant.md) |
| [devops](devops/plan.md) | — | [`plan.md`](devops/plan.md), [`deployment.md`](devops/deployment.md), [`promote.md`](devops/promote.md) |
| [frontend-shell](frontend-shell/plan.md) | — | [`plan.md`](frontend-shell/plan.md), [`proxy.md`](frontend-shell/proxy.md) |

## Archivo

[`../_archive/`](../_archive/) — insumos del split de `spec.md`, ya fusionados en
las features y conservados como histórico: `spec-gaps.md` (refinamiento de huecos),
`spec-consistency-review.md` (auditoría de consistencia, aplicada) y el
`owliver-frontend.md` original (ahora en [`13-frontend/spec.md`](13-frontend/spec.md)).
