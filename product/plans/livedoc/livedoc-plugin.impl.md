---
spec: ./livedoc-plugin.md
domain: tools
status: as-built
updated: 2026-06-02
summary: Plugin livedoc construido; codegraph movido al skill (no script), reindex plegado al journal hook, bug de tokenización FTS corregido
source: { branch: dev, commits: null, pr: null }
feature: livedoc
type: plan
coverage: 95
audited: 2026-06-16
---

# livedoc-plugin — estado de implementación

> Verdad **as-built** del propio plugin. El spec hermano (`livedoc-plugin.md`) es el diseño;
> esto es lo que se construyó y qué cambió. Dogfooding: livedoc se documenta a sí mismo.

## Decisiones revisadas en implementación

| # | Decisión planeada (spec §) | As-built | Δ | Por qué |
|---|----------------------------|----------|---|---------|
| 4.2 | `scripts/backlinks.py` resuelve símbolos vía codegraph | **Eliminado**; la resolución de símbolos vive en el skill `recall-decisions` | CAMBIÓ | codegraph es un MCP tool, solo invocable por el agente — un script standalone no puede llamarlo |
| 4.2 | `hooks/reindex.py` como script separado | **Plegado** en `journal_append.py`: si el archivo editado termina en `.impl.md`, hace shell-out a `index.py reindex` | CAMBIÓ | menos scripts; el reindex en caliente es parte natural del PostToolUse |
| 4.4 | Índice central `DECISIONS.md` en la raíz | `DECISIONS.md` en raíz (junto a PRODUCT/DESIGN) | CONFIRMADA | mismo anclaje agent-facing que ya honra CLAUDE.md |
| 6 | Config en `livedoc.local.md` | Sample en `livedoc/livedoc.local.md`; se copia a `<repo>/.claude/livedoc.local.md` (patrón plugin-settings) | CONFIRMADA (+detalle) | la config es per-repo, no del plugin |
| 4.2 / 7 | Plugin vive dentro de doxiq; registrar en `.claude/settings.json` (Fase 4) | **Extraído a su propio repo `Llamitai/livedoc`**, que ES el marketplace (`.claude-plugin/marketplace.json`, `source: "."`); install `livedoc@livedoc` | CAMBIÓ | portabilidad: una fuente estable, instalable en cualquier repo/máquina y para el equipo, sin copiar la carpeta a cada repo |

## Invariantes as-built

- **Cero dependencias:** todos los scripts son Python 3 stdlib (`sqlite3` con FTS5). Si
  FTS5 no está, el índice degrada a tabla normal + `LIKE` (verificado: el repo tiene FTS5).
- **Los hooks nunca rompen la herramienta:** `journal_append.py` y `session_context.py`
  envuelven todo en try/except y **siempre salen 0**. El journal ignora cualquier Bash que
  no sea `git commit` / `git merge` / `gh pr create`.
- **`.livedoc/` se auto-gitignorea** (`index.py` escribe `.livedoc/.gitignore` = `*` al
  conectar). `DECISIONS.md` y los `.impl.md` **sí** se commitean.
- **SessionStart inyecta solo el índice** (tope 4000 chars), nunca el cuerpo de los docs.
- **Búsqueda:** cada argumento se tokeniza por palabras → términos OR. Un tema entre
  comillas (`/recall "critic gemini reviewer"`) funciona; antes se trataba como una frase
  contigua y devolvía 0 (corregido en `tokenize()`).

## Back-links

- spec `product/specs/livedoc/livedoc-plugin.md` ↔ plugin repo `github.com/Llamitai/livedoc`
- símbolos: `index.py` (`reindex_file`, `query`, `tokenize`, `rebuild_decisions_index`),
  `journal_append.py`, `session_context.py`, `hooks.json`
- activación: `/plugin marketplace add Llamitai/livedoc` → `/plugin install livedoc@livedoc`
