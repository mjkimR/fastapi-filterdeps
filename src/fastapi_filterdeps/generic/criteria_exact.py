from typing import Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class GenericExactCriteria(SqlFilterCriteriaBase):
    """Base filter for exact value matching.

    Provides a generic implementation for filtering with exact value matches
    on a specified field.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
    """

    def __init__(self, field: str, alias: str):
        """Initialize the exact match filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
        """
        self.field = field
        self.alias = alias

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for exact filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter condition.

        Raises:
            AttributeError: If the specified field doesn't exist on the model.
        """
        if not hasattr(orm_model, self.field):
            raise AttributeError(f"Field '{self.field}' does not exist on model '{orm_model.__name__}'")

        def filter_dependency(
                value: Optional[str] = Query(
                    default=None, alias=self.alias,
                    description=f"Filter by field '{self.field}' value using exact match"
                )
        ):
            """Generate an exact match filter condition.

            Args:
                value (Optional[str]): Value to match exactly.

            Returns:
                Optional[BinaryExpression]: SQLAlchemy filter condition or None if no value provided.
            """
            if value is None:
                return None
            return getattr(orm_model, self.field) == value

        return filter_dependency
