import re
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Optional, Tuple

from dateutil.relativedelta import relativedelta

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase
from fastapi_filterdeps.core.exceptions import InvalidValueError


class RelativeTimeMatchType(str, Enum):
    """Defines how to match a relative time calculation."""

    # Represents a range from the calculated past/future time up to the present.
    # e.g., for "-7d", the range is [now - 7 days, now]
    RANGE_TO_NOW = "range_to_now"

    # Represents all time strictly before the calculated time.
    # e.g., for "-7d", the condition is < (now - 7 days)
    BEFORE = "before"

    # Represents all time strictly after the calculated time.
    # e.g., for "+3d", the condition is > (now + 3 days)
    AFTER = "after"


class RelativeTimeCriteria(SimpleFilterCriteriaBase):
    """A filter for relative datetime comparisons using a concise string format.

    This class allows filtering records based on a datetime field relative to the
    current time. The matching behavior can be controlled via `RelativeTimeMatchType`.

    The format for the input string is: `[sign][value][unit]`.
    - `sign`: `+` or `-` (optional, defaults to `-`).
    - `value`: An integer.
    - `unit`: `d` (day), `w` (week), `m` (month), `y` (year) (case-insensitive).

    Args:
        field (str): The name of the SQLAlchemy model's datetime field.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        match_type (RelativeTimeMatchType): The matching strategy to use.
            Defaults to `RANGE_TO_NOW`.
        include_bound (bool): For `BEFORE` and `AFTER` types, whether to include
            the calculated datetime in the comparison (i.e., use `<=` or `>=`).
            For `RANGE_TO_NOW`, this applies to both ends of the range.
        description (Optional[str]): A custom description for the OpenAPI documentation.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            class PostFilterSet(FilterSet):
                # Finds posts created in the last 7 days
                created_within = RelativeTimeCriteria(
                    field="created_at",
                    match_type=RelativeTimeMatchType.RANGE_TO_NOW,
                )

                # Finds posts created before 1 month ago
                created_before = RelativeTimeCriteria(
                    field="created_at",
                    alias="created_before",
                    match_type=RelativeTimeMatchType.BEFORE,
                    include_bound=False, # strictly before (<)
                )
    """

    _pattern = re.compile(r"^([+-]?)(\d+)([dwmyDWMY])$")

    def __init__(
        self,
        field: str,
        alias: Optional[str] = None,
        *,
        match_type: RelativeTimeMatchType = RelativeTimeMatchType.RANGE_TO_NOW,
        include_bound: bool = True,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        query_params_with_regex = {
            "pattern": self._pattern.pattern,
            **query_params,
        }
        super().__init__(
            field=field,
            alias=alias,
            description=description,
            bound_type=str,
            **query_params_with_regex,
        )
        self.match_type = match_type
        self.include_bound = include_bound

    def _get_default_description(self) -> str:
        """Generates a default description for the filter."""
        base_desc = (
            f"Filter by relative time on '{self.field}' with match type '{self.match_type.value}'. "
            "Format: [sign][value][unit] (e.g., -7d, +1m, -2y)."
        )
        if self.match_type is RelativeTimeMatchType.RANGE_TO_NOW:
            bound = "inclusive" if self.include_bound else "exclusive"
            base_desc += (
                f" Filters for dates within the calculated range up to now ({bound})."
            )
        else:
            op_str = ">=" if self.include_bound else ">"
            if self.match_type is RelativeTimeMatchType.BEFORE:
                op_str = "<=" if self.include_bound else "<"
            base_desc += (
                f" Uses operator '{op_str}' against the calculated relative time."
            )
        return base_desc

    def _parse_relative_time(self, value: str) -> Tuple[int, str]:
        """Parses a relative time string into an offset and unit."""
        match = self._pattern.match(value)
        if not match:
            raise InvalidValueError(
                f"Invalid relative time format: '{value}'. Expected format like '-7d' or '+1m'."
            )
        sign, num_str, unit_char = match.groups()
        offset = int(num_str)
        if sign == "-":
            offset *= -1
        # A positive sign `+` is handled by default int conversion
        return offset, unit_char.lower()

    def _filter_logic(self, orm_model: Any, value: Optional[str]) -> Any:
        """Generate the SQLAlchemy filter expression for the relative time criteria."""
        if value is None:
            return None

        offset, unit = self._parse_relative_time(value)
        model_field = getattr(orm_model, self.field)
        now = datetime.now()

        delta_map = {
            "d": timedelta(days=offset),
            "w": timedelta(weeks=offset),
            "m": relativedelta(months=offset),
            "y": relativedelta(years=offset),
        }
        delta = delta_map.get(unit)
        if delta is None:
            raise InvalidValueError(f"Invalid time unit: '{unit}'.")

        target_date = now + delta

        if self.match_type == RelativeTimeMatchType.RANGE_TO_NOW:
            start_date, end_date = (
                (target_date, now) if offset <= 0 else (now, target_date)
            )

            op_start = model_field.__ge__ if self.include_bound else model_field.__gt__
            op_end = model_field.__le__ if self.include_bound else model_field.__lt__
            return [op_start(start_date), op_end(end_date)]

        elif self.match_type == RelativeTimeMatchType.BEFORE:
            op = model_field.__le__ if self.include_bound else model_field.__lt__
            return op(target_date)

        elif self.match_type == RelativeTimeMatchType.AFTER:
            op = model_field.__ge__ if self.include_bound else model_field.__gt__
            return op(target_date)

        return None
