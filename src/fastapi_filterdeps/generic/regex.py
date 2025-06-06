from typing import Optional
from fastapi import Query
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class GenericRegexCriteria(SqlFilterCriteriaBase):
    """Base filter for regular expression matching.

    Provides a generic implementation for filtering with regular expressions.
    This implementation uses the regexp_match function from SQLAlchemy and (?i) flag for case-insensitive matching.
    Note that regular expression support and syntax may vary by database engine.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        case_sensitive (bool): Whether the matching should be case sensitive.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        # Filter users by email domain pattern
        email_filter = GenericRegexCriteria(
            field="email",
            alias="email_pattern",
            case_sensitive=False,
            description="Filter users by email pattern (e.g. '@example\\.com$')"
        )

        # Filter products by name with case-sensitive pattern
        name_filter = GenericRegexCriteria(
            field="name",
            alias="name_pattern",
            case_sensitive=True
        )

        # Filter logs by message pattern
        log_filter = GenericRegexCriteria(
            field="message",
            alias="log_pattern",
            case_sensitive=False,
            description="Filter logs by message content using regex"
        )
    """

    def __init__(
        self,
        field: str,
        alias: str,
        case_sensitive: bool = False,
        description: Optional[str] = None,
    ):
        """Initialize the regex filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
            case_sensitive (bool): Whether the regex matching should be case sensitive.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.case_sensitive = case_sensitive
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        case_info = (
            " (case sensitive)" if self.case_sensitive else " (case insensitive)"
        )
        return f"Filter by field '{self.field}' using regex pattern{case_info}"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for regex filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter condition.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[str] = Query(
                default=None, alias=self.alias, description=self.description
            )
        ) -> Optional[ColumnElement]:
            """Generate a regex match filter condition.

            Args:
                value (Optional[str]): Regular expression pattern to match against.

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no value provided.
            """
            if value is None:
                return None
            pattern = value if self.case_sensitive else f"(?i){value}"
            return model_field.regexp_match(pattern)

        return filter_dependency
