from enum import Enum
from typing import Any, Optional


from fastapi_filterdeps.base import SimpleFilterCriteriaBase


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


class StringCriteria(SimpleFilterCriteriaBase):
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

    Example:
        In a FastAPI app, define filters for a 'Post' model::

            from .models import Post
            from fastapi_filterdeps import create_combined_filter_dependency

            post_filters = create_combined_filter_dependency(
                StringCriteria(
                    field="title",
                    alias="title_contains",
                    match_type=StringMatchType.CONTAINS,
                    case_sensitive=False,
                    description="Filter posts by title (case-insensitive contains)"
                ),
                StringCriteria(
                    field="author",
                    alias="author_exact",
                    match_type=StringMatchType.EXACT,
                    case_sensitive=True,
                    description="Filter posts by exact author name (case-sensitive)"
                ),
                orm_model=Post,
            )

            # In your endpoint, a request like GET /posts?title_contains=foo&author_exact=Bar
            # will filter for posts where the title contains 'foo' (case-insensitive)
            # and the author is exactly 'Bar' (case-sensitive).
    """

    def __init__(
        self,
        field: str,
        match_type: StringMatchType = StringMatchType.CONTAINS,
        case_sensitive: bool = False,
        alias: Optional[str] = None,
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
        super().__init__(field, alias, description, str, **query_params)
        self.match_type = match_type
        self.case_sensitive = case_sensitive

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            The default description for the OpenAPI documentation.
        """
        case_info = "(case-sensitive)" if self.case_sensitive else "(case-insensitive)"
        return f"Filter records where '{self.field}' matches the value using '{self.match_type}' logic{case_info}."

    def _validation_logic(self, orm_model):
        self._validate_enum_value(
            self.match_type, StringMatchType.get_all_operators(), "match type"
        )

    def _filter_logic(self, orm_model, value):
        model_field = getattr(orm_model, self.field)
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


class StringSetCriteria(SimpleFilterCriteriaBase):
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

    Example:
        In a FastAPI app, define set-based filters for a 'Post' model::

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
        exclude: bool = False,
        alias: Optional[str] = None,
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
        super().__init__(field, alias, description, list[str], **query_params)
        self.exclude = exclude

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            The default description for the OpenAPI documentation.
        """
        return f"Filter records where '{self.field}' is {'' if not self.exclude else 'not '}in the provided list of values."

    def _filter_logic(self, orm_model, value):
        model_field = getattr(orm_model, self.field)
        return model_field.notin_(value) if self.exclude else model_field.in_(value)
