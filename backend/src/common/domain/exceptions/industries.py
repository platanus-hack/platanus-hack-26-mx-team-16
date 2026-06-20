from src.common.domain.exceptions._base import DomainError


class IndustryNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="industries.IndustryNotFound",
            message=f"Industry not found: {identifier}" if identifier else "Industry not found",
            status_code=404,
        )


class IndustryAlreadyExistsError(DomainError):
    def __init__(self, slug: str = ""):
        super().__init__(
            code="industries.IndustryAlreadyExists",
            message=f"Industry with slug '{slug}' already exists" if slug else "Industry already exists",
            status_code=409,
        )


class ProcessNotFoundError(DomainError):
    def __init__(self, identifier: str = ""):
        super().__init__(
            code="industries.ProcessNotFound",
            message=f"Process not found: {identifier}" if identifier else "Process not found",
            status_code=404,
        )


class ProcessAlreadyExistsError(DomainError):
    def __init__(self, slug: str = ""):
        super().__init__(
            code="industries.ProcessAlreadyExists",
            message=f"Process with slug '{slug}' already exists" if slug else "Process already exists",
            status_code=409,
        )
