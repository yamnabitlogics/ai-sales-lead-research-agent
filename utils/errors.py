"""Application-specific errors with user-friendly messages."""


class PipelineError(Exception):
    """Base error for pipeline failures."""

    def __init__(self, message: str, code: str = "pipeline_error"):
        self.message = message
        self.code = code
        super().__init__(message)


class ValidationError(PipelineError):
    def __init__(self, message: str):
        super().__init__(message, code="validation_error")


class ConfigurationError(PipelineError):
    def __init__(self, message: str):
        super().__init__(message, code="configuration_error")


class EmptyResultError(PipelineError):
    def __init__(self, message: str = "Research completed but produced no usable results."):
        super().__init__(message, code="empty_result")
