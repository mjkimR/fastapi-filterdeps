from enum import Enum
from typing import Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class BinaryFilterType(str, Enum):
    """Binary filter types.

    Available types:
    - IS_TRUE: Check if field is true
    - IS_FALSE: Check if field is false
    - IS_NONE: Check if field is null
    - IS_NOT_NONE: Check if field is not null
    """

    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    IS_NONE = "is_none"
    IS_NOT_NONE = "is_not_none"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        return set(op.value for op in cls)


class BinaryCriteria(SqlFilterCriteriaBase):
    """Base filter for binary conditions.

    Provides filtering for boolean fields and null checks.
    Supports four types of conditions:
    - IS TRUE: field == True
    - IS FALSE: field == False
    - IS NULL: field IS NULL
    - IS NOT NULL: field IS NOT NULL

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        filter_type (BinaryFilterType): Type of binary filter to apply.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        # Filter active users
        active_filter = BinaryCriteria(
            field="is_active",
            alias="active_only",
            filter_type=BinaryFilterType.IS_TRUE
        )

        # Filter incomplete tasks
        incomplete_filter = BinaryCriteria(
            field="completed",
            alias="show_incomplete",
            filter_type=BinaryFilterType.IS_FALSE
        )

        # Filter users with verified email
        verified_filter = BinaryCriteria(
            field="email_verified_at",
            alias="verified_only",
            filter_type=BinaryFilterType.IS_NOT_NONE,
            description="Show only users with verified email"
        )
    """

    def __init__(
        self,
        field: str,
        alias: str = None,
        filter_type: BinaryFilterType = BinaryFilterType.IS_TRUE,
        description: Optional[str] = None,
    ):
        """Initialize the binary filter.

        Args:
            field (str): Model field name to filter on.
            alias (str, optional): Query parameter name to use in API endpoints.
            filter_type (BinaryFilterType): Type of binary filter to apply.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias or f"{field}_{filter_type.value}"
        self.filter_type = filter_type
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Generate default description based on filter type.

        Returns:
            str: Default description for the filter.
        """
        if self.filter_type == BinaryFilterType.IS_TRUE:
            return f"Filter records where {self.field} is true"
        elif self.filter_type == BinaryFilterType.IS_FALSE:
            return f"Filter records where {self.field} is false"
        elif self.filter_type == BinaryFilterType.IS_NONE:
            return f"Filter records where {self.field} is null"
        else:  # IS_NOT_NONE
            return f"Filter records where {self.field} is not null"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for binary filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns list of SQLAlchemy filter conditions.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
            InvalidValueError: If the filter type is invalid.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_enum_value(
            self.filter_type, BinaryFilterType.get_all_operators(), "filter type"
        )

        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            is_value: Optional[bool] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            ),
        ) -> Optional[ColumnElement]:
            """Generate binary filter conditions.

            Args:
                is_value (Optional[bool]): Is value of the filter. If None, no filter is applied. If False, the filter is inverted.

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no filter is applied.
            """
            if is_value is None:
                return None

            if self.filter_type == BinaryFilterType.IS_TRUE:
                return model_field.is_(True) if is_value else model_field.is_(False)
            elif self.filter_type == BinaryFilterType.IS_FALSE:
                return model_field.is_(False) if is_value else model_field.is_(True)
            elif self.filter_type == BinaryFilterType.IS_NONE:
                return model_field.is_(None) if is_value else model_field.isnot(None)
            else:  # IS_NOT_NONE
                return model_field.isnot(None) if is_value else model_field.is_(None)

        return filter_dependency
