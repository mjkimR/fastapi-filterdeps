from typing import Any, Optional

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase


class RegexCriteria(SimpleFilterCriteriaBase):
    """A filter for matching a field against a regular expression.

    Inherits from SimpleFilterCriteriaBase. This class provides a generic way to filter text fields using regular
    expression patterns. It relies on the `regexp_match` function available in
    SQLAlchemy, which translates to the native regex functions of the
    underlying database (e.g., `REGEXP` or `~`).

    Note:
        Regular expression syntax and feature support (such as for case-
        insensitivity flags like `(?i)`) can vary significantly between
        different database systems (e.g., PostgreSQL, MySQL, SQLite).

    Args:
        field (str): The name of the SQLAlchemy model field to filter on.
        case_sensitive (bool): If False, the pattern is modified to be case-insensitive, typically by prepending `(?i)`. Defaults to False.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        description (Optional[str]): A custom description for the OpenAPI documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.regex import RegexCriteria
            from myapp.models import Post

            class PostFilterSet(FilterSet):
                title_pattern = RegexCriteria(
                    field="title",
                    alias="title_pattern",
                    case_sensitive=False,
                    description="Filter posts by a case-insensitive regex pattern on the title."
                )
                class Meta:
                    orm_model = Post

            # GET /posts?title_pattern=^hello
            # will find all posts where the title starts with "hello" or "Hello", etc.
    """

    def __init__(
        self,
        field: str,
        case_sensitive: bool = False,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initialize the regular expression filter criterion.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            alias (str): The alias for the query parameter in the API.
            case_sensitive (bool): Whether the regex match should be case-sensitive. Defaults to False.
            description (Optional[str]): Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, str, **query_params)
        self.case_sensitive = case_sensitive

    def _get_default_description(self) -> str:
        """Generate a default description for the filter.

        Returns:
            str: The default description for the OpenAPI documentation.
        """
        case_info = (
            " (case-sensitive)" if self.case_sensitive else " (case-insensitive)"
        )
        return f"Filter by '{self.field}' using a regular expression{case_info}. Example: '^Item' for prefix matching."

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the regex criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The regex pattern from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        pattern = value if self.case_sensitive else f"(?i){value}"
        return model_field.regexp_match(pattern)
