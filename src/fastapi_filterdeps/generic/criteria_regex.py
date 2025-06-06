from typing import Optional
from fastapi import Query
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import func

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class GenericRegexCriteria(SqlFilterCriteriaBase):
    """Base filter for regular expression matching.

    Provides a generic implementation for filtering with regular expressions.
    Note that regular expression support and syntax may vary by database engine.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        case_sensitive (bool): Whether the matching should be case sensitive.
        description (Optional[str]): Custom description for the filter parameter.
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
            case_sensitive (bool): Whether the matching should be case sensitive.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.case_sensitive = case_sensitive
        self.description = (
            description
            or f"Filter by field '{self.field}' using regex pattern"
            + (" (case sensitive)" if case_sensitive else "")
        )

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for regex filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter condition.

        Raises:
            AttributeError: If the specified field doesn't exist on the model.
        """
        if not hasattr(orm_model, self.field):
            raise AttributeError(
                f"Field '{self.field}' does not exist on model '{orm_model.__name__}'"
            )

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
            return model_field.regexp_match(value)

        return filter_dependency


class PostgresRegexCriteria(GenericRegexCriteria):
    """PostgreSQL-specific implementation of regex filtering.

    Uses PostgreSQL's regex syntax with (?i) flag for case-insensitive matching.
    """

    def build_filter(self, orm_model: type[DeclarativeBase]):
        if not hasattr(orm_model, self.field):
            raise AttributeError(
                f"Field '{self.field}' does not exist on model '{orm_model.__name__}'"
            )

        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[str] = Query(
                default=None, alias=self.alias, description=self.description
            )
        ) -> Optional[ColumnElement]:
            if value is None:
                return None
            pattern = value if self.case_sensitive else f"(?i){value}"
            return model_field.regexp_match(pattern)

        return filter_dependency


class MySQLRegexCriteria(GenericRegexCriteria):
    """MySQL-specific implementation of regex filtering.

    Uses MySQL's REGEXP operator with optional case sensitivity through BINARY keyword.
    """

    def build_filter(self, orm_model: type[DeclarativeBase]):
        if not hasattr(orm_model, self.field):
            raise AttributeError(
                f"Field '{self.field}' does not exist on model '{orm_model.__name__}'"
            )

        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[str] = Query(
                default=None, alias=self.alias, description=self.description
            )
        ) -> Optional[ColumnElement]:
            if value is None:
                return None
            if self.case_sensitive:
                return func.regexp_like(
                    model_field, value, "c"
                )  # 'c' flag for case-sensitive
            return func.regexp_like(
                model_field, value, "i"
            )  # 'i' flag for case-insensitive

        return filter_dependency
