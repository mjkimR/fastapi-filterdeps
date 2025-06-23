from typing import Any, Optional


from fastapi_filterdeps.base import SimpleFilterCriteriaBase


class RegexCriteria(SimpleFilterCriteriaBase):
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

    Example:
        In a FastAPI app, define a regex filter for a 'Post' model's title::

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
        super().__init__(field, alias, description, str, **query_params)
        self.case_sensitive = case_sensitive

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            The default description for the OpenAPI documentation.
        """
        case_info = (
            " (case-sensitive)" if self.case_sensitive else " (case-insensitive)"
        )
        return f"Filter by '{self.field}' using a regular expression{case_info}. Example: '^Item' for prefix matching."

    def _filter_logic(self, orm_model, value):
        model_field = getattr(orm_model, self.field)
        pattern = value if self.case_sensitive else f"(?i){value}"
        return model_field.regexp_match(pattern)
