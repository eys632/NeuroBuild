"""Stable domain error codes for adapters to translate into public responses."""


class DomainError(ValueError):
    """A rejected domain operation, with an explicit machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
