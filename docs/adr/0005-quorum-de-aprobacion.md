# 0005 — Quórum de aprobación N-de-M en `human_review`

- **Estado:** accepted — config + lógica de decisión + **acumulación multi-voto runtime IMPLEMENTADA** (workflow + endpoint, ver §Integración)
- **Fecha:** 2026-06-14
- **Decisores:** Vic (decisiones D-E, D-I zanjadas 2026-06-14)
- **Origen:** `product/plans/pipeline/phases-config.md` §6.6 + D-E/D-I. Prerequisito: ADR 0004
  (config tipada por fase). Hoy el gate `human_review` (kind=approval) es **single**:
  un approve/reject decide. El negocio pide **N-de-M** (quórum).

## Contexto y problema

`_approval_gate` (`pause_phases.py`) abre una HumanTask y hace **un** `wait_for_task`:
`{approved: bool}` decide. No hay recuento de votos, ni quórum, ni distinción de
aprobadores, ni timeout. El mecanismo de resolución (`task_resolved` →
`_resolved_tasks[task_key]`) guarda **una** resolución por `task_key` (la última
sobrescribe), así que no acumula votos por diseño.

## Drivers

- **N-de-M** con N aprobadores **distintos** de la audiencia permitida (D-E).
- **Determinismo Temporal:** el recuento debe ser replay-safe; la lógica de
  decisión, pura y testeable.
- **Compat total:** el default (N=1) debe reproducir el gate single de hoy
  byte-a-byte (los golden / casos E2E vivos no cambian).
- **Fail-safe (D-I):** `timeout` ⇒ auto-rechazo; un rechazo **descuenta del
  quórum** (falla cuando N se vuelve inalcanzable), no termina al primer reject.

## Decisión

1. **Config (ADR 0004):** `HumanReviewConfig` gana `approvers: ApproverSpec`
   (`roles`/`users`/`audience`), `approvals_required: int (ge=1, default 1)`,
   `distinct_approvers: bool (default True)`, `timeout: Duration|None`. Validador:
   `approvals_required>1` solo con `kind="approval"` (con `review` ⇒ 422). Las
   etapas L1/L2 siguen en `ActivationPolicy.stages` (version-level), no aquí.
2. **Lógica de decisión pura** (`domain/services/approval_quorum.py`,
   replay-safe, sin I/O):
   - `quorum_pool_size(users, N)` = nº de aprobadores designados (`approvers.users`)
     o, si no hay, `N` (el caso minimal 1-de-1 = el gate de hoy).
   - `evaluate_quorum(approvals, rejections, N, pool)` → `approved` si
     `approvals≥N`; `rejected` si `pool − rejections < N` (D-I: inalcanzable);
     `pending` en otro caso.
   - `tally_votes(resolution, distinct_approvers)` cuenta `(approvals, rejections)`
     desde la forma single `{approved}` (hoy ⇒ 1 voto) o el tally multi-voto
     `{"votes": [{approved, actor}]}` (dedup por actor si `distinct`).
3. **Gate:** `_approval_gate` parsea el quórum, tally + `evaluate_quorum`. Con
   N=1 y la resolución single de hoy: approve ⇒ `approved`; reject ⇒ pool 1 −
   1 = 0 < 1 ⇒ `rejected`. **Byte-idéntico al gate de hoy.**

### Compatibilidad N=1 (verificada)

| Resolución | tally | pool | decisión |
|---|---|---|---|
| `{approved:true}` | (1,0) | 1 | approved (= hoy) |
| `{approved:false}` | (0,1) | 1 | rejected (= hoy) |

## Integración (acumulación multi-voto) — IMPLEMENTADA

N>1 funciona end-to-end:

- **Workflow (replay-safe):** la señal `task_resolved` *appendea* cada resolución
  a `self._votes[task_key]` (lista append-only en `ProcessingJobWorkflowBase`); el
  gate `_approval_gate` para N>1 hace `wait_condition` sobre el recuento
  (`_await_quorum`) hasta decidir, o `timeout` ⇒ **auto-rechazo** (fail-safe D-I).
  N=1 sigue el `wait_for_task` single de hoy (byte-idéntico).
- **Endpoint/HumanTask:** `open_approval_task` sella el quórum (`approvalsRequired`,
  `distinctApprovers`, `approvers`) en el payload de la task; `ResolveHumanTask`
  (`_quorum_resolve`) autoriza al actor contra `approvers.users` (403 si no), acumula
  el voto en `payload.votes` (dedup por actor si `distinct`), señala cada voto, y
  marca la task RESOLVED solo al alcanzar/volver inalcanzable el quórum.

La matriz rol×acción (E5) sigue autorizando en el guard del router; el use case
añade el allowlist por `approvers.users`. La forma de tally (`{votes:[...]}`)
también se acepta como resolución single, para compat.

## Consecuencias

- **+** Decisión de quórum aislada y testeada (D-I codificada y verificada).
- **+** N=1 byte-idéntico ⇒ cero regresión en los flujos vivos.
- **+** El gate ya consume tallies multi-voto: cuando el endpoint los emita, N>1
  funciona sin tocar el workflow.
- **−** N>1 no es end-to-end hasta cerrar la integración (endpoint + señal).
- **−** La matriz rol×acción (E5) autoriza al votante en el endpoint, no en la
  función pura — debe cablearse junto a la acumulación.
