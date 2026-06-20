---
spec: ./analysis-execution.md
domain: backend
status: as-built
updated: 2026-06-02
summary: Pipeline de 5 etapas con modelos reviewer/critic y N de consenso configurables por workflow (defaults Opus 4.7 / Gemini 2.5 Pro / N=5)
source: { branch: null, commits: null, pr: null }
feature: analysis-rules
type: plan
coverage: 20
audited: 2026-06-16
---

# analysis-execution — estado de implementación

> Verdad **as-built**. El spec hermano (`analysis-execution.md`) es la intención de diseño;
> esto es lo que se construyó y qué decisiones se refinaron. **Léelo antes de tocar el
> pipeline de evaluación de reglas.**
>
> ⚠️ **Semilla**: derivado de `docs/consensus-strategy.md` contrastado con el spec. Las
> filas marcadas deben **validarse contra el código** corriendo `/synthesize analysis` en
> una rama con el diff real (este doc se generó sin journal de implementación).

## Decisiones revisadas en implementación

| # | Decisión planeada (spec §) | As-built | Δ | Por qué |
|---|----------------------------|----------|---|---------|
| E2 | Reviewer "Agno + tools", sin modelo default fijado (§6.3) | Reviewer default = **Claude Opus 4.7**, configurable vía `workflow.reviewer_model` | NUEVA | fijar un default capaz y permitir override por workflow |
| E4 | Crítico cross-provider "opcional" (§1, §6.3) | Critic default = **Gemini 2.5 Pro**, configurable vía `workflow.critic_model` | NUEVA | proveedor **distinto** al reviewer a propósito: dos modelos de la misma familia tienden a alucinar lo mismo |
| E3 | Self-consistency **N=5 fijo** (§6.3) | `workflow.analysis_consensus_samples`, **default 5** | CAMBIÓ | N configurable por workflow en vez de hardcodeado |
| E4 | "escala a critic si 3/2" (§6.3) | 5/0 y 4/1 (`agreement_ratio` ≥ 0.8) → sin critic; **3/2 (0.6) → critic** | CONFIRMADA (+detalle) | umbral explícito de `agreement_ratio` |
| E.parser | parser **Sonnet 4.6** (§4.2) | parser **Sonnet 4.6** (sin cambio) | CONFIRMADA | sweet spot — Opus es overkill para descomponer reglas, Haiku misclasifica lógica compuesta |

## Invariantes as-built

- El array `consensus` (los N verdicts de la etapa 3) es **inmutable tras la etapa 3**.
  Aunque la etapa 4 (critic) cambie `is_passed`, los verdicts originales se conservan para
  auditoría. La señal de que el critic intervino es `critic_iterations > 0`.
- El critic corre **solo** cuando `needs_critic` (consenso 3/2), **nunca antes** de la
  etapa 3. Máximo **2 iteraciones** reviewer↔critic; el rerun del reviewer ocurre solo si
  el critic devuelve `severity=high`.
- Una regla con `parsed_checks=null` o `parser_error != null` sigue siendo **válida** para
  evaluación: la etapa 1 se skipea (`{"skipped": true, "reason": "parser_unavailable"}`) y
  el reviewer asume toda la carga.
- El parser corre **una sola vez** por versión de regla (cacheado en DB); re-parseo lazy al
  bumpear `PARSER_VERSION`. Un `AnalysisRun` activo termina con el AST viejo, no se
  interrumpe.

## Back-links

- spec §6.3 (las 5 etapas) · §4.2 (parser) · §6 (combinaciones) ↔ `docs/consensus-strategy.md`
- símbolos: `AgnoAgentReviewer`, `workflow.reviewer_model`, `workflow.critic_model`, `workflow.analysis_consensus_samples`
