from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, List, Optional

from dateutil.relativedelta import relativedelta
from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.exceptions import InvalidValueError


class TimeMatchType(str, Enum):
    """Defines the available comparison operators for datetime fields.

    Attributes:
        GTE: Greater than or equal to (>=).
        GT: Greater than (>).
        LTE: Less than or equal to (<=).
        LT: Less than (<).
    """

    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Returns a set of all available operator values."""
        return {op.value for op in cls}


class TimeUnit(str, Enum):
    """Defines time units for relative date calculations.

    Attributes:
        DAY: Represents a day.
        WEEK: Represents a week.
        MONTH: Represents a calendar month.
        YEAR: Represents a calendar year.
    """

    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


class TimeCriteria(SqlFilterCriteriaBase):
    """A filter for a single, absolute datetime comparison.

    This class creates a filter for a datetime field against a specific point in
    time, using an operator like "greater than" or "less than". To create a
    fixed date range (e.g., from a start date to an end date), combine two
    instances of this class.

    Attributes:
        field (str): The name of the SQLAlchemy model's datetime field.
        alias (str): The alias for the query parameter in the API endpoint.
        match_type (TimeMatchType): The comparison operator to use.
        description (Optional[str]): A custom description for OpenAPI.

    Examples:
        # In a FastAPI app, define a fixed date range filter for a 'Post' model.

        from .models import Post
        from fastapi_filterdeps import create_combined_filter_dependency

        post_filters = create_combined_filter_dependency(
            # Sets the lower bound of the range (created_at >= value).
            TimeCriteria(
                field="created_at",
                alias="created_after",
                match_type=TimeMatchType.GTE
            ),
            # Sets the upper bound of the range (created_at <= value).
            TimeCriteria(
                field="created_at",
                alias="created_before",
                match_type=TimeMatchType.LTE
            ),
            orm_model=Post,
        )

        # A request like /posts?created_after=2025-01-01T00:00:00
        # will find all posts created on or after that timestamp.
    """

    def __init__(
        self,
        field: str,
        alias: str,
        match_type: TimeMatchType,
        description: Optional[str] = None,
    ):
        """Initializes the absolute time filter criterion.

        Args:
            field: The name of the SQLAlchemy model's datetime field.
            alias: The alias for the query parameter in the API.
            match_type: The comparison operator to use.
            description: A custom description for the OpenAPI documentation.
        """
        self.field = field
        self.alias = alias
        self.match_type = match_type
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Generates a default description based on the filter's configuration."""
        op_map = {
            TimeMatchType.GTE: "on or after",
            TimeMatchType.GT: "after",
            TimeMatchType.LTE: "on or before",
            TimeMatchType.LT: "before",
        }
        desc = op_map.get(self.match_type, "matches")
        return f"Filter where '{self.field}' is {desc} the given datetime."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for single datetime value filtering.

        Args:
            orm_model: The SQLAlchemy model class to apply the filter to.

        Returns:
            A FastAPI dependency that returns a SQLAlchemy filter condition
            or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist.
            InvalidValueError: If the `match_type` is not a valid `TimeMatchType`.
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
            """Generates a datetime comparison filter condition.

            Args:
                value: The datetime value from the query parameter.

            Returns:
                A SQLAlchemy filter expression, or `None` if no value was provided.
            """
            if value is None:
                return None

            op_map = {
                TimeMatchType.GTE: model_field >= value,
                TimeMatchType.GT: model_field > value,
                TimeMatchType.LTE: model_field <= value,
                TimeMatchType.LT: model_field < value,
            }
            return op_map.get(self.match_type)

        return filter_dependency


