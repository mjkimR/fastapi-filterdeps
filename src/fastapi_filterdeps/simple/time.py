from datetime import datetime
from enum import Enum
from typing import Any, Optional


from fastapi_filterdeps.base import SimpleFilterCriteriaBase


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


class TimeCriteria(SimpleFilterCriteriaBase):
    """A filter for a single, absolute datetime comparison.

    This class creates a filter for a datetime field against a specific point in
    time, using an operator like "greater than" or "less than". To create a
    fixed date range (e.g., from a start date to an end date), combine two
    instances of this class.

    Attributes:
        field (str): The name of the SQLAlchemy model's datetime field.
        alias (str): The alias for the query parameter in the API endpoint.
        match_type (TimeMatchType): The comparison operator to use.
        description (Optional[str]): A custom description for the OpenAPI documentation.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        In a FastAPI app, define filters for a 'Post' model's published date::

            from .models import Post
            from fastapi_filterdeps import create_combined_filter_dependency
            from fastapi_filterdeps.generic.time import TimeCriteria, TimeMatchType

            post_filters = create_combined_filter_dependency(
                TimeCriteria(
                    field="published_at",
                    alias="published_after",
                    match_type=TimeMatchType.GTE,
                    description="Filter posts published after a certain date"
                ),
                TimeCriteria(
                    field="published_at",
                    alias="published_before",
                    match_type=TimeMatchType.LTE,
                    description="Filter posts published before a certain date"
                ),
                orm_model=Post,
            )

            # In your endpoint, a request like GET /posts?published_after=2023-01-01&published_before=2023-12-31
            # will filter for posts published in 2023.
    """

    def __init__(
        self,
        field: str,
        match_type: TimeMatchType,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the absolute time filter criterion.

        Args:
            field: The name of the SQLAlchemy model's datetime field.
            alias: The alias for the query parameter in the API.
            match_type: The comparison operator to use.
            description: A custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        super().__init__(field, alias, description, datetime, **query_params)
        self.match_type = match_type

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

    def _validation_logic(self, orm_model):
        self._validate_enum_value(
            self.match_type, TimeMatchType.get_all_operators(), "match_type"
        )

    def _filter_logic(self, orm_model, value):
        model_field = getattr(orm_model, self.field)
        op_map = {
            TimeMatchType.GTE: model_field >= value,
            TimeMatchType.GT: model_field > value,
            TimeMatchType.LTE: model_field <= value,
            TimeMatchType.LT: model_field < value,
        }
        return op_map.get(self.match_type)
