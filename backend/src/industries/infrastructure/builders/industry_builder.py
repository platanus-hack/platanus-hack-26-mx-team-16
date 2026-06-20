from src.common.database.models.processing.industry import IndustryORM
from src.common.domain.models.industry import Industry


def build_industry(orm_instance: IndustryORM) -> Industry:
    return Industry(
        uuid=orm_instance.uuid,
        slug=orm_instance.slug,
        name=orm_instance.name,
        icon=orm_instance.icon,
        description=orm_instance.description,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
