from enum import Enum
from typing import Optional, Type
from fastapi import Query
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class EnumCriteria(SqlFilterCriteriaBase):
    """Base filter for Enum field matching.

    Provides a generic implementation for filtering fields that use Enum types.
    This is particularly useful with FastAPI as it will automatically document
    the available enum values in the OpenAPI schema.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        enum_class (Type[Enum]): The Enum class to use for filtering.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        >>> from enum import Enum
        >>>
        >>> class OrderStatus(str, Enum):
        ...     PENDING = "pending"
        ...     PROCESSING = "processing"
        ...     COMPLETED = "completed"
        ...     CANCELLED = "cancelled"
        >>>
        >>> # Filter orders by status
        >>> status_filter = EnumCriteria(
        ...     field="status",
        ...     alias="order_status",
        ...     enum_class=OrderStatus
        ... )
        >>>
        >>> # Filter tasks by priority with custom description
        >>> class Priority(str, Enum):
        ...     LOW = "low"
        ...     MEDIUM = "medium"
        ...     HIGH = "high"
        >>>
        >>> priority_filter = EnumCriteria(
        ...     field="priority",
        ...     alias="task_priority",
        ...     enum_class=Priority,
        ...     description="Filter tasks by priority level"
        ... )
    """

    def __init__(
        self,
        field: str,
        alias: str,
        enum_class: Type[Enum],
        description: Optional[str] = None,
    ):
        """Initialize the enum filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
            enum_class (Type[Enum]): The Enum class to use for filtering.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.enum_class = enum_class
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        enum_values = ", ".join([f"'{v.value}'" for v in self.enum_class])
        return (
            f"Filter by field '{self.field}' using one of these values: {enum_values}"
        )

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for enum filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter condition.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[self.enum_class] = Query(  # type: ignore
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            """Generate an enum match filter condition.

            Args:
                value (Optional[Enum]): Enum value to match against.
                    If None, no filtering will be applied.

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no filtering should be applied.
            """
            if value is None:
                return None
            return model_field == value

        return filter_dependency


class MultiEnumCriteria(SqlFilterCriteriaBase):
    """Base filter for multiple Enum value matching.

    Provides a generic implementation for filtering fields that can match
    multiple Enum values. This is useful for implementing OR conditions
    across multiple enum values.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        enum_class (Type[Enum]): The Enum class to use for filtering.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        >>> from enum import Enum
        >>>
        >>> class UserRole(str, Enum):
        ...     ADMIN = "admin"
        ...     MODERATOR = "moderator"
        ...     EDITOR = "editor"
        ...     VIEWER = "viewer"
        >>>
        >>> # Filter users by multiple roles
        >>> role_filter = MultiEnumCriteria(
        ...     field="role",
        ...     alias="user_roles",
        ...     enum_class=UserRole
        ... )
        >>>
        >>> # Filter products by multiple categories
        >>> class ProductCategory(str, Enum):
        ...     ELECTRONICS = "electronics"
        ...     CLOTHING = "clothing"
        ...     BOOKS = "books"
        ...     FOOD = "food"
        >>>
        >>> category_filter = MultiEnumCriteria(
        ...     field="category",
        ...     alias="product_categories",
        ...     enum_class=ProductCategory,
        ...     description="Filter products by one or more categories"
        ... )
    """

    def __init__(
        self,
        field: str,
        alias: str,
        enum_class: Type[Enum],
        description: Optional[str] = None,
    ):
        """Initialize the multi-enum filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
            enum_class (Type[Enum]): The Enum class to use for filtering.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.enum_class = enum_class
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        enum_values = ", ".join([f"'{v.value}'" for v in self.enum_class])
        return f"Filter by field '{self.field}' using one or more of these values: {enum_values}"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for multi-enum filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter condition.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            values: Optional[list[self.enum_class]] = Query(  # type: ignore
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            """Generate a multi-enum match filter condition.

            Args:
                values (list[Enum]): List of enum values to match against (OR condition).

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no values provided.
            """
            if not values:
                return None
            return model_field.in_(values)

        return filter_dependency
