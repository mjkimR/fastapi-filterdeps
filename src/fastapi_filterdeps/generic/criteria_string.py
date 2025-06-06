from enum import Enum
from fastapi import Query
from typing import Optional
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class StringMatchType(str, Enum):
    """String matching types for filtering.

    Defines the available string matching strategies for filtering:
    - CONTAINS: Partial string match
    - PREFIX: Match string prefix
    - SUFFIX: Match string suffix
    - EXACT: Exact string match
    - NOT_EQUAL: Exact non-match
    - NOT_CONTAINS: Partial string non-match
    """

    CONTAINS = "contains"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    EXACT = "exact"
    NOT_EQUAL = "not_equal"
    NOT_CONTAINS = "not_contains"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        return set(op.value for op in cls)


class GenericStringCriteria(SqlFilterCriteriaBase):
    """Base filter for string matching with multiple strategies.

    Provides a generic implementation for filtering strings using various matching
    strategies including partial match, prefix match, suffix match, and exact match.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        match_type (StringMatchType): String matching strategy to use.
        case_sensitive (bool): Whether the matching should be case sensitive.
        description (Optional[str]): Custom description for the filter parameter.
    """

    def __init__(
        self,
        field: str,
        alias: str,
        match_type: StringMatchType = StringMatchType.CONTAINS,
        case_sensitive: bool = False,
        description: Optional[str] = None,
    ):
        """Initialize the string filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
            match_type (StringMatchType): String matching strategy to use.
            case_sensitive (bool): Whether the matching should be case sensitive.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.match_type = match_type
        self.case_sensitive = case_sensitive
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        case_info = " (case sensitive)" if self.case_sensitive else ""
        return (
            f"Filter by field '{self.field}' using {self.match_type} match{case_info}"
        )

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for string filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter condition.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
            InvalidValueError: If the match type is invalid.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_enum_value(
            self.match_type, StringMatchType.get_all_operators(), "match type"
        )

        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[str] = Query(
                default=None, alias=self.alias, description=self.description
            )
        ) -> Optional[ColumnElement]:
            """Generate a string match filter condition.

            Args:
                value (Optional[str]): Value to match against.

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no value provided.
            """
            if value is None:
                return None

            if self.match_type == StringMatchType.CONTAINS:
                return (
                    model_field.like(f"%{value}%")
                    if self.case_sensitive
                    else model_field.ilike(f"%{value}%")
                )
            if self.match_type == StringMatchType.PREFIX:
                return (
                    model_field.like(f"{value}%")
                    if self.case_sensitive
                    else model_field.ilike(f"{value}%")
                )
            if self.match_type == StringMatchType.SUFFIX:
                return (
                    model_field.like(f"%{value}")
                    if self.case_sensitive
                    else model_field.ilike(f"%{value}")
                )
            if self.match_type == StringMatchType.EXACT:
                return (
                    model_field == value
                    if self.case_sensitive
                    else model_field.ilike(value)
                )
            if self.match_type == StringMatchType.NOT_EQUAL:
                return (
                    model_field != value
                    if self.case_sensitive
                    else ~model_field.ilike(value)
                )
            if self.match_type == StringMatchType.NOT_CONTAINS:
                return (
                    ~model_field.like(f"%{value}%")
                    if self.case_sensitive
                    else ~model_field.ilike(f"%{value}%")
                )
            return None

        return filter_dependency


class GenericStringSetCriteria(SqlFilterCriteriaBase):
    """Base filter for string field set operations.

    Provides a generic implementation for filtering string fields using
    set operations (IN, NOT IN). This is useful for filtering where
    the field should match one of multiple possible values.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        exclude (bool): Whether to use NOT IN instead of IN.
        description (Optional[str]): Custom description for the filter parameter.
    """

    def __init__(
        self,
        field: str,
        alias: str,
        exclude: bool = False,
        description: Optional[str] = None,
    ):
        """Initialize the string set filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
            exclude (bool): Whether to use NOT IN instead of IN.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.exclude = exclude
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        return f"Filter {self.field} where value is {'not ' if self.exclude else ''}in the specified set"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for string set filtering.

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
            values: Optional[list[str]] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            """Generate a string set filter condition.

            Args:
                values (Optional[list[str]]): Values to match against.
                    If None or empty list, no filtering will be applied.

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no filtering should be applied.
            """
            if not values:
                return None

            if self.exclude:
                return model_field.notin_(values)
            return model_field.in_(values)

        return filter_dependency
