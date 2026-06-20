"""Background-task helper that runs the compilation runner with a fresh DB
session and emits SSE events on the per-workflow rules channel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from redis.asyncio import Redis

from src.common.application.logging import get_logger
from src.common.database.config import DatabaseConfig
from src.common.domain.enums.workflow_rules import WorkflowRuleCompilationStatus
from src.common.infrastructure.domain_builder import build_async_domain
from src.common.infrastructure.event_publisher import EventPublisher
from src.knowledge_base.domain.services.kb_resolver import KBDocumentResolver
from src.workflows.application.workflow_rules.compilation.runner import (
    WorkflowRuleCompilationRunner,
)
from src.workflows.application.workflow_rules.compilation.scheduler import (
    WorkflowRuleCompilationScheduler,
)
from src.workflows.domain.rules.events import (
    WorkflowRuleEvent,
    compiling_rules_key,
)

logger = get_logger(__name__)

_COMPILING_KEY_TTL_SECONDS = 5 * 60


async def schedule_and_run_compilation(
    rule_id: UUID,
    tenant_id: UUID,
    workflow_id: UUID,
    database_config: DatabaseConfig,
    redis_client: Redis,
    event_publisher: EventPublisher,
) -> None:
    """End-to-end background pipeline: enqueue + run + publish events."""
    parsing_key = compiling_rules_key(workflow_id)
    seq_root = 0
    compilation = None

    try:
        async with database_config.session_maker() as session:
            domain = build_async_domain(session)
            scheduler = WorkflowRuleCompilationScheduler(
                rule_id=rule_id,
                tenant_id=tenant_id,
                rule_repository=domain.workflow_rule_repository,
                compilation_repository=domain.workflow_rule_compilation_repository,
            )
            compilation = await scheduler.execute()
            await session.commit()

        await redis_client.sadd(parsing_key, str(rule_id))
        await redis_client.expire(parsing_key, _COMPILING_KEY_TTL_SECONDS)

        seq_root += 1
        await event_publisher.publish(
            WorkflowRuleEvent(
                seq=seq_root,
                ts=datetime.now(timezone.utc),
                payload={},
                type="COMPILATION_STARTED",
                workflow_id=workflow_id,
                rule_id=rule_id,
                compilation_id=compilation.uuid,
            )
        )

        async with database_config.session_maker() as session:
            domain = build_async_domain(session)
            runner = WorkflowRuleCompilationRunner(
                compilation_id=compilation.uuid,
                rule_id=rule_id,
                tenant_id=tenant_id,
                rule_repository=domain.workflow_rule_repository,
                compilation_repository=domain.workflow_rule_compilation_repository,
                document_type_repository=domain.document_type_repository,
                kb_resolver=KBDocumentResolver(repo=domain.kb_document_repository),
            )
            outcome = await runner.execute()
            await session.commit()

        seq_root += 1
        if outcome.status.value == "READY":
            await event_publisher.publish(
                WorkflowRuleEvent(
                    seq=seq_root,
                    ts=datetime.now(timezone.utc),
                    payload={},
                    type="COMPILATION_COMPLETED",
                    workflow_id=workflow_id,
                    rule_id=rule_id,
                    compilation_id=outcome.uuid,
                    version=outcome.version,
                )
            )
        else:
            await event_publisher.publish(
                WorkflowRuleEvent(
                    seq=seq_root,
                    ts=datetime.now(timezone.utc),
                    payload={},
                    type="COMPILATION_FAILED",
                    workflow_id=workflow_id,
                    rule_id=rule_id,
                    compilation_id=outcome.uuid,
                    error=outcome.error,
                )
            )
    except Exception as exc:
        logger.exception(
            "workflow_rule.compilation.background_failed",
            rule_id=str(rule_id),
        )
        if compilation is not None:
            try:
                async with database_config.session_maker() as session:
                    domain = build_async_domain(session)
                    await domain.workflow_rule_compilation_repository.mark_status(
                        compilation.uuid,
                        WorkflowRuleCompilationStatus.FAILED,
                        error=str(exc),
                    )
                    await session.commit()
            except Exception:
                logger.exception(
                    "workflow_rule.compilation.mark_failed_error",
                    rule_id=str(rule_id),
                )
            try:
                seq_root += 1
                await event_publisher.publish(
                    WorkflowRuleEvent(
                        seq=seq_root,
                        ts=datetime.now(timezone.utc),
                        payload={},
                        type="COMPILATION_FAILED",
                        workflow_id=workflow_id,
                        rule_id=rule_id,
                        compilation_id=compilation.uuid,
                        error=str(exc),
                    )
                )
            except Exception:
                logger.exception(
                    "workflow_rule.compilation.publish_failed_error",
                    rule_id=str(rule_id),
                )
    finally:
        try:
            await redis_client.srem(parsing_key, str(rule_id))
        except Exception:
            logger.exception(
                "workflow_rule.compilation.redis_cleanup_error",
                rule_id=str(rule_id),
            )
