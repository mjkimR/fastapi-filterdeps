from enum import Enum
from typing import Any, Callable, List, Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class StringMatchType(str, Enum):
    """Defines the available string matching strategies.

    This enum specifies the filtering strategy for the `StringCriteria` class.

    Attributes:
        CONTAINS: Case-sensitive or -insensitive partial string match (LIKE/ILIKE '%value%').
        PREFIX: Case-sensitive or -insensitive prefix match (LIKE/ILIKE 'value%').
        SUFFIX: Case-sensitive or -insensitive suffix match (LIKE/ILIKE '%value').
        EXACT: Case-sensitive or -insensitive exact match.
        NOT_EQUAL: Case-sensitive or -insensitive inequality match.
        NOT_CONTAINS: Case-sensitive or -insensitive exclusion of a partial string.
    """

    CONTAINS = "contains"
    PREFIX = "prefix"
    SUFFIX = "suffix"
    EXACT = "exact"
    NOT_EQUAL = "not_equal"
    NOT_CONTAINS = "not_contains"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Returns a set of all available operator values."""
        return {op.value for op in cls}


class StringCriteria(SqlFilterCriteriaBase):
    """A filter for various types of string matching.

    This class provides a generic implementation for filtering string fields
    using multiple strategies, such as partial matches (contains, prefix, suffix),
    exact matches, and their negations. It can be configured to be case-sensitive
    or case-insensitive.

    Attributes:
        field (str): The name of the SQLAlchemy model field to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        match_type (StringMatchType): The string matching strategy to apply.
            Defaults to `StringMatchType.CONTAINS`.
        case_sensitive (bool): If True, matching is case-sensitive.
            Defaults to False.
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Examples:
        # In a FastAPI app, define filters for a 'Post' model.

        from .models import Post
        from fastapi_filterdeps import create_combined_filter_dependency

        post_filters = create_combined_filter_dependency(
            # Case-insensitive search for a substring in the 'title'.
            # e.g., /posts?title_contains=hello
            StringCriteria(
                field="title",
                alias="title_contains",
                match_type=StringMatchType.CONTAINS,
                case_sensitive=False
            ),
            # Case-sensitive search for a 'slug' prefix.
            # e.g., /posts?slug_starts_with=tech-
            StringCriteria(
                field="slug",
                alias="slug_starts_with",
                match_type=StringMatchType.PREFIX,
                case_sensitive=True
            ),
            orm_model=Post,
        )

        # @app.get("/posts")
        # def list_posts(filters=Depends(post_filters)):
        #     query = select(Post).where(*filters)
        #     ...
    """

    def __init__(
        self,
        field: str,
        alias: str,
        match_type: StringMatchType = StringMatchType.CONTAINS,
        case_sensitive: bool = False,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the string filter criterion.

        Args:
            field: The name of the SQLAlchemy model field to filter on.
            alias: The alias for the query parameter in the API.
            match_type: The string matching strategy to use. Defaults to `CONTAINS`.
            case_sensitive: Whether the matching should be case-sensitive.
                Defaults to False.
            description: Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        self.field = field
        self.alias = alias
        self.match_type = match_type
        self.case_sensitive = case_sensitive
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            The default description for the OpenAPI documentation.
        """
        case_info = "(case-sensitive)" if self.case_sensitive else "(case-insensitive)"
        return f"Filter '{self.field}' by a {self.match_type.value} {case_info} match."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for string filtering.

        This method validates the inputs and creates a callable FastAPI dependency
        that produces the appropriate SQLAlchemy filter expression.

        Args:
            orm_model: The SQLAlchemy model class to apply the filter to.

        Returns:
            A FastAPI dependency that returns a SQLAlchemy filter
            condition (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the
                `orm_model`.
            InvalidValueError: If the `match_type` is not a valid
                `StringMatchType`.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_enum_value(
            self.match_type, StringMatchType.get_all_operators(), "match type"
        )

        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[str] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates a string match filter condition.

            Args:
                value: The string value from the query parameter. If None,
                    no filter is applied.

            Returns:
                A SQLAlchemy filter expression, or `None` if no value
                was provided.
            """
            if value is None:
                return None

            op_map = {
                StringMatchType.CONTAINS: lambda: model_field.ilike(f"%{value}%"),
                StringMatchType.PREFIX: lambda: model_field.ilike(f"{value}%"),
                StringMatchType.SUFFIX: lambda: model_field.ilike(f"%{value}"),
                StringMatchType.EXACT: lambda: model_field.ilike(value),
                StringMatchType.NOT_EQUAL: lambda: ~model_field.ilike(value),
                StringMatchType.NOT_CONTAINS: lambda: ~model_field.ilike(f"%{value}%"),
            }
            op_map_cs = {
                StringMatchType.CONTAINS: lambda: model_field.like(f"%{value}%"),
                StringMatchType.PREFIX: lambda: model_field.like(f"{value}%"),
                StringMatchType.SUFFIX: lambda: model_field.like(f"%{value}"),
                StringMatchType.EXACT: lambda: model_field == value,
                StringMatchType.NOT_EQUAL: lambda: model_field != value,
                StringMatchType.NOT_CONTAINS: lambda: ~model_field.like(f"%{value}%"),
            }

            return (
                op_map_cs[self.match_type]()
                if self.case_sensitive
                else op_map[self.match_type]()
            )

        return filter_dependency


class StringSetCriteria(SqlFilterCriteriaBase):
    """A filter to match a field against a set of string values (SQL IN/NOT IN).

    This class provides a generic implementation for filtering string fields using
    set-based operations. It is useful for filtering records where a field's value
    must be one of several possible options, or must not be in a list of options.

    Attributes:
        field (str): The name of the SQLAlchemy model field to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        exclude (bool): If True, uses a `NOT IN` clause to exclude the provided
            values. If False, uses an `IN` clause. Defaults to False.
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.
            (e.g., min_length=3, max_length=50)
    Examples:
        # In a FastAPI app, define set-based filters for a 'Post' model.

        from .models import Post
        from fastapi_filterdeps import create_combined_filter_dependency

        post_filters = create_combined_filter_dependency(
            # Filter for posts whose 'status' is one of the given values.
            # e.g., /posts?status_in=published&status_in=archived
            StringSetCriteria(
                field="status",
                alias="status_in",
                exclude=False
            ),
            # Filter for posts whose 'category' is NOT one of the given values.
            # e.g., /posts?category_not_in=spam&category_not_in=old
            StringSetCriteria(
                field="category",
                alias="category_not_in",
                exclude=True
            ),
            orm_model=Post,
        )

        # @app.get("/posts")
        # def list_posts(filters=Depends(post_filters)):
        #     query = select(Post).where(*filters)
        #     ...
    """

    def __init__(
        self,
        field: str,
        alias: str,
        exclude: bool = False,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the string set filter criterion.

        Args:
            field: The name of the SQLAlchemy model field to filter on.
            alias: The alias for the query parameter in the API.
            exclude: If True, uses `NOT IN` logic instead of `IN`.
                Defaults to False.
            description: Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        self.field = field
        self.alias = alias
        self.exclude = exclude
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            The default description for the OpenAPI documentation.
        """
        verb = "is not in" if self.exclude else "is in"
        return f"Filter where '{self.field}' {verb} the specified list of values."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for string set filtering.

        This method creates a callable FastAPI dependency that produces either a
        SQL `IN` or `NOT IN` clause.

        Args:
            orm_model: The SQLAlchemy model class to apply the filter to.

        Returns:
            A FastAPI dependency that returns a SQLAlchemy filter
            condition (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the
                `orm_model`.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            values: Optional[List[str]] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates a string set (IN/NOT IN) filter condition.

            Args:
                values: A list of string values from the query parameter. If
                    None or empty, no filter is applied.

            Returns:
                A SQLAlchemy filter expression, or `None` if no values
                were provided.
            """
            if not values:
                return None

            return (
                model_field.notin_(values) if self.exclude else model_field.in_(values)
            )

        return filter_dependency
