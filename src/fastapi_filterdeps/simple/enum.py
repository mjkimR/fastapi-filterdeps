from enum import Enum
from typing import Any, Optional, Type


from fastapi_filterdeps.base import SimpleFilterCriteriaBase


class EnumCriteria(SimpleFilterCriteriaBase):
    """A filter for an exact match on an Enum field.

    This class provides a generic implementation for filtering fields that use
    Python's `Enum` types. When used with FastAPI, it leverages the type hint
    to automatically create a dropdown menu with the available enum values in
    the OpenAPI (Swagger/ReDoc) documentation.

    Attributes:
        field (str): The name of the SQLAlchemy model field to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        enum_class (Type[Enum]): The Enum class to use for validation and
            type hinting.
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        In a FastAPI app, define a filter for a 'Post' model with a 'status' field of type 'PostStatus' enum::

            from .models import Post, PostStatus  # Assuming PostStatus is an Enum
            from fastapi_filterdeps import create_combined_filter_dependency

            post_filters = create_combined_filter_dependency(
                # Creates a 'status' query parameter that accepts one of the
                # values from the PostStatus enum.
                EnumCriteria(
                    field="status",
                    alias="status",
                    enum_class=PostStatus,
                    description="Filter posts by their publication status."
                ),
                orm_model=Post,
            )

            # In your endpoint, a request like GET /posts?status=published
            # will filter for posts where `post.status == PostStatus.PUBLISHED`.

            # @app.get("/posts")
            # def list_posts(filters=Depends(post_filters)):
            #     query = select(Post).where(*filters)
            #     ...
    """

    def __init__(
        self,
        field: str,
        enum_class: Type[Enum],
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the single-enum filter criteria.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            alias (str): The alias for the query parameter in the API endpoint.
            enum_class (Type[Enum]): The Enum class for type validation.
            description (Optional[str]): A custom description for the OpenAPI
                documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        super().__init__(field, alias, description, enum_class, **query_params)
        self.enum_class = enum_class

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            str: The default description, including available enum values.
        """
        enum_values = ", ".join([f"`{v.value}`" for v in self.bound_type])
        return f"Filter by '{self.field}' on one of: {enum_values}."

    def _filter_logic(self, orm_model, value):
        model_field = getattr(orm_model, self.field)
        return model_field == value


class MultiEnumCriteria(SimpleFilterCriteriaBase):
    """A filter to match a field against a set of Enum values (SQL IN clause).

    This class creates a filter that accepts multiple values of a given Enum
    type. It generates a SQL `IN` clause to find records where the specified
    field matches any of the provided enum values.

    Attributes:
        field (str): The name of the SQLAlchemy model field to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        enum_class (Type[Enum]): The Enum class for validation and type hinting.
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        In a FastAPI app, define a filter for a 'Post' model that can have multiple statuses::

            from .models import Post, PostStatus  # Assuming PostStatus is an Enum
            from fastapi_filterdeps import create_combined_filter_dependency

            post_filters = create_combined_filter_dependency(
                # Creates a 'statuses' query parameter that accepts one or more
                # values from the PostStatus enum.
                MultiEnumCriteria(
                    field="status",
                    alias="statuses",
                    enum_class=PostStatus,
                    description="Filter posts by one or more publication statuses."
                ),
                orm_model=Post,
            )

            # In your endpoint, a request like GET /posts?statuses=draft&statuses=archived
            # will filter for posts where `post.status` is either `DRAFT` or `ARCHIVED`.

            # @app.get("/posts")
            # def list_posts(filters=Depends(post_filters)):
            #     query = select(Post).where(*filters)
            #     ...
    """

    def __init__(
        self,
        field: str,
        enum_class: Type[Enum],
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the multi-enum filter criteria.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            alias (str): The alias for the query parameter in the API endpoint.
            enum_class (Type[Enum]): The Enum class for type validation.
            description (Optional[str]): A custom description for the OpenAPI
                documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        super().__init__(field, alias, description, list[enum_class], **query_params)
        self.enum_class = enum_class

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            str: The default description, including available enum values.
        """
        enum_values = ", ".join([f"`{v.value}`" for v in self.enum_class])
        return f"Filter by '{self.field}' on one or more of: {enum_values}."

    def _filter_logic(self, orm_model, value):
        model_field = getattr(orm_model, self.field)
        return model_field.in_(value)
