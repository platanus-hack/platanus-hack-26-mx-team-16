from dataclasses import dataclass
from typing import cast

from src.common.domain.contexts.bus import BusContext
from src.common.domain.contexts.domain import DomainContext
from src.common.domain.enums.common import Environment
from src.common.infrastructure.contexts.mock_bus_singleton import MockBusSingleton
from src.common.infrastructure.contexts.mock_domain_singleton import MockDomainSingleton
from src.common.settings import settings


@dataclass
class AppContext:
    domain: DomainContext
    bus: BusContext
    scheduler: None = None


class AppContextBuilder:
    @classmethod
    def from_env(
        cls,
        environment: Environment | None = None,
        domain: DomainContext | None = None,
        bus: BusContext | None = None,
    ) -> AppContext:
        environment = cast(Environment, environment or settings.ENVIRONMENT)
        if environment.is_production or environment.is_development:
            return AppContext(
                domain=domain,
                bus=bus,
            )
        if environment.is_testing:
            return AppContext(
                domain=MockDomainSingleton.instance,
                bus=MockBusSingleton.instance,
            )
        error_msg = f"Invalid environment: {environment.value}"
        raise NotImplementedError(error_msg)
