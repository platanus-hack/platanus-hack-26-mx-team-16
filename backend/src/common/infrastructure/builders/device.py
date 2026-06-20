from src.common.database.models.device import DeviceORM
from src.common.domain.entities.device import Device


def build_device(
    orm_instance: DeviceORM,
) -> Device:
    return Device(
        uuid=orm_instance.uuid,
        name=orm_instance.name,
        serial_number=orm_instance.serial_number,
        status=orm_instance.status,
        battery_level=orm_instance.battery_level,
        created_at=orm_instance.created_at,
        updated_at=orm_instance.updated_at,
    )
