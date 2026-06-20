from src.common.database.config import get_scoped_session
from src.common.database.factories.base_factory import AsyncSQLAlchemyTestFactory
from src.common.database.models import TenantORM


class TenantORMFactory(AsyncSQLAlchemyTestFactory):
    class Meta:
        model = TenantORM
        sqlalchemy_session = get_scoped_session()

    name = "test-tenant"
    slug = "test-slug"
