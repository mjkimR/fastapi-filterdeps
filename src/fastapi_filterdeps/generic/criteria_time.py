from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from dateutil.relativedelta import relativedelta

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.exceptions import InvalidValueError


class TimeUnit(str, Enum):
    """Time units for relative date calculations.

    Available units:
    - DAY: Daily unit
    - WEEK: Weekly unit
    - MONTH: Monthly unit
    - YEAR: Yearly unit
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class GenericTimeRangeCriteria(SqlFilterCriteriaBase):
    """Base filter for explicit time range filtering.

    Provides filtering for datetime fields using explicit start and end dates.

    Attributes:
        field (str): Model datetime field name to filter on.
        start_alias (str): Query parameter name for start time.
        end_alias (str): Query parameter name for end time.
        include_start_bound (bool): Whether to include the start bound in the filter conditions.
        include_end_bound (bool): Whether to include the end bound in the filter conditions.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        # Filter orders by creation date range (inclusive bounds)
        order_date_filter = GenericTimeRangeCriteria(
            field="created_at",
            start_alias="order_from",
            end_alias="order_to",
            include_start_bound=True,
            include_end_bound=True
        )

        # Filter events by time range (exclusive bounds)
        event_time_filter = GenericTimeRangeCriteria(
            field="event_time",
            start_alias="after",
            end_alias="before",
            include_start_bound=False,
            include_end_bound=False
        )

        # Filter logs by timestamp with custom description
        log_filter = GenericTimeRangeCriteria(
            field="timestamp",
            description="Filter log entries by time range"
        )
    """

    def __init__(
        self,
        field: str,
        start_alias: str = None,
        end_alias: str = None,
        include_start_bound: bool = True,
        include_end_bound: bool = True,
        description: Optional[str] = None,
    ):
        """Initialize the time range filter.

        Args:
            field (str): Model datetime field name to filter on.
            start_alias (str, optional): Query parameter name for start time.
            end_alias (str, optional): Query parameter name for end time.
            include_start_bound (bool): Whether to include the start bound in the filter conditions.
            include_end_bound (bool): Whether to include the end bound in the filter conditions.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.start_alias = start_alias or f"{field}_start"
        self.end_alias = end_alias or f"{field}_end"
        self.include_start_bound = include_start_bound
        self.include_end_bound = include_end_bound
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        bounds = []
        if self.include_start_bound:
            bounds.append("inclusive start")
        else:
            bounds.append("exclusive start")
        if self.include_end_bound:
            bounds.append("inclusive end")
        else:
            bounds.append("exclusive end")
        return f"Filter by time range on field '{self.field}' ({', '.join(bounds)})"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for time range filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns list of SQLAlchemy filter conditions.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            start: Optional[datetime] = Query(
                default=None,
                alias=self.start_alias,
                description=f"Start time for filtering {self.field}",
            ),
            end: Optional[datetime] = Query(
                default=None,
                alias=self.end_alias,
                description=f"End time for filtering {self.field}",
            ),
        ) -> list[ColumnElement]:
            """Generate time range filter conditions.

            Args:
                start (Optional[datetime]): Start datetime for range filter.
                end (Optional[datetime]): End datetime for range filter.

            Returns:
                list: List of SQLAlchemy filter conditions.

            Raises:
                InvalidValueError: If the date range is invalid.
            """
            filters = []

            if start is not None and end is not None and start > end:
                raise InvalidValueError("Start date must be before end date")

            if start is not None:
                if self.include_start_bound:
                    filters.append(model_field >= start)
                else:
                    filters.append(model_field > start)
            if end is not None:
                if self.include_end_bound:
                    filters.append(model_field <= end)
                else:
                    filters.append(model_field < end)

            return filters

        return filter_dependency


