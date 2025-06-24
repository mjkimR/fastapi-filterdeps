from enum import Enum
from typing import Any, Optional, Type

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase


class EnumCriteria(SimpleFilterCriteriaBase):
    """A filter for an exact match on an Enum field.

    Inherits from SimpleFilterCriteriaBase. This class provides a generic implementation for filtering fields that use
    Python's `Enum` types. When used with FastAPI, it leverages the type hint
    to automatically create a dropdown menu with the available enum values in
    the OpenAPI documentation.

    Args:
        field (str): The name of the SQLAlchemy model field to filter on.
        enum_class (Type[Enum]): The Enum class to use for validation and type hinting.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        description (Optional[str]): A custom description for the OpenAPI documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.enum import EnumCriteria
            from myapp.models import Post, PostStatus

            class PostFilterSet(FilterSet):
                status = EnumCriteria(
                    field="status",
                    alias="status",
                    enum_class=PostStatus,
                    description="Filter posts by their publication status."
                )
                class Meta:
                    orm_model = Post

            # GET /posts?status=published
            # will filter for posts where post.status == PostStatus.PUBLISHED
    """

    def __init__(
        self,
        field: str,
        enum_class: Type[Enum],
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initialize the single-enum filter criteria.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            enum_class (Type[Enum]): The Enum class for type validation.
            alias (Optional[str]): The alias for the query parameter in the API endpoint.
            description (Optional[str]): A custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, enum_class, **query_params)
        self.enum_class = enum_class

    def _get_default_description(self) -> str:
        """Generate a default description for the filter, including enum values.

        Returns:
            str: The default description, including available enum values.
        """
        enum_values = ", ".join([f"`{v.value}`" for v in self.bound_type])
        return f"Filter by '{self.field}' on one of: {enum_values}."

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the enum criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The enum value from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        return model_field == value


class MultiEnumCriteria(SimpleFilterCriteriaBase):
    """A filter to match a field against a set of Enum values (SQL IN clause).

    Inherits from SimpleFilterCriteriaBase. This class creates a filter that accepts multiple values of a given Enum
    type. It generates a SQL `IN` clause to find records where the specified
    field matches any of the provided enum values.

    Args:
        field (str): The name of the SQLAlchemy model field to filter on.
        enum_class (Type[Enum]): The Enum class for validation and type hinting.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        description (Optional[str]): A custom description for the OpenAPI documentation. A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.enum import MultiEnumCriteria
            from myapp.models import Post, PostStatus

            class PostFilterSet(FilterSet):
                statuses = MultiEnumCriteria(
                    field="status",
                    alias="statuses",
                    enum_class=PostStatus,
                    description="Filter posts by one or more publication statuses."
                )
                class Meta:
                    orm_model = Post

            # GET /posts?statuses=draft&statuses=archived
            # will filter for posts where post.status is either DRAFT or ARCHIVED.
    """

    def __init__(
        self,
        field: str,
        enum_class: Type[Enum],
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initialize the multi-enum filter criteria.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            enum_class (Type[Enum]): The Enum class for type validation.
            alias (Optional[str]): The alias for the query parameter in the API endpoint.
            description (Optional[str]): A custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, list[enum_class], **query_params)
        self.enum_class = enum_class

    def _get_default_description(self) -> str:
        """Generate a default description for the filter, including enum values.

        Returns:
            str: The default description, including available enum values.
        """
        enum_values = ", ".join([f"`{v.value}`" for v in self.enum_class])
        return f"Filter by '{self.field}' on one or more of: {enum_values}."

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the multi-enum criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The list of enum values from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        return model_field.in_(value)
