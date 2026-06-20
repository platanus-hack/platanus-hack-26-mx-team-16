from src.common.database.models.classifier import ClassifierORM
from src.workflows.domain.models.classifier import Classifier


def build_classifier(orm: ClassifierORM) -> Classifier:
    return Classifier(
        uuid=orm.uuid,
        tenant_id=orm.tenant_id,
        slug=orm.slug,
        kind=orm.kind,
        config=orm.config or {},
        enabled=orm.enabled,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )
