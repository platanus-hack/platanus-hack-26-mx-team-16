from enum import StrEnum, auto


class DeviceStatus(StrEnum):
    ACTIVE = auto()
    INACTIVE = auto()
    MAINTENANCE = auto()
    DISCONNECTED = auto()
