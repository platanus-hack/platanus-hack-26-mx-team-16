# product/specs — índice

> Qué se construye (PRD, comportamiento; casi sin código). El **CÓMO** —con
> referencia a código— vive en [`product/plans/`](../plans/). El overview de
> producto y el plan de 20h están en [`product/spec.md`](../spec.md).

Cada doc lleva frontmatter `status:` (`implemented` · `partial` · `pending` ·
`obsolete`) y `coverage:`.

## Motor de pentest Owliver (subspecs numerados)

Derivados de [`spec.md`](../spec.md) §3–§14 + `owliver-frontend.md`, fusionando la
profundidad de implementación de `spec-gaps.md`. Orden de lectura sugerido = el
prefijo numérico. Todos en `status: pending` (aún no implementados).

| # | Subspec | Cubre |
|---|---------|-------|
| 01 | [legal-ethics](01-legal-ethics/README.md) | Invariante legal/ética: atestación, automáticos solo pasivos, "pasivo" como whitelist verificable. |
| 02 | [attack-levels](02-attack-levels/README.md) | Los 3 niveles de intrusividad + subagente OWASP web + whitelist `(is_gov, level)`. |
| 03 | [agentic-surface](03-agentic-surface/README.md) | **El diferenciador:** detección + puente Playwright + LLM-juez contra chatbots/widgets LLM. |
| 04 | [scanning-engine](04-scanning-engine/README.md) | Ejecución de scanners en Docker, aislamiento, watchdog, cold-start, stack de herramientas. |
| 05 | [agent-team](05-agent-team/README.md) | Agno Team (Opus + 2 Sonnet), parsers Python, LLM fuera del camino de datos. |
| 06 | [data-model](06-data-model/README.md) | Esquema Postgres del motor de pentest + contratos `Finding`/`AgenticResult`. |
| 07 | [scoring](07-scoring/README.md) | Doble sub-score → grado A–F, `penalty_raw`, cobertura parcial, `agentic_status` (3 estados). |
| 08 | [ranking-watchlists](08-ranking-watchlists/README.md) | Leaderboard gov (solo pasivo), watchlists, monitoreo/alertas (Arq cron + Resend/Slack). |
| 09 | [reporting](09-reporting/README.md) | Reporte "Owliver te explica" (2 capas), export PDF, `/r/[token]` con exploits redactados. |
| 10 | [realtime-live-view](10-realtime-live-view/README.md) | Live view por SSE: `scan_events` en Postgres, replay-then-tail, auth por cookie. |
| 11 | [auth-magic-link](11-auth-magic-link/README.md) | Magic-link sin contraseña: 4 pantallas, `magic_tokens`, cookie HttpOnly. |
| 12 | [api](12-api/README.md) | Superficie HTTP FastAPI: scans idempotentes, AuthZ anti-IDOR, SSE, watchlist, paginación. |
| 13 | [frontend](13-frontend/README.md) | Frontend Next.js completo: Hall of Shame, gate, Live Pentest Theater, reporte, auth. |

## Boilerplate SaaS (base sobre la que se construye Owliver)

| Feature | Estado |
|---|---|
| [data-model](data-model/README.md) | Modelo de datos del boilerplate (usuarios, tenants, roles, permisos, invitaciones). |
| [roles-permissions](roles-permissions/README.md) | Roles y permisos. |

## Archivo

[`_archive/`](_archive/) — insumos del split de `spec.md`, ya fusionados en los
subspecs y conservados como histórico: `spec-gaps.md` (refinamiento de huecos) y
`spec-consistency-review.md` (auditoría de consistencia, aplicada) más el
`owliver-frontend.md` original (ahora en [`13-frontend`](13-frontend/README.md)).
