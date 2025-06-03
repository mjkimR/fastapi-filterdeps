from typing import Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class GenericILikeCriteria(SqlFilterCriteriaBase):
    """Base filter for case-insensitive partial matching using ILIKE.

    Provides a generic implementation for filtering with case-insensitive
    partial string matches on a specified field.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
    """

    def __init__(self, field: str, alias: str):
        """Initialize the ILIKE filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
        """
        self.field = field
        self.alias = alias

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for ILIKE filtering.

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
                    description=f"Filter by field '{self.field}' value using ILIKE (case-insensitive partial match)"
                )
        ):
            """Generate an ILIKE filter condition.

            Args:
                value (Optional[str]): Value to match against (surrounded by % wildcards).

            Returns:
                Optional[BinaryExpression]: SQLAlchemy filter condition or None if no value provided.
            """
            if value is None:
                return None
            return getattr(orm_model, self.field).ilike(f"%{value}%")

        return filter_dependency


class GenericPrefixCriteria(SqlFilterCriteriaBase):
    """Base filter for prefix matching using LIKE.

    Provides a generic implementation for filtering with prefix matches
    on a specified field.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
    """

    def __init__(self, field: str, alias: str):
        """Initialize the prefix filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
        """
        self.field = field
        self.alias = alias

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for prefix filtering.

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
                    description=f"Filter by field '{self.field}' value using prefix match"
                )
        ):
            """Generate a prefix match filter condition.

            Args:
                value (Optional[str]): Value to match against (should not be surrounded by wildcards).

            Returns:
                Optional[BinaryExpression]: SQLAlchemy filter condition or None if no value provided.
            """
            if value is None:
                return None
            return getattr(orm_model, self.field).like(f"{value}%")

        return filter_dependency


class GenericSuffixCriteria(SqlFilterCriteriaBase):
    """Base filter for suffix matching using LIKE.

    Provides a generic implementation for filtering with suffix matches
    on a specified field.

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
    """

    def __init__(self, field: str, alias: str):
        """Initialize the suffix filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
        """
        self.field = field
        self.alias = alias

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for suffix filtering.

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
                    description=f"Filter by field '{self.field}' value using suffix match"
                )
        ):
            """Generate a suffix match filter condition.

            Args:
                value (Optional[str]): Value to match against (should not be surrounded by wildcards).

            Returns:
                Optional[BinaryExpression]: SQLAlchemy filter condition or None if no value provided.
            """
            if value is None:
                return None
            return getattr(orm_model, self.field).like(f"%{value}")

        return filter_dependency
