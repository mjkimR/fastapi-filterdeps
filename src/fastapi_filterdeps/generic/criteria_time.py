from datetime import datetime
from typing import Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class GenericTimeRangeCriteria(SqlFilterCriteriaBase):
    """Base filter for time range filtering.

    Provides a generic implementation for filtering records within a time range
    using start and end parameters.

    Attributes:
        field (str): Model datetime field name to filter on.
        alias (str): Base name for query parameters (will be appended with _start and _end).
        bound_type (type): Type of datetime field (default is datetime).
        include_bounds (bool): Whether to include the bounds in the filter conditions.
        need_all_params (bool): Whether to require both min and max parameters for the filter.
    """

    def __init__(
            self, field: str, alias: str,
            bound_type: type = datetime,
            include_bounds: bool = True,
            need_all_params: bool = False,
    ):
        """Initialize the time range filter.

        Args:
            field (str): Model datetime field name to filter on.
            alias (str): Base name for query parameters.
            bound_type (type): Type of datetime field (default is datetime).
            include_bounds (bool): Whether to include the bounds in the filter conditions.
            need_all_params (bool): Whether to require both start and end parameters for the filter.
        """
        self.field = field
        self.alias = alias
        self.bound_type = bound_type
        self.include_bounds = include_bounds
        self.need_all_params = need_all_params

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for time range filtering.

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
                start: Optional[bound_type] = Query(
                    default=None, alias=f"{self.alias}_start",
                    description=f"Filter by start time on field '{self.field}'."
                ),
                end: Optional[bound_type] = Query(
                    default=None, alias=f"{self.alias}_end",
                    description=f"Filter by end time on field '{self.field}'."
                ),
        ):
            """Generate time range filter conditions.

            Args:
                start (Optional[bound_type]): Start datetime for range filter.
                end (Optional[bound_type]): End datetime for range filter.

            Returns:
                list: List of SQLAlchemy filter conditions or empty list if no dates provided.
            """
            if self.need_all_params and (start is None or end is None):
                raise ValueError(f"Both '{self.alias}_start' and '{self.alias}_end' parameters are required.")

            filters = []
            if start is not None:
                if self.include_bounds:
                    filters.append(getattr(orm_model, self.field) >= start)
                else:
                    filters.append(getattr(orm_model, self.field) > start)
            if end is not None:
                if self.include_bounds:
                    filters.append(getattr(orm_model, self.field) <= end)
                else:
                    filters.append(getattr(orm_model, self.field) < end)

            return filters

        return filter_dependency
