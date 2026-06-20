from doxiq_shared.domain.exceptions import DomainException


class ResponseParserNotSetError(DomainException):
    pass


class SampleTextExtractionError(DomainException):
    pass
