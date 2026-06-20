---
feature: livedoc
type: spec
status: partial
coverage: 25
audited: 2026-06-16
---

# livedoc — plugin de live documentation (síntesis de decisiones de implementación)

Estado: **diseño cerrado — pendiente implementación de archivos del plugin**

> Meta-spec: este documento usa la propia metodología que define. Al implementarse,
> obtendrá su archivo hermano `livedoc-plugin.impl.md` con las decisiones que cambien
> durante la construcción del plugin.

---

## 1. Objetivo

Cerrar el ciclo `spec → implementación → conocimiento sintetizado → siguiente spec`.

Hoy el flujo es **design-forward y se detiene en la implementación**: los specs capturan
el diseño y las decisiones *antes* de construir, pero las decisiones que se toman o cambian
*durante* la implementación no se sintetizan de vuelta en ningún artefacto durable e
ingerible por agentes. El resultado: cada feature nueva arriesga re-litigar decisiones ya
zanjadas, porque el acuerdo nunca se escribió donde un agente lo vaya a leer.

`livedoc` es un **plugin de Claude Code** (skills + hooks + utilidades) que mantiene una
**live documentation**: captura señales de la sesión automáticamente, destila decisiones
de implementación a demanda, y las re-inyecta a los agentes antes de construir algo nuevo.

**Caso canónico que motiva todo esto:** `product/specs/analysis-rules/_archive/analysis-execution.md` declara *parser =
Sonnet 4.6* y un pipeline planeado. `docs/consensus-strategy.md` describe una arquitectura
de 5 etapas (critic Gemini 2.5 Pro + reviewer Opus) que **no está en el spec** y nunca se
registró como un delta de decisión. Un agente que lea el spec construiría sobre supuestos
obsoletos. `livedoc` evita exactamente eso.

---

## 2. Contexto del codebase actual

| Activo | Rol | Reutilización en `livedoc` |
|--------|-----|----------------------------|
| `specs/` (33 archivos, grammar: Objetivo → Contexto → FALTA → Diseño → **Decisiones** → Edge cases → Plan) | Diseño forward por feature | El `.impl.md` es hermano del spec; reúsa la tabla de Decisiones numeradas |
| `.claude/commands/commit.md` | Comando custom (frontmatter, Conventional Commits, scopes) | Plantilla de house-style para `/synthesize` y `/recall` |
| `.claude/skills/brainstorming/SKILL.md` | HARD-GATE de diseño; step 1 "explore context" | Punto de ingesta natural; bookend simétrico al cierre |
| `.claude/skills/.../spec-document-reviewer-prompt.md` | Subagente revisor de specs | Plantilla para un revisor de síntesis |
| `.claude/settings.json` → `hooks: {}` | Vacío | Slot libre para SessionStart / PostToolUse |
| `CLAUDE.md` | Contrato agent-facing; ya obliga a leer PRODUCT/DESIGN antes de UI | Anclaje para la cláusula "lee el .impl.md del dominio antes de tocarlo" |
| context-mode (FTS5) + codegraph (MCP) | Búsqueda de texto / símbolos | Descubrimiento híbrido: FTS sobre decisiones + codegraph para back-links a símbolos |
| `MEMORY.md` + SessionStart de memoria | Patrón de índice inyectado al arrancar | Mismo patrón para inyectar el índice de decisiones |

---

## 3. Lo que FALTA

- 🔴 **No hay paso entre "código completo" y "siguiente feature"** que emita un registro
  sintetizado de qué se construyó, qué decisiones cambiaron y por qué.
- 🔴 **No hay trazabilidad** spec ↔ commit/PR. Las decisiones de arquitectura viven en
  cuerpos de PR (~50%) y commits, sin back-link al spec.
- 🔴 **No hay verdad as-built ingerible**: el único registro post-implementación vive en
  git history no estructurado, así que el gate de `brainstorming` ingiere ruido.
- 🟡 **No hay índice** que ate los specs entre sí ni un log de decisiones consultable.

---

## 4. Diseño propuesto

### 4.1 Flujo end-to-end

```
                     ┌─────────────────── sesión de trabajo ───────────────────┐
  SessionStart hook  │  PostToolUse hook (Edit/Write/Bash git)                  │
   inyecta índice ──▶│   append a journal vivo: .livedoc/journal/<branch>.jsonl │
   de decisiones     │   (archivos tocados, commits, intención si disponible)   │
                     └──────────────────────────────────────────────────────────┘
                                              │
                          feature lista │ /synthesize <topic>
                                              ▼
   skill synthesize-decisions:  lee journal + `git diff` + spec hermano
                                propone Δ decisiones · invariantes · back-links
                                ──▶ subagente revisor (¿completo? ¿preciso?)
                                ──▶ humano confirma
                                ──▶ escribe specs/<dom>/<feature>.impl.md
                                ──▶ actualiza DECISIONS.md (índice humano)
                                ──▶ reindexa .livedoc/index.db (FTS5)
                                              │
              feature NUEVA │ /recall <topic>  (o step 1 de brainstorming)
                                              ▼
   skill recall-decisions:  FTS sobre .impl.md  +  codegraph para resolver símbolos
                            ──▶ "esto ya se decidió: …; invariantes a respetar: …"
```

