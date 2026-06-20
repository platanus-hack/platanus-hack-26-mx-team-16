"""Resolve a durable HumanTask and resume its pipeline run (F6).

Two effects: persist the resolution (so the review queue reflects it) and signal
the waiting workflow via ``task_resolved`` so the pause phase unblocks. The signal
is keyed by ``task_key`` (deterministic per run+phase), matching the workflow's
``wait_for_task``.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from temporalio.client import Client

from src.common.application.logging import get_logger
from src.common.domain.enums.human_tasks import HumanTaskKind
from src.common.domain.exceptions._base import DomainError
from src.common.domain.interfaces.use_case import UseCase
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.models.human_task import HumanTask
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.human_task import HumanTaskRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository
from src.workflows.domain.services.approval_quorum import evaluate_quorum, quorum_pool_size

logger = get_logger(__name__)

TASK_RESOLVED_SIGNAL = "task_resolved"
QA_PASSED_EVENT = "qa.passed"
QA_FAILED_EVENT = "qa.failed"


class HumanTaskSignalError(DomainError):
    def __init__(self, task_id: str):
        super().__init__(
            code="human_task.signal_failed",
            message="The task was recorded but the pipeline run could not be resumed. Retry shortly.",
            status_code=503,
            context={"task_id": task_id},
        )


class HumanTaskClaimConflictError(DomainError):
    """E5 §3.2: la tarea está reclamada por otro actor (lock pesimista)."""

    def __init__(self, task_id: str, holder: str | None = None):
        super().__init__(
            code="human_task.already_claimed",
            message="The task is claimed by another actor",
            status_code=409,
            context={"task_id": task_id, "holder": holder},
        )


class HumanTaskNotAnApproverError(DomainError):
    """F4: el actor no está en ``approvers.users`` del gate de quórum (403)."""

    def __init__(self, task_id: str):
        super().__init__(
            code="human_task.not_an_approver",
            message="You are not an authorized approver for this task.",
            status_code=403,
            context={"task_id": task_id},
        )


class HumanTaskOpenFlagsError(DomainError):
    """E5 §3.4: no se aprueba con campos flageados sin verificación.

    ``{force: true}`` en la resolución lo salta (mismo patrón 409+force del
    ready de E4)."""

    def __init__(self, task_id: str, open_fields: list[dict]):
        super().__init__(
            code="human_task.open_flags",
            message="The case has flagged fields without verification. Verify them or resolve with force.",
            status_code=409,
            context={"task_id": task_id, "openFields": open_fields},
        )


@dataclass
class ResolveHumanTask(UseCase):
    task_id: UUID
    tenant_id: UUID
    resolution: dict
    repository: HumanTaskRepository
    temporal_client: Client
    # E5 §3.2 · atribución: `user:<uuid>` | `staff:<uuid>`. Compatible:
    # sin actor el comportamiento E4 queda intacto.
    actor: str | None = None
    # E5 §3.4 · invariante open_flags: con repo de documentos presente, un
    # ``approved: true`` exige que no queden campos flageados sin verificación
    # (``{force: true}`` lo salta). None ⇒ check apagado (M2M / compat).
    document_repository: WorkflowDocumentRepository | None = None
    # E6 §3 · resolución de tareas QA (kind=QA): ``{passed, findings?}`` ⇒
    # case_event qa.passed/qa.failed. Una task QA NO tiene run pausado
    # (pipeline_run_id None) ⇒ jamás se señala Temporal. None ⇒ sin registro
    # de veredicto (compat).
    case_event_repository: CaseEventRepository | None = None

    async def execute(self) -> HumanTask | None:
        task = await self.repository.find_by_id(self.task_id, self.tenant_id)
        if task is None:
            return task
        if task.status.value != "pending":
            return await self._resignal_resolved(task)

        # E5 §3.2: si está reclamada por OTRO actor ⇒ 409 (con holder).
        # Sin claim previo ⇒ auto-claim implícito (el resolve la consume).
        if self.actor and task.claimed_by and task.claimed_by != self.actor:
            raise HumanTaskClaimConflictError(str(self.task_id), holder=task.claimed_by)

        # E5 §3.4: "no avanza con flags abiertos" — aplica a aprobar (tenant
        # L2 y staff L1); rechazar siempre es legal.
        await self._assert_no_open_flags(task)

        # F4 · quórum: tasks de aprobación N>1 acumulan un voto por resolución
        # hasta alcanzar/volver inalcanzable el quórum (D-I). N=1 ⇒ flujo single.
        if task.kind == HumanTaskKind.APPROVAL and int((task.payload or {}).get("approvalsRequired") or 1) > 1:
            return await self._quorum_resolve(task)

        resolution = dict(self.resolution)
        if self.actor:
            resolution["resolvedBy"] = self.actor

        resolved = await self.repository.resolve(self.task_id, self.tenant_id, resolution)
        if resolved is None:
            return None

        # E5 §C5: el repo hace UPDATE condicional. Si la fila ya no estaba
        # ``pending`` (carrera perdida / doble-submit) devuelve la fila YA
        # resuelta sin sobrescribirla: nuestra ``resolution`` no aplicó, así que
        # re-señalamos la resolución ALMACENADA (idempotente), nunca la nuestra.
        if resolved.status.value != "pending" and resolved.resolution != resolution:
            return await self._resignal_resolved(resolved)

        # E6 §3: veredicto QA al timeline (no toca el caso ni señala Temporal).
        await self._record_qa_verdict(resolved, resolution)

        if resolved.pipeline_run_id:
            # La señal ES la reanudación del run: si falla, el caller debe
            # saberlo (503 ⇒ reintenta; el retry entra por la rama de arriba).
            # Una task QA tiene pipeline_run_id None ⇒ NUNCA entra aquí.
            await self._signal(resolved, resolution, strict=True)
        return resolved

    async def _quorum_resolve(self, task: HumanTask) -> HumanTask | None:
        """F4 · D-I: registra el voto del actor, lo señala al run y solo marca la
        task RESOLVED cuando el quórum se decide (approved/rejected). Mientras
        sea ``pending`` la task sigue abierta para más aprobadores."""
        payload = dict(task.payload or {})
        n = int(payload.get("approvalsRequired") or 1)
        approvers = payload.get("approvers") or {}
        distinct = bool(payload.get("distinctApprovers", True))

        allowed_users: list[str] = approvers.get("users") or []
        actor_id = self.actor.split(":", 1)[-1] if self.actor else None
        if allowed_users and actor_id not in allowed_users and self.actor not in allowed_users:
            raise HumanTaskNotAnApproverError(str(self.task_id))

        vote = {
            "approved": bool(self.resolution.get("approved")),
            "comment": self.resolution.get("comment"),
            "resolvedBy": self.actor,
        }
        votes: list[dict] = list(payload.get("votes") or [])
        if distinct and self.actor:
            votes = [v for v in votes if v.get("resolvedBy") != self.actor]
        votes.append(vote)
        task.payload = {**payload, "votes": votes}
        task = await self.repository.upsert(task)  # persiste el voto (sigue pending)

        if task.pipeline_run_id:
            await self._signal(task, vote, strict=True)  # el gate acumula este voto

        pool = quorum_pool_size(len(allowed_users), n)
        approvals = sum(1 for v in votes if v.get("approved"))
        decision = evaluate_quorum(approvals, len(votes) - approvals, n, pool)
        if decision == "pending":
            return task  # esperando más votos
        return await self.repository.resolve(
            self.task_id, self.tenant_id, {"approved": decision == "approved", "votes": votes}
        )

    async def _record_qa_verdict(self, task: HumanTask, resolution: dict) -> None:
        """qa.passed/qa.failed para una task QA — best-effort, jamás tumba el
        resolve (la task ya quedó RESOLVED). No-op para cualquier otro kind."""
        if task.kind != HumanTaskKind.QA or self.case_event_repository is None or task.case_id is None:
            return
        passed = bool(resolution.get("passed"))
        event_type = QA_PASSED_EVENT if passed else QA_FAILED_EVENT
        payload: dict = {"taskId": str(task.uuid)}
        findings = resolution.get("findings")
        if findings:
            payload["findings"] = findings
        try:
            await self.case_event_repository.create(
                CaseEvent(
                    uuid=uuid4(),
                    tenant_id=task.tenant_id,
                    case_id=task.case_id,
                    type=event_type,
                    payload=payload,
                    actor=self.actor,
                    dedupe_key=f"{task.task_key}:{event_type}",
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "human_task.qa_verdict_record_failed",
                task_id=str(self.task_id),
                error=f"{type(exc).__name__}: {exc}",
            )

    async def _resignal_resolved(self, task: HumanTask) -> HumanTask:
        """Rama idempotente "ya resuelta" (retry tras señal caída o carrera
        perdida): re-señala la resolución ALMACENADA. El re-signal es
        best-effort, pero si vuelve a fallar propagamos 503 — devolver 200 con
        el run pausado para siempre sería una mentira (minor: retry señal caída
        ⇒ 503)."""
        if task.pipeline_run_id and task.resolution is not None:
            await self._signal(task, task.resolution, strict=True)
        return task

    async def _assert_no_open_flags(self, task: HumanTask) -> None:
        """409 ``human_task.open_flags`` si quedan campos flageados sin entrada
        en ``verification``: ``needs_clarification`` del doc + gate items del
        stage (``task.payload["items"]``). ``{force: true}`` lo salta."""
        if (
            self.document_repository is None
            or task.kind != HumanTaskKind.APPROVAL
            or task.case_id is None
            or self.resolution.get("approved") is not True
            or bool(self.resolution.get("force"))
        ):
            return

        flagged_by_doc: dict[str, set[str]] = {}
        for item in (task.payload or {}).get("items") or []:
            document_id = item.get("documentId")
            field_path = item.get("fieldPath")
            if document_id and field_path:
                flagged_by_doc.setdefault(document_id, set()).add(field_path)

        documents = await self.document_repository.list_by_case(task.case_id, self.tenant_id)
        open_fields: list[dict] = []
        for document in documents:
            doc_id = str(document.uuid)
            flagged = set(document.needs_clarification or []) | flagged_by_doc.get(doc_id, set())
            verification = document.verification or {}
            for field_path in sorted(flagged):
                if not self._is_verified(verification.get(field_path)):
                    open_fields.append({"documentId": doc_id, "fieldPath": field_path})
        if open_fields:
            raise HumanTaskOpenFlagsError(str(self.task_id), open_fields)

    @staticmethod
    def _is_verified(entry: dict | None) -> bool:
        """E5 §C-minor: una corrección ``external`` (``level 0``) NO habilita la
        aprobación sin force — sólo cuenta como verificación una entrada L1/L2
        (``level >= 1``), igual que el filtro Rossum. Entrada sin ``level`` se
        trata como verificada por una persona (compat: el verify_field tenant
        siempre sella ``level``)."""
        if not isinstance(entry, dict):
            return False
        level = entry.get("level")
        return level is None or level >= 1

    async def _signal(self, task: HumanTask, resolution: dict, *, strict: bool) -> None:
        try:
            handle = self.temporal_client.get_workflow_handle(task.pipeline_run_id)
            # Señal multi-arg: SIEMPRE vía args=[...] — posicionales extra
            # lanzan TypeError en el cliente de temporalio.
            await handle.signal(TASK_RESOLVED_SIGNAL, args=[task.task_key, resolution])
        except Exception as exc:
            logger.warning(
                "human_task.signal_failed",
                task_id=str(self.task_id),
                run_id=task.pipeline_run_id,
                error=f"{type(exc).__name__}: {exc}",
            )
            if strict:
                raise HumanTaskSignalError(str(self.task_id)) from exc
