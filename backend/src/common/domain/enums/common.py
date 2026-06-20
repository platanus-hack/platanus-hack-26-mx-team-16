from src.common.domain.enums.base_enum import BaseEnum


class ProcessLabel(BaseEnum):
    admin = "admin"
    api = "api"
    workflow_worker = "workflow-worker"

    @property
    def is_admin(self):
        return self == self.admin

    @property
    def is_api(self):
        return self == self.api

    @property
    def is_workflow_worker(self):
        return self == self.workflow_worker


class Stage(BaseEnum):
    dev = "dev"
    prod = "prod"

    @property
    def is_dev(self):
        return self == self.dev

    @property
    def is_prod(self):
        return self == self.prod


class Environment(BaseEnum):
    development = "development"
    production = "production"
    testing = "testing"

    @property
    def is_local(self):
        return self in [
            self.development,
            self.testing,
        ]

    @property
    def is_development(self) -> bool:
        return self == self.development

    @property
    def is_production(self) -> bool:
        return self == self.production

    @property
    def is_testing(self):
        return self == self.testing


class TaskStatus(BaseEnum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
