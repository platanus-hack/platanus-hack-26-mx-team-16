from async_factory_boy.factory.sqlalchemy import AsyncSQLAlchemyFactory
from sqlalchemy import select


class AsyncSQLAlchemyTestFactory(AsyncSQLAlchemyFactory):
    _created_uuid_instances = []

    @classmethod
    async def _save(cls, model_class, *args, **kwargs):
        created_uuid_instances = cls._created_uuid_instances
        obj = await super()._save(model_class, *args, **kwargs)
        created_uuid_instances.append(obj.uuid)
        return obj

    @classmethod
    async def clean_up(cls):
        session = cls._meta.sqlalchemy_session
        model_class = cls._meta.model
        created_uuid_instances = cls._created_uuid_instances

        stmt = select(model_class).filter(model_class.uuid.in_(created_uuid_instances))

        orm_instances = (await session.execute(stmt)).scalars().all()

        for orm_instance in orm_instances:
            created_uuid_instances.remove(orm_instance.uuid)
            await session.delete(orm_instance)
        await session.commit()
