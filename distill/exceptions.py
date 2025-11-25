"""
Custom exceptions for DISTILL.
"""


class DistillError(Exception):
    """Base exception for all DISTILL errors."""

    def __init__(self, message: str, details: dict = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class CompressionError(DistillError):
    """Raised when compression fails."""
    pass


class DecompressionError(DistillError):
    """Raised when decompression fails."""
    pass


class ValidationError(DistillError):
    """Raised when input validation fails."""
    pass


class CircularReferenceError(ValidationError):
    """Raised when circular reference is detected in data."""
    pass


class MaxDepthExceededError(ValidationError):
    """Raised when data nesting exceeds maximum allowed depth."""
    pass


class MaxSizeExceededError(ValidationError):
    """Raised when data size exceeds maximum allowed size."""
    pass


class InvalidInputError(ValidationError):
    """Raised when input type is not supported."""
    pass


class SchemaExtractionError(CompressionError):
    """Raised when schema extraction fails."""
    pass


class DictionaryOverflowError(CompressionError):
    """Raised when dictionary capacity is exceeded."""
    pass
