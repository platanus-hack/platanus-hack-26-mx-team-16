from src.auth.infrastructure.bus_wiring import auth_wiring
from src.messaging.infrastructure.bus_wiring import messaging_wiring
from src.tenants.infrastructure.bus_wiring import tenants_wiring
from src.users.infrastructure.bus_wiring import users_wiring


def init_bus_event() -> None:
    auth_wiring()
    messaging_wiring()
    tenants_wiring()
    users_wiring()