class RelativeTimeCriteria(SqlFilterCriteriaBase):
    """A filter for a dynamic, relative datetime range (e.g., "last 7 days").

    This filter creates a date range based on a specified offset from a
    reference date. The user provides the offset value and the time unit,
    and the filter calculates the start and end dates for the query.

    Attributes:
        field (str): The name of the SQLAlchemy model's datetime field.
        reference_alias (Optional[str]): Alias for the reference date parameter.
            Defaults to `{field}_reference`.
        unit_alias (Optional[str]): Alias for the time unit parameter. Defaults
            to `{field}_unit`.
        offset_alias (Optional[str]): Alias for the offset value parameter.
            Defaults to `{field}_offset`.
        include_start_bound (bool): If True, use `>=` for the start of the range.
            If False, use `>`. Defaults to True.
        include_end_bound (bool): If True, use `<=` for the end of the range.
            If False, use `<`. Defaults to True.
        description (Optional[str]): A custom description for OpenAPI.

    Examples:
        # In a FastAPI app, filter for posts created in the last 7 days.

        from .models import Post
        from fastapi_filterdeps import create_combined_filter_dependency

        post_filters = create_combined_filter_dependency(
            # Creates 'created_at_unit' and 'created_at_offset' params.
            RelativeTimeCriteria(field="created_at"),
            orm_model=Post,
        )

        # A request to /posts?created_at_offset=-7&created_at_unit=day
        # will find all posts from the last 7 days. The reference date
        # defaults to the current time.
    """

    def __init__(
        self,
        field: str,
        reference_alias: Optional[str] = None,
        unit_alias: Optional[str] = None,
        offset_alias: Optional[str] = None,
        include_start_bound: bool = True,
        include_end_bound: bool = True,
        description: Optional[str] = None,
    ):
        """Initializes the relative time filter criterion.

        Args:
            field: The model datetime field name to filter on.
            reference_alias: Query parameter name for the reference time.
            unit_alias: Query parameter name for the time unit.
            offset_alias: Query parameter name for the offset value.
            include_start_bound: Whether to include the start of the range.
            include_end_bound: Whether to include the end of the range.
            description: Custom description for the OpenAPI documentation.
        """
        self.field = field
        self.reference_alias = reference_alias or f"{field}_reference"
        self.unit_alias = unit_alias or f"{field}_unit"
        self.offset_alias = offset_alias or f"{field}_offset"
        self.include_start_bound = include_start_bound
        self.include_end_bound = include_end_bound
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Generates a default description for the filter."""
        bounds = []
        bounds.append("inclusive" if self.include_start_bound else "exclusive")
        bounds.append("inclusive" if self.include_end_bound else "exclusive")
        return f"Filter by relative time on '{self.field}' ({bounds[0]} start, {bounds[1]} end)."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., List[ColumnElement]]:
        """Builds a FastAPI dependency for relative time filtering.

        Args:
            orm_model: The SQLAlchemy model class to apply the filter to.

        Returns:
            A FastAPI dependency that returns a list of SQLAlchemy filter
            conditions defining the date range.

        Raises:
            InvalidFieldError: If the specified `field` does not exist.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            reference: datetime = Query(
                default_factory=datetime.now,
                alias=self.reference_alias,
                description=f"Reference date for filtering '{self.field}'. Defaults to current time.",
            ),
            unit: TimeUnit = Query(
                default=TimeUnit.DAY,
                alias=self.unit_alias,
                description="Time unit for the offset.",
            ),
            offset: int = Query(
                default=-7,
                alias=self.offset_alias,
                description="Number of time units to offset from the reference date.",
            ),
        ) -> List[ColumnElement]:
            """Generates relative time filter conditions.

            Args:
                reference: The reference date for calculation.
                unit: The time unit for the offset.
                offset: The number of units to offset.

            Returns:
                A list of SQLAlchemy filter conditions.
            """
            offset_map = {
                TimeUnit.DAY: timedelta(days=offset),
                TimeUnit.WEEK: timedelta(weeks=offset),
                TimeUnit.MONTH: relativedelta(months=offset),
                TimeUnit.YEAR: relativedelta(years=offset),
            }
            delta = offset_map.get(unit)
            if delta is None:
                raise InvalidValueError(f"Invalid time unit: {unit}")

            start_date = reference + delta
            end_date = reference

            if offset > 0:
                start_date, end_date = end_date, start_date

            filters = []
            if self.include_start_bound:
                filters.append(model_field >= start_date)
            else:
                filters.append(model_field > start_date)

            if self.include_end_bound:
                filters.append(model_field <= end_date)
            else:
                filters.append(model_field < end_date)

            return filters

        return filter_dependency