class GenericRelativeTimeCriteria(SqlFilterCriteriaBase):
    """Base filter for relative time filtering.

    Provides filtering for datetime fields using a reference date and offset.

    Attributes:
        field (str): Model datetime field name to filter on.
        reference_alias (str): Query parameter name for reference date.
        unit_alias (str): Query parameter name for time unit.
        offset_alias (str): Query parameter name for offset value.
        include_start_bound (bool): Whether to include the start bound in the filter conditions.
        include_end_bound (bool): Whether to include the end bound in the filter conditions.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        # Filter orders from last 7 days
        recent_orders_filter = GenericRelativeTimeCriteria(
            field="created_at",
            reference_alias="from_date",
            unit_alias="time_unit",
            offset_alias="days_ago"
        )

        # Filter events from last month (exclusive bounds)
        monthly_events_filter = GenericRelativeTimeCriteria(
            field="event_time",
            include_start_bound=False,
            include_end_bound=False,
            description="Filter events from the past month"
        )

        # Filter user activity with custom time unit
        activity_filter = GenericRelativeTimeCriteria(
            field="last_active",
            unit_alias="inactive_period_unit",
            offset_alias="inactive_period"
        )
    """

    def __init__(
        self,
        field: str,
        reference_alias: str = None,
        unit_alias: str = None,
        offset_alias: str = None,
        include_start_bound: bool = True,
        include_end_bound: bool = True,
        description: Optional[str] = None,
    ):
        """Initialize the relative time filter.

        Args:
            field (str): Model datetime field name to filter on.
            reference_alias (str, optional): Query parameter name for reference time.
            unit_alias (str, optional): Query parameter name for time unit.
            offset_alias (str, optional): Query parameter name for offset value.
            include_start_bound (bool): Whether to include the start bound in the filter conditions.
            include_end_bound (bool): Whether to include the end bound in the filter conditions.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.reference_alias = reference_alias or f"{field}_reference"
        self.unit_alias = unit_alias or f"{field}_unit"
        self.offset_alias = offset_alias or f"{field}_offset"
        self.include_start_bound = include_start_bound
        self.include_end_bound = include_end_bound
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        bounds = []
        if self.include_start_bound:
            bounds.append("inclusive start")
        else:
            bounds.append("exclusive start")
        if self.include_end_bound:
            bounds.append("inclusive end")
        else:
            bounds.append("exclusive end")
        return f"Filter by relative time range on field '{self.field}' ({', '.join(bounds)})"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for relative time filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns list of SQLAlchemy filter conditions.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
            InvalidValueError: If the time unit is invalid.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            reference: datetime = Query(
                default=datetime.now(),
                alias=self.reference_alias,
                description=f"Reference date for filtering {self.field}",
            ),
            unit: TimeUnit = Query(
                default=TimeUnit.DAY,
                alias=self.unit_alias,
                description="Time unit for offset calculation",
            ),
            offset: int = Query(
                default=-7,
                alias=self.offset_alias,
                description="Number of time units to offset from reference date",
            ),
        ) -> list[ColumnElement]:
            """Generate relative time filter conditions.

            Args:
                reference (datetime): Reference date for calculations.
                unit (TimeUnit): Time unit for offset calculation.
                offset (int): Number of time units to offset from reference date.

            Returns:
                list: List of SQLAlchemy filter conditions.
            """
            if unit == TimeUnit.DAY:
                start = reference + timedelta(days=offset)
            elif unit == TimeUnit.WEEK:
                start = reference + timedelta(weeks=offset)
            elif unit == TimeUnit.MONTH:
                start = reference + relativedelta(months=offset)
            elif unit == TimeUnit.YEAR:
                start = reference + relativedelta(years=offset)
            else:
                raise ValueError(f"Invalid time unit: {unit}")

            if offset > 0:
                start, reference = reference, start

            filters = []
            if self.include_start_bound:
                filters.append(model_field >= start)
            else:
                filters.append(model_field > start)

            if self.include_end_bound:
                filters.append(model_field <= reference)
            else:
                filters.append(model_field < reference)

            return filters

        return filter_dependency
