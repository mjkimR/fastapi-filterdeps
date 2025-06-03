from typing import Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class GenericNumericRangeCriteria(SqlFilterCriteriaBase):
    """Base filter for numeric range filtering.

    Provides a generic implementation for filtering numeric fields within a specified range.
    Attributes:
        field (str): Model numeric field name to filter on.
        alias (str): Base name for query parameters (will be appended with _min and _max).
        bound_type (type): Type of numeric field (default is float).
        include_bounds (bool): Whether to include the bounds in the filter conditions.
        need_all_params (bool): Whether to require both min and max parameters for the filter.
    """

    def __init__(
            self,
            field: str,
            alias: str,
            bound_type: type = float,
            include_bounds: bool = True,
            need_all_params: bool = False,
    ):
        """Initialize the numeric range filter.

        Args:
            field (str): Model numeric field name to filter on.
            alias (str): Base name for query parameters.
            bound_type (type): Type of numeric field (default is float).
            include_bounds (bool): Whether to include the bounds in the filter conditions.
            need_all_params (bool): Whether to require both min and max parameters for the filter.
        """
        self.field = field
        self.alias = alias
        self.bound_type = bound_type
        self.include_bounds = include_bounds
        self.need_all_params = need_all_params

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for numeric range filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter conditions.

        Raises:
            AttributeError: If the specified field doesn't exist on the model.
        """
        if not hasattr(orm_model, self.field):
            raise AttributeError(f"Field '{self.field}' does not exist on model '{orm_model.__name__}'")

        bound_type = self.bound_type

        def filter_dependency(
                min_value: Optional[bound_type] = Query(
                    default=None, alias=f"{self.alias}_min",
                    description=f"Filter by minimum value on field '{self.field}'"
                ),
                max_value: Optional[bound_type] = Query(
                    default=None, alias=f"{self.alias}_max",
                    description=f"Filter by maximum value on field '{self.field}'"
                ),
        ):
            """Generate numeric range filter conditions.

            Args:
                min_value (Optional[bound_type]): Minimum value for range filter.
                max_value (Optional[bound_type]): Maximum value for range filter.

            Returns:
                list: List of SQLAlchemy filter conditions based on provided bounds.
            """
            if self.need_all_params and (min_value is None or max_value is None):
                raise ValueError("Both min and max parameters are required when need_all_params is True")

            filters = []
            if min_value is not None:
                if self.include_bounds:
                    filters.append(getattr(orm_model, self.field) >= min_value)
                else:
                    filters.append(getattr(orm_model, self.field) > min_value)
            if max_value is not None:
                if self.include_bounds:
                    filters.append(getattr(orm_model, self.field) <= max_value)
                else:
                    filters.append(getattr(orm_model, self.field) < max_value)

            return filters

        return filter_dependency
