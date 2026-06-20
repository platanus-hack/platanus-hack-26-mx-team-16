"""Verificación/corrección por campo del Inspection Bench (E5 · diseño §4).

``correct`` actualiza el valor de la hoja en ``mapped_extraction`` (resuelto por
segmentos: ``foo.bar``, ``items[0].dosis`` — convención @slug.path) y lo marca
verificado; ``accept`` verifica el valor actual sin tocarlo. Un fieldPath que no
resuelve a una hoja existente ⇒ 422 ``field.not_found`` (jamás clave fantasma);
un contenedor (dict sin ``value`` / lista) ⇒ 422 ``field.not_correctable``.
Ambos escriben ``verification[fieldPath] = {value, verified_by, level,
verified_at, previous_value}``, limpian el flag ``needs_clarification`` del campo
y emiten ``field.corrected`` / ``field.verified``. El ``dedupe_key`` HASHEA el
path (longitud acotada: no desborda el VARCHAR(160) único de case_events) e
incluye ``action`` y ``level`` (un accept tras correct NO se absorbe).

Si el caso tiene una tarea APPROVAL abierta:
- reclamada por OTRO actor ⇒ 423 ``case.locked`` (lock pesimista §3.2 vía el
  helper compartido ``human_tasks.case_lock.ensure_case_not_locked``).
- y la APPROVAL es de un stage de revisión (``review_l1``/``review_l2``) ⇒ tras
  persistir, señal ``corrections`` al run pausado, estricta (503). Una APPROVAL
  E4 (stage=None) espera con ``wait_for_task`` y NO consume ``corrections``: no
  se señala (bufferizarla aprobaría sin re-analizar — hallazgo C12).

``level``: 0 = external (M2M)/sin nivel, 1 = L1, 2 = L2. Si el caller no lo fija
se deriva: sin APPROVAL ⇒ 2 (verificación tenant directa); ``review_l1`` ⇒ 1;
``review_l2`` ⇒ 2; APPROVAL E4 stage=None ⇒ 0 (no acuña un L1/L2 fantasma que
el filtro Rossum excluiría).

Lista de campos vacía (o sin cambios) ⇒ early-return: ni persiste ni señala.
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from temporalio.client import Client as TemporalClient

from src.common.domain.exceptions._base import DomainError
from src.common.domain.exceptions.processing import CaseNotFoundError, DocumentNotFoundError
from src.common.domain.interfaces.use_case import UseCase
from src.common.domain.models.processing.workflow_document import WorkflowDocument

# Lock por caso (helper W3 §3.2): re-export para compat de imports previos.
from src.workflows.application.human_tasks.case_lock import (  # noqa: F401
    CaseLockedError,
    ensure_case_not_locked,
)
from src.workflows.application.human_tasks.corrections_signal import signal_corrections
from src.workflows.domain.models.case_event import CaseEvent
from src.workflows.domain.repositories.case_event import CaseEventRepository
from src.workflows.domain.repositories.human_task import HumanTaskRepository
from src.workflows.domain.repositories.workflow_case import WorkflowCaseRepository
from src.workflows.domain.repositories.workflow_document import WorkflowDocumentRepository

FIELD_CORRECTED_EVENT = "field.corrected"
FIELD_VERIFIED_EVENT = "field.verified"


class FieldValueRequiredError(DomainError):
    def __init__(self, field_path: str):
        super().__init__(
            code="field.value_required",
            message=f"Action 'correct' requires a value for field '{field_path}'.",
            status_code=422,
            context={"field_path": field_path},
        )


class CorrectionDocumentAmbiguousError(DomainError):
    def __init__(self, case_id: str):
        super().__init__(
            code="corrections.document_required",
            message="The case has multiple documents; each field needs a documentId.",
            status_code=422,
            context={"case_id": case_id},
        )


class FieldNotFoundError(DomainError):
    """El fieldPath no resuelve a una hoja existente en ``mapped_extraction``."""

    def __init__(self, field_path: str):
        super().__init__(
            code="field.not_found",
            message=f"Field '{field_path}' does not resolve to an extracted leaf.",
            status_code=422,
            context={"field_path": field_path},
        )


class FieldNotCorrectableError(DomainError):
    """El fieldPath apunta a un contenedor (dict sin ``value`` / lista), no a
    una hoja corregible — corregirlo deformaría el árbol para los consumidores."""

    def __init__(self, field_path: str):
        super().__init__(
            code="field.not_correctable",
            message=(
                f"Field '{field_path}' targets a container node; only scalar "
                "leaves or dicts with a 'value' can be corrected."
            ),
            status_code=422,
            context={"field_path": field_path},
        )


@dataclass
class FieldVerification:
    field_path: str
    action: str = "correct"  # "correct" | "accept"
    value: Any = None


@dataclass
class VerifyDocumentFieldResult:
    document: WorkflowDocument
    verified_paths: list[str]
    level: int
    corrections_signaled: bool


@dataclass
class VerifyDocumentField(UseCase):
    tenant_id: UUID
    case_id: UUID
    fields: list[FieldVerification]
    verified_by: str  # "user:<uuid>" | "staff:<uuid>" | "external"
    case_repository: WorkflowCaseRepository
    document_repository: WorkflowDocumentRepository
    case_event_repository: CaseEventRepository
    human_task_repository: HumanTaskRepository
    temporal_client: TemporalClient
    document_id: UUID | None = None
    # None ⇒ derivar del stage de la APPROVAL abierta; 0 lo fija el plano M2M.
    level: int | None = None
    # Binding al workflow del path (endpoints JWT, patrón E4 anti-IDOR).
    workflow_id: UUID | None = None

    async def execute(self) -> VerifyDocumentFieldResult:
        case = await self.case_repository.find_by_id(self.case_id, self.tenant_id)
        if case is None:
            raise CaseNotFoundError(str(self.case_id))
        if self.workflow_id is not None and case.workflow_id != self.workflow_id:
            raise CaseNotFoundError(str(self.case_id))

        document = await self._resolve_document()
        # Lock pesimista §3.2 (helper compartido): APPROVAL reclamada por
        # otro ⇒ 423 ``case.locked``; devuelve la APPROVAL abierta (o None).
        approval = await ensure_case_not_locked(
            self.human_task_repository, self.case_id, self.tenant_id, self.verified_by
        )

        # Nivel de la verificación (filtro Rossum §4):
        # - review_l1 ⇒ 1, review_l2 ⇒ 2 (= stage en que se verificó).
        # - sin APPROVAL abierta ⇒ 2 (verificación tenant directa, diseño §4).
        # - APPROVAL E4 abierta con stage=None ⇒ 0: NO acuñar un L1/L2 que
        #   nunca ocurrió y que el filtro Rossum (min_level>=1) excluiría de
        #   gate items futuros de review_l2 (hallazgo C12).
        level = self.level
        if level is None:
            if approval is None:
                level = 2
            elif approval.stage == "review_l2":
                level = 2
            elif approval.stage == "review_l1":
                level = 1
            else:
                level = 0

        # Copia PROFUNDA: el árbol anidado se reescribe por referencia del padre
        # resuelto; un dict() superficial mutaría el documento original in situ.
        mapped = copy.deepcopy(document.mapped_extraction or {})
        verification = dict(document.verification or {})
        needs = list(document.needs_clarification or [])
        verified_at = datetime.now(UTC).isoformat()
        verified_paths: list[str] = []
        events: list[CaseEvent] = []

        for item in self.fields:
            if item.action == "correct" and item.value is None:
                raise FieldValueRequiredError(item.field_path)

            # Resolución por segmentos (convención @slug.path): localiza la hoja
            # existente; un path inexistente ⇒ 422 (jamás clave fantasma) y un
            # contenedor (dict sin 'value' / lista) ⇒ 422 (no deformar el árbol).
            parent, key, leaf = _resolve_leaf(mapped, item.field_path)
            previous_value = leaf.get("value") if isinstance(leaf, dict) else leaf

            if item.action == "correct":
                new_value = item.value
                if isinstance(leaf, dict):
                    parent[key] = {**leaf, "value": new_value}
                else:
                    parent[key] = new_value
            else:  # accept: verifica el valor vigente sin tocarlo
                new_value = previous_value

            verification[item.field_path] = {
                "value": new_value,
                "verified_by": self.verified_by,
                "level": level,
                "verified_at": verified_at,
                "previous_value": previous_value,
            }
            if item.field_path in needs:
                needs = [path for path in needs if path != item.field_path]

            event_type = FIELD_CORRECTED_EVENT if item.action == "correct" else FIELD_VERIFIED_EVENT
            events.append(
                CaseEvent(
                    uuid=uuid4(),
                    tenant_id=self.tenant_id,
                    case_id=self.case_id,
                    type=event_type,
                    payload={
                        "documentId": str(document.uuid),
                        "fieldPath": item.field_path,
                        "previousValue": previous_value,
                        "newValue": new_value,
                        "level": level,
                        "verifiedBy": self.verified_by,
                        "action": item.action,
                    },
                    actor=self.verified_by,
                    # Longitud ACOTADA: el path va hasheado (jamás crudo) para no
                    # desbordar el VARCHAR(160) único de case_events; action+level
                    # entran en la clave para que un accept tras correct NO se
                    # absorba por dedupe (idempotente solo en la MISMA operación).
                    dedupe_key=(
                        f"{document.uuid}:{_value_hash(item.field_path)}"
                        f":{item.action}:{level}:{_value_hash(new_value)}"
                    ),
                )
            )
            verified_paths.append(item.field_path)

        # Early-return: si ningún campo cambió (lista vacía), NO persistir ni
        # señalar — un re-analyze full sin correcciones es ruido innecesario.
        if not verified_paths:
            return VerifyDocumentFieldResult(
                document=document,
                verified_paths=[],
                level=level,
                corrections_signaled=False,
            )

        document.mapped_extraction = mapped
        document.verification = verification
        document.needs_clarification = needs if document.needs_clarification is not None else None
        updated = await self.document_repository.update(document)

        for event in events:
            await self.case_event_repository.create(event)

        signaled = False
        # Solo señalar ``corrections`` a una APPROVAL de revisión STAGED
        # (review_l1/review_l2): la espera de esas fases consume la señal y
        # re-analiza (invariante §3.3). Una APPROVAL E4 (stage=None) espera con
        # wait_for_task: bufferizaría la señal sin consumirla y se aprobaría sin
        # re-analizar ⇒ NO señalar (corrections_signaled=false).
        if (
            approval is not None
            and approval.pipeline_run_id
            and approval.stage in ("review_l1", "review_l2")
        ):
            # Estricto (503 patrón CaseReadySignalError): la señal dispara el
            # re-analyze que mantiene el invariante "re-evaluar antes de aprobar".
            await signal_corrections(
                self.temporal_client,
                approval.pipeline_run_id,
                approval.task_key,
                # Refs cortos SIEMPRE (límite 2 MiB Temporal): jamás valores.
                [{"documentId": str(document.uuid), "fieldPath": p} for p in verified_paths],
            )
            signaled = True

        return VerifyDocumentFieldResult(
            document=updated,
            verified_paths=verified_paths,
            level=level,
            corrections_signaled=signaled,
        )

    async def _resolve_document(self) -> WorkflowDocument:
        if self.document_id is not None:
            document = await self.document_repository.find_by_id(self.document_id, self.tenant_id)
            # Binding doc→caso (anti-IDOR E4): doc de otro caso ⇒ 404.
            if document is None or document.case_id != self.case_id:
                raise DocumentNotFoundError(str(self.document_id))
            return document
        documents = await self.document_repository.list_by_case(self.case_id, self.tenant_id)
        if len(documents) == 1:
            return documents[0]
        raise CorrectionDocumentAmbiguousError(str(self.case_id))


def _value_hash(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


def _resolve_leaf(mapped: dict, field_path: str) -> tuple[Any, Any, Any]:
    """Resuelve ``field_path`` (dot-split, convención @slug.path) sobre el árbol
    ``mapped_extraction`` y devuelve ``(parent_container, key_or_index, leaf)``.

    ``mapped_extraction`` es un ÁRBOL: hojas ``{value, bbox, page_number}``
    anidables en dicts y listas (``foo.bar``, ``items[0].dosis``). El write-back
    plano (``mapped[field_path] = ...``) creaba claves fantasma y dejaba el valor
    real intacto. Reglas:

    - El path debe resolver a un nodo EXISTENTE; si no ⇒ ``FieldNotFoundError``.
    - La hoja debe ser un escalar o un dict con clave ``value``; un contenedor
      (dict sin ``value`` / lista) ⇒ ``FieldNotCorrectableError``.
    """
    segments = _split_path(field_path)
    if not segments:
        raise FieldNotFoundError(field_path)

    parent: Any = None
    key: Any = None
    node: Any = mapped
    for segment in segments:
        parent = node
        if isinstance(segment, int):
            if not isinstance(node, list) or not (-len(node) <= segment < len(node)):
                raise FieldNotFoundError(field_path)
            key = segment
            node = node[segment]
        else:
            if not isinstance(node, dict) or segment not in node:
                raise FieldNotFoundError(field_path)
            key = segment
            node = node[segment]

    # Solo escalares o dicts-hoja con 'value' son corregibles. Un dict sin
    # 'value' es un contenedor; una lista es estructura — corregirlos cambiaría
    # el shape para assess/webhooks que recorren el árbol.
    if isinstance(node, dict) and "value" not in node:
        raise FieldNotCorrectableError(field_path)
    if isinstance(node, list):
        raise FieldNotCorrectableError(field_path)

    return parent, key, node


def _split_path(field_path: str) -> list[str | int]:
    """``"a.b[0].c"`` ⇒ ``["a", "b", 0, "c"]`` (dot + índices de lista)."""
    segments: list[str | int] = []
    for raw in field_path.split("."):
        token = raw
        while "[" in token:
            head, _, rest = token.partition("[")
            if head:
                segments.append(head)
            index_str, close, remainder = rest.partition("]")
            if not close or not index_str.lstrip("-").isdigit():
                # Sintaxis de índice malformada ⇒ se trata como path inexistente.
                return []
            segments.append(int(index_str))
            token = remainder
        if token:
            segments.append(token)
    return segments
