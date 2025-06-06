class FilterDependencyError(Exception):
    """Base exception for all filter dependency related errors."""

    pass


class InvalidFieldError(FilterDependencyError):
    """Raised when a field does not exist on the model."""

    pass


class InvalidValueError(FilterDependencyError):
    """Raised when a filter value is invalid."""

    pass
