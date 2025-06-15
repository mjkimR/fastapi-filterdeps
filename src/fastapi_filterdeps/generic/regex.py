from typing import Any, Callable, Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class RegexCriteria(SqlFilterCriteriaBase):
    """A filter for matching a field against a regular expression.

    This class provides a generic way to filter text fields using regular
    expression patterns. It relies on the `regexp_match` function available in
    SQLAlchemy, which translates to the native regex functions of the
    underlying database (e.g., `REGEXP` or `~`).

    Note:
        Regular expression syntax and feature support (such as for case-
        insensitivity flags like `(?i)`) can vary significantly between
        different database systems (e.g., PostgreSQL, MySQL, SQLite).

    Attributes:
        field (str): The name of the SQLAlchemy model field to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        case_sensitive (bool): If False, the pattern is modified to be
            case-insensitive, typically by prepending `(?i)`. Defaults to False.
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Examples:
        # In a FastAPI app, define a regex filter for a 'Post' model's title.

        from .models import Post
        from fastapi_filterdeps import create_combined_filter_dependency

        post_filters = create_combined_filter_dependency(
            # Creates a 'title_pattern' query parameter for case-insensitive
            # regex matching on the 'title' field.
            RegexCriteria(
                field="title",
                alias="title_pattern",
                case_sensitive=False,
                description="Filter posts by a case-insensitive regex pattern on the title."
            ),
            orm_model=Post,
        )

        # In your endpoint, a request like GET /posts?title_pattern=^hello
        # will find all posts where the title starts with "hello" or "Hello", etc.

        # @app.get("/posts")
        # def list_posts(filters=Depends(post_filters)):
        #     query = select(Post).where(*filters)
        #     ...
    """

    def __init__(
        self,
        field: str,
        alias: str,
        case_sensitive: bool = False,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the regular expression filter criterion.

        Args:
            field: The name of the SQLAlchemy model field to filter on.
            alias: The alias for the query parameter in the API.
            case_sensitive: Whether the regex match should be case-sensitive.
                Defaults to False.
            description: Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        self.field = field
        self.alias = alias
        self.case_sensitive = case_sensitive
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            The default description for the OpenAPI documentation.
        """
        case_info = "(case-sensitive)" if self.case_sensitive else "(case-insensitive)"
        return f"Filter '{self.field}' by a {case_info} regex pattern."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for regular expression filtering.

        This method creates a callable FastAPI dependency that produces a
        SQLAlchemy `regexp_match` filter condition.

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
            value: Optional[str] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates a regex match filter condition.

            Args:
                value: The regex pattern string from the query parameter. If
                    None, no filter is applied.

            Returns:
                A SQLAlchemy filter expression, or `None` if no pattern
                was provided.
            """
            if value is None:
                return None
            pattern = value if self.case_sensitive else f"(?i){value}"
            return model_field.regexp_match(pattern)

        return filter_dependency
