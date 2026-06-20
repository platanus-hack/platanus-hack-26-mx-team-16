# ADRs — Architecture Decision Records

Decisiones de arquitectura de Doxiq en formato **MADR** (Markdown Any Decision
Records, <https://adr.github.io/madr/>), versión abreviada.

## Convención

- Un archivo por decisión: `NNNN-titulo-en-kebab-case.md`, numeración
  secuencial de 4 dígitos empezando en `0001`.
- Idioma: español. Código, identificadores y nombres de tablas/claims en inglés.
- Secciones mínimas: **Estado** (`proposed | accepted | deprecated | superseded
  by NNNN`), **Contexto y problema**, **Drivers**, **Opciones consideradas**,
  **Decisión**, **Consecuencias**. Secciones extra (esbozos, matrices,
  criterios de salida) son bienvenidas cuando hacen la decisión accionable.
- Un ADR aceptado **no se edita** para cambiar la decisión: se escribe uno
  nuevo que lo reemplaza (`superseded by`). Correcciones menores (typos,
  enlaces) sí se editan en sitio.
- Se generan preferentemente con el plugin `adr-writer` (marketplace
  `claude-code-toolkit`).

## Decisiones históricas

Las decisiones previas a esta carpeta viven en
`product/plans/re-architecture/re-architecture.md` §8.1 (D1–D7) y en los
`specs/<...>/<feature>.impl.md`. Consultarlas antes de re-litigar algo ya
zanjado; lo nuevo entra aquí como ADR.

## Índice

| # | Título | Estado |
|---|--------|--------|
| [0001](0001-consola-staff-authz-cross-tenant.md) | Consola staff cross-tenant: modelo de autorización | proposed |
| [0002](0002-pipeline-propiedad-del-workflow.md) | Pipeline propiedad del workflow (1:1) + entry points | accepted |
| [0003](0003-workflow-unico-capacidades-derivadas.md) | Workflow único: capacidades derivadas + caso universal | accepted |
| [0004](0004-config-tipada-por-fase.md) | Config tipada por fase (`PhaseConfig` por `kind`) | accepted |
| [0005](0005-quorum-de-aprobacion.md) | Quórum de aprobación N-de-M en `human_review` | accepted (runtime multi-voto pendiente) |
| [0006](0006-script-tools-sandbox.md) | Script tools (Python/JS) en sandbox in-cluster | accepted (ejecutor real bloqueado por revisión de seguridad) |
