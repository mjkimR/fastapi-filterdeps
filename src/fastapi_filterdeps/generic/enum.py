from enum import Enum
from typing import Any, Callable, List, Optional, Type

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class EnumCriteria(SqlFilterCriteriaBase):
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
        alias: str,
        enum_class: Type[Enum],
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
        self.field = field
        self.alias = alias
        self.enum_class = enum_class
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            str: The default description, including available enum values.
        """
        enum_values = ", ".join([f"`{v.value}`" for v in self.enum_class])
        return f"Filter by '{self.field}' on one of: {enum_values}."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for single-enum filtering.

        This method creates a callable FastAPI dependency that produces an
        SQLAlchemy equality filter condition.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to which
                the filter will be applied.

        Returns:
            Callable: A FastAPI dependency that, when resolved, returns a
                SQLAlchemy filter condition (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the
                `orm_model`.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[self.enum_class] = Query(  # type: ignore
                default=None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates an enum equality filter condition.

            Args:
                value (Optional[Enum]): The enum member provided in the query
                    parameter. If None, no filter is applied.

            Returns:
                Optional[ColumnElement]: A SQLAlchemy filter expression, or `None`
                    if no value was provided.
            """
            if value is None:
                return None
            return model_field == value

        return filter_dependency


class MultiEnumCriteria(SqlFilterCriteriaBase):
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
        alias: str,
        enum_class: Type[Enum],
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
        self.field = field
        self.alias = alias
        self.enum_class = enum_class
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            str: The default description, including available enum values.
        """
        enum_values = ", ".join([f"`{v.value}`" for v in self.enum_class])
        return f"Filter by '{self.field}' on one or more of: {enum_values}."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for multi-enum filtering.

        This method creates a callable FastAPI dependency that produces a SQL
        `IN` clause for filtering.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to which
                the filter will be applied.

        Returns:
            Callable: A FastAPI dependency that, when resolved, returns a
                SQLAlchemy filter condition (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the
                `orm_model`.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            values: Optional[List[self.enum_class]] = Query(  # type: ignore
                default=None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates a multi-enum 'IN' filter condition.

            Args:
                values (Optional[List[Enum]]): A list of enum members provided
                    in the query parameters. If None or empty, no filter is applied.

            Returns:
                Optional[ColumnElement]: A SQLAlchemy filter expression, or `None`
                    if no values were provided.
            """
            if not values:
                return None
            return model_field.in_(values)

        return filter_dependency
