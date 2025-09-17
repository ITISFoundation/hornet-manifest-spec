"""Core domain exceptions for hornet-flow operations.

These exceptions are used by the API layer and represent business logic errors.
They do not contain CLI-specific concerns like exit codes.
"""


class HornetFlowError(Exception):
    """Base exception for hornet-flow operations."""


class ApiValidationError(HornetFlowError):
    """Raised when validation fails."""


class ApiProcessingError(HornetFlowError):
    """Raised when processing operations fail."""


class ApiInputValueError(HornetFlowError):
    """Raised when input parameters are invalid."""


class ApiFileNotFoundError(HornetFlowError):
    """Raised when required files are not found."""
