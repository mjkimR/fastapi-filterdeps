from enum import Enum
from fastapi import Query
from typing import Optional, List
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
        self.description = (
            description
            or f"Filter by field '{self.field}' using {self.match_type} match"
            + (" (case sensitive)" if case_sensitive else "")
        )

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for string filtering.

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
        if self.match_type not in StringMatchType.get_all_operators():
            raise ValueError(
                f"Invalid match type: {self.match_type}. "
                f"Valid match types are: {', '.join(StringMatchType.get_all_operators())}"
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
        self.description = (
            description
            or f"Filter {field} where value is {'not ' if exclude else ''}in the specified set"
        )

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for string set filtering.

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
            values: Optional[List[str]] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            """Generate a string set filter condition.

            Args:
                values (Optional[List[str]]): Values to match against.
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
