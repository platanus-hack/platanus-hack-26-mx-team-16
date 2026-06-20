from src.common.database.models.usage.process_record import ProcessRecordORM
from src.usage.domain.models.process_record import ProcessRecord


def build_process_record(orm: ProcessRecordORM, workflow_name: str | None = None) -> ProcessRecord:
    record = ProcessRecord.model_validate(orm)
    record.workflow_name = workflow_name
    return record
