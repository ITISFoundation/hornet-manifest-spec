"""Core domain exceptions for hornet-flow operations.

These exceptions are used by the API layer and represent business logic errors.
They do not contain CLI-specific concerns like exit codes.
"""


class HornetFlowError(Exception):
    """Base exception for hornet-flow operations."""


class ValidationError(HornetFlowError):
    """Raised when validation fails."""


class ProcessingError(HornetFlowError):
    """Raised when processing operations fail."""


class InputError(HornetFlowError):
    """Raised when input parameters are invalid."""


class InputFileNotFoundError(HornetFlowError):
    """Raised when required files are not found."""
