from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from dateutil.relativedelta import relativedelta

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.exceptions import InvalidValueError


class TimeMatchType(str, Enum):
    """
    Enumeration for time-based matching operations.

    Defines the available comparison operators for datetime fields.
    - GTE: Greater than or equal to (>=)
    - GT: Greater than (>)
    - LTE: Less than or equal to (<=)
    - LT: Less than (<)
    """

    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Get all available operators."""
        return {op.value for op in cls}


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


class TimeCriteria(SqlFilterCriteriaBase):
    """
    Base filter for single datetime field comparisons.

    Provides a generic implementation for filtering datetime fields based on
    a specific comparison operator (e.g., greater than, less than, equal to).

    Attributes:
        field (str): Model datetime field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        match_type (TimeMatchType): The comparison operator to use.
        description (Optional[str]): Custom description for the filter parameter.
    """

    def __init__(
        self,
        field: str,
        alias: str,
        match_type: TimeMatchType,
        description: Optional[str] = None,
    ):
        """
        Initializes the time filter.

        Args:
            field (str): Model datetime field name to filter on.
            alias (str): Query parameter name for the API.
            match_type (TimeMatchType): The comparison operator.
            description (Optional[str]): Custom description for documentation.
        """
        self.field = field
        self.alias = alias
        self.match_type = match_type
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """
        Generates a default description based on the filter configuration.
        """
        descriptions = {
            TimeMatchType.GTE: f"Filter where '{self.field}' is on or after the given datetime.",
            TimeMatchType.GT: f"Filter where '{self.field}' is after the given datetime.",
            TimeMatchType.LTE: f"Filter where '{self.field}' is on or before the given datetime.",
            TimeMatchType.LT: f"Filter where '{self.field}' is before the given datetime.",
        }
        return descriptions.get(self.match_type, f"Filter by {self.field}")

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """
        Builds a FastAPI dependency for single datetime value filtering.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_enum_value(
            self.match_type, TimeMatchType.get_all_operators(), "match_type"
        )
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[datetime] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            """
            Generates a datetime comparison filter condition.
            """
            if value is None:
                return None

            if self.match_type == TimeMatchType.GTE:
                return model_field >= value
            elif self.match_type == TimeMatchType.GT:
                return model_field > value
            elif self.match_type == TimeMatchType.LTE:
                return model_field <= value
            elif self.match_type == TimeMatchType.LT:
                return model_field < value
            else:
                raise InvalidValueError(f"Invalid match type: {self.match_type}")

        return filter_dependency


class RelativeTimeCriteria(SqlFilterCriteriaBase):
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
        recent_orders_filter = RelativeTimeCriteria(
            field="created_at",
            reference_alias="from_date",
            unit_alias="time_unit",
            offset_alias="days_ago"
        )

        # Filter events from last month (exclusive bounds)
        monthly_events_filter = RelativeTimeCriteria(
            field="event_time",
            include_start_bound=False,
            include_end_bound=False,
            description="Filter events from the past month"
        )

        # Filter user activity with custom time unit
        activity_filter = RelativeTimeCriteria(
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