### 4.2 Estructura del plugin (portable)

```
livedoc/
  .claude-plugin/plugin.json          # manifest
  commands/
    synthesize.md                     # /livedoc:synthesize <topic>  → destila y escribe
    recall.md                         # /livedoc:recall <topic>      → busca decisiones
  skills/
    synthesize-decisions/SKILL.md     # lógica de síntesis + plantilla + revisor
    recall-decisions/SKILL.md         # lógica de descubrimiento (FTS + codegraph)
  hooks/
    hooks.json                        # SessionStart + PostToolUse
    session_context.py                # inyecta índice compacto al arrancar
    journal_append.py                 # acumula journal de la sesión
    reindex.py                        # reindexa .impl.md → FTS5 tras escribir
  scripts/
    index.py                          # construye/consulta .livedoc/index.db (sqlite3 FTS5, 0 deps)
    backlinks.py                      # resuelve símbolos vía codegraph (best-effort)
  templates/impl.template.md          # plantilla del archivo .impl.md
  livedoc.local.md                    # config por repo (frontmatter)  ← gitignore opcional
  README.md
```

> Runtime: **Python 3 stdlib únicamente** (sqlite3 incluye FTS5). Cero dependencias para
> que el plugin sea portable a cualquier repo de Llamitai.

### 4.3 Formato del archivo hermano `.impl.md`

```markdown
---
spec: ./analysis-execution.md
domain: backend
status: as-built            # in-progress | as-built
updated: 2026-06-02
source: { branch: feat/analysis-consensus, commits: 8932c3c..c58cbaf, pr: 42 }
---

# analysis-execution — estado de implementación

> Verdad as-built. El spec hermano es intención de diseño; esto es lo que se construyó
> y qué decisiones cambiaron. Léelo ANTES de tocar este dominio.

## Decisiones revisadas en implementación
| # | Decisión planeada (spec §) | As-built | Δ | Por qué |
|---|----------------------------|----------|---|---------|
| 11 | parser Sonnet 4.6 (§10) | Gemini 2.5 Pro critic + Opus reviewer, 5 etapas | CAMBIÓ | self-consistency N=5 sola insuficiente; critic externo baja falsos positivos |

## Invariantes as-built
- El critic corre DESPUÉS de self-consistency (N=5), nunca antes.
- `addTask` es idempotente por `run_id`.

## Alternativas rechazadas   <!-- opcional: solo si hay una vía a evitar -->
- Cache del parser en Redis — descartado: AST ya cacheado en proceso, Redis = sobrecosto.

## Back-links
- spec §11 ↔ PR #42 ↔ commits 8932c3c..c58cbaf
- símbolos: `VerdictAggregator`, `ConsensusPipeline`
```

### 4.4 Índice central `DECISIONS.md` (raíz, agent-facing)

Una línea por delta, generada por la utilidad. Es lo que el SessionStart hook inyecta
(forma compacta, como `MEMORY.md`) y lo que un humano navega:

```markdown
# Registro de decisiones (as-built)
- [analysis-execution] consensus 5-stage reemplaza parser simple → specs/backend/analysis-execution.impl.md §11 · PR#42
- [webhooks] HMAC Svix-style, idempotente por run_id → specs/backend/standard-webhooks.impl.md · PR#39
```

### 4.5 Hooks (`hooks.json`)

| Evento | Matcher | Script | Acción |
|--------|---------|--------|--------|
| `SessionStart` | — | `session_context.py` | Emite `DECISIONS.md` compacto como `additionalContext`. Solo el índice (1 línea/feature), nunca el cuerpo — protege el contexto. |
| `PostToolUse` | `Edit\|Write\|MultiEdit` | `journal_append.py` | Append `{tool, path, branch}` a `.livedoc/journal/<branch>.jsonl`. |
| `PostToolUse` | `Bash` (git commit/merge) | `journal_append.py` | Append `{commit_sha, msg, branch}`. |

> El disparo de la **síntesis es explícito** (`/synthesize`), no automático. El hook solo
> *acumula* señal barata; la destilación de calidad la hace la skill con revisión humana.

