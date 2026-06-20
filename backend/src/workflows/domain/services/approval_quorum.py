"""Lógica pura de quórum de aprobación (phases-config · F4 · D-I).

Sin I/O ni Temporal: el gate ``human_review`` cuenta votos (vía señales) y delega
aquí la DECISIÓN. Aislar la lógica la hace testeable y replay-safe.

Semántica D-I:
- ``approved`` cuando ``approvals >= approvals_required``.
- un **rechazo descuenta del quórum**: el gate falla cuando ``N`` aprobaciones se
  vuelven **inalcanzables** dado el pool de aprobadores elegibles — NO al primer
  reject. Pool ``P`` = nº de aprobadores designados (``approvers.users``) o, si no
  se designan, ``approvals_required`` (el caso minimal 1-de-1 = el gate de hoy).
- al expirar ``timeout`` el gate **auto-rechaza** (fail-safe) — eso lo decide el
  handler (timer), no esta función.
"""

from __future__ import annotations

from typing import Any, Literal

QuorumDecision = Literal["approved", "rejected", "pending"]


def quorum_pool_size(approver_user_count: int, approvals_required: int) -> int:
    """Pool de aprobadores elegibles: los designados, o el mínimo ``N`` si no hay."""
    return approver_user_count if approver_user_count > 0 else approvals_required


def evaluate_quorum(approvals: int, rejections: int, approvals_required: int, pool_size: int) -> QuorumDecision:
    if approvals >= approvals_required:
        return "approved"
    # Un reject consume un slot del pool: inalcanzable si ni con todos los slots
    # restantes se llega a N (P - rejections < N).
    if pool_size - rejections < approvals_required:
        return "rejected"
    return "pending"


def tally_votes(resolution: dict[str, Any], *, distinct_approvers: bool) -> tuple[int, int]:
    """``(approvals, rejections)`` desde la resolución de la HumanTask.

    Acepta dos formas:
    - tally multi-voto ``{"votes": [{"approved": bool, "actor": str}, ...]}`` (la
      forma que enviará el endpoint de resolución cuando acumule votos);
    - decisión single ``{"approved": bool}`` (la de hoy ⇒ 1 voto).

    Con ``distinct_approvers`` el último voto de cada actor cuenta una sola vez.
    """
    votes = resolution.get("votes")
    if isinstance(votes, list) and votes:
        if distinct_approvers:
            by_actor: dict[Any, bool] = {}
            for i, v in enumerate(votes):
                actor = v.get("actor", i)  # sin actor ⇒ voto distinto por posición
                by_actor[actor] = bool(v.get("approved"))
            decisions = list(by_actor.values())
        else:
            decisions = [bool(v.get("approved")) for v in votes]
        approvals = sum(1 for d in decisions if d)
        return approvals, len(decisions) - approvals
    # Forma single (compat con el gate de hoy).
    return (1, 0) if bool(resolution.get("approved")) else (0, 1)
