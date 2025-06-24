from enum import Enum
from typing import Any, Optional

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase


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
        """Return all available operator values for string matching.

        Returns:
            set[str]: Set of all operator string values.
        """
        return {op.value for op in cls}


class StringCriteria(SimpleFilterCriteriaBase):
    """A filter for various types of string matching.

    Inherits from SimpleFilterCriteriaBase. This class provides a generic implementation for filtering string fields
    using multiple strategies, such as partial matches (contains, prefix, suffix),
    exact matches, and their negations. It can be configured to be case-sensitive
    or case-insensitive.

    Args:
        field (str): The name of the SQLAlchemy model field to filter on.
        match_type (StringMatchType): The string matching strategy to apply. Defaults to `StringMatchType.CONTAINS`.
        case_sensitive (bool): If True, matching is case-sensitive. Defaults to False.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        description (Optional[str]): A custom description for the OpenAPI documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.string import StringCriteria, StringMatchType
            from myapp.models import Post

            class PostFilterSet(FilterSet):
                title = StringCriteria(
                    field="title",
                    alias="title_contains",
                    match_type=StringMatchType.CONTAINS,
                    case_sensitive=False,
                    description="Filter posts by title (case-insensitive contains)"
                )
                author = StringCriteria(
                    field="author",
                    alias="author_exact",
                    match_type=StringMatchType.EXACT,
                    case_sensitive=True,
                    description="Filter posts by exact author name (case-sensitive)"
                )
                class Meta:
                    orm_model = Post

            # GET /posts?title_contains=foo&author_exact=Bar
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
        """Initialize the string filter criterion.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            match_type (StringMatchType): The string matching strategy to use. Defaults to `CONTAINS`.
            case_sensitive (bool): Whether the matching should be case-sensitive. Defaults to False.
            alias (Optional[str]): The alias for the query parameter in the API.
            description (Optional[str]): Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, str, **query_params)
        self.match_type = match_type
        self.case_sensitive = case_sensitive

    def _get_default_description(self) -> str:
        """Generate a default description for the filter.

        Returns:
            str: The default description for the OpenAPI documentation.
        """
        case_info = "(case-sensitive)" if self.case_sensitive else "(case-insensitive)"
        return f"Filter records where '{self.field}' matches the value using '{self.match_type}' logic {case_info}."

    def _validation_logic(self, orm_model):
        """Validate that the match_type is a valid StringMatchType value.

        Args:
            orm_model: The SQLAlchemy ORM model class.
        """
        self._validate_enum_value(
            self.match_type, StringMatchType.get_all_operators(), "match type"
        )

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the string criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The string value from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
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

    Inherits from SimpleFilterCriteriaBase. This class provides a generic implementation for filtering string fields using
    set-based operations. It is useful for filtering records where a field's value
    must be one of several possible options, or must not be in a list of options.

    Args:
        field (str): The name of the SQLAlchemy model field to filter on.
        exclude (bool): If True, uses a `NOT IN` clause to exclude the provided values. If False, uses an `IN` clause. Defaults to False.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        description (Optional[str]): A custom description for the OpenAPI documentation. A default is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.string import StringSetCriteria
            from myapp.models import Post

            class PostFilterSet(FilterSet):
                status_in = StringSetCriteria(
                    field="status",
                    alias="status_in",
                    exclude=False
                )
                category_not_in = StringSetCriteria(
                    field="category",
                    alias="category_not_in",
                    exclude=True
                )
                class Meta:
                    orm_model = Post

            # GET /posts?status_in=published&status_in=archived&category_not_in=spam
            # will filter for posts whose status is in [published, archived] and category is not in [spam].
    """

    def __init__(
        self,
        field: str,
        exclude: bool = False,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initialize the string set filter criterion.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            exclude (bool): If True, use NOT IN; if False, use IN. Defaults to False.
            alias (Optional[str]): The alias for the query parameter in the API.
            description (Optional[str]): Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, list[str], **query_params)
        self.exclude = exclude

    def _get_default_description(self) -> str:
        """Generate a default description for the filter.

        Returns:
            str: The default description for the OpenAPI documentation.
        """
        return (
            f"Filter records where '{self.field}' is not in the provided list."
            if self.exclude
            else f"Filter records where '{self.field}' is in the provided list."
        )

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the string set criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The list of string values from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        return model_field.notin_(value) if self.exclude else model_field.in_(value)