### 4.6 Descubrimiento híbrido (ingesta)

1. **Pasivo — SessionStart**: índice compacto siempre presente al arrancar.
2. **Pasivo — CLAUDE.md**: cláusula "antes de construir/modificar una feature, lee el
   `.impl.md` del dominio afectado si existe".
3. **Activo — FTS** (`/recall`): `scripts/index.py` mantiene `.livedoc/index.db` (FTS5
   sobre delta + por-qué + invariantes); búsqueda por tópico.
4. **Activo — codegraph**: `scripts/backlinks.py` resuelve los símbolos citados en
   back-links a su ubicación/firma actual → detecta si la decisión sigue vigente.

---

## 5. Decisiones

- ✅ **Decisión 1 — Formato:** anexo vivo `.impl.md` hermano del spec + índice central
  `DECISIONS.md`. El spec queda como intención pura; el `.impl.md` como verdad as-built.
- ✅ **Decisión 2 — Anexo separado, no inline:** archivo hermano, no sección dentro del
  spec — los specs llegan a 700+ líneas y mezclar intención con as-built los infla.
- ✅ **Decisión 3 — Disparo:** hook acumula journal automáticamente; síntesis explícita vía
  `/synthesize`. Calidad sobre fricción cero (los commits no estándar del repo confirman
  que el auto-resumen en merge daría ruido).
- ✅ **Decisión 4 — Ingesta:** cláusula CLAUDE.md (pasiva) + FTS (prosa de decisiones) +
  codegraph (símbolos/back-links). SessionStart inyecta solo el índice compacto.
- ✅ **Decisión 5 — Contenido mínimo:** (a) decisiones que cambiaron + por qué, (b)
  invariantes as-built, (c) back-links spec↔commit/PR. Alternativas rechazadas = opcional.
- ✅ **Decisión 6 — Empaquetado:** plugin portable, Python 3 stdlib (0 deps), afinado para
  Doxiq pero con specifics del repo en `livedoc.local.md`.
- ✅ **Decisión 7 — Idioma:** español, para coincidir con el corpus de `specs/` que los
  agentes ya leen.
- ✅ **Decisión 8 — Índice propio, no context-mode:** `livedoc` mantiene su propio FTS5
  (`.livedoc/index.db`) por portabilidad; cuando context-mode está presente es sinergia,
  no dependencia.

Decisiones abiertas: ninguna.

---

## 6. Edge cases

- **Spec inexistente** (feature sin spec previo): `/synthesize` crea el `.impl.md` de todos
  modos, con `spec: null`, y avisa que no hay intención de diseño con la cual comparar.
- **Journal vacío** (conversación compactada / sesión nueva): `/synthesize` cae a `git
  diff <base>..HEAD` + spec como fuente; el journal es enriquecimiento, no requisito.
- **Branch sin journal**: idem; se sintetiza desde el diff.
- **`.impl.md` ya existe**: `/synthesize` hace *merge* — añade filas a la tabla de
  decisiones y refresca `updated`/`source`, no sobreescribe ciega.
- **Símbolo en back-link ya no existe** (`backlinks.py` vía codegraph): marca la decisión
  como `⚠ posiblemente obsoleta` en `/recall`.
- **codegraph/context-mode ausentes**: degradación elegante — FTS propio sigue funcionando;
  back-links quedan como texto sin resolución de símbolos.
- **Multi-idioma en el journal**: se preserva tal cual; la síntesis final se normaliza a ES.

---

## 7. Plan de implementación

- **Fase 0 — Scaffolding:** `.claude-plugin/plugin.json`, árbol de directorios, `README.md`,
  `livedoc.local.md` con defaults de Doxiq.
- **Fase 1 — Utilidades (núcleo):** `scripts/index.py` (build/query FTS5),
  `scripts/backlinks.py` (codegraph best-effort), `templates/impl.template.md`.
- **Fase 2 — Hooks:** `hooks/hooks.json`, `session_context.py`, `journal_append.py`,
  `reindex.py`.
- **Fase 3 — Skills + comandos:** `synthesize-decisions/SKILL.md` (+ subagente revisor),
  `recall-decisions/SKILL.md`, `commands/synthesize.md`, `commands/recall.md`.
- **Fase 4 — Integración Doxiq:** registrar el plugin en `.claude/settings.json`; añadir la
  cláusula de ingesta a `CLAUDE.md`; sembrar `DECISIONS.md` y un primer `.impl.md`
  (candidato ideal: `analysis-execution.impl.md`, el gap canónico) como ejemplo vivo.
- **Fase 5 — Dogfood:** generar `livedoc-plugin.impl.md` con las decisiones que hayan
  cambiado al construir el propio plugin.
