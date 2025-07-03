from datetime import datetime
from enum import Enum
from typing import Any, Optional

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase


class TimeMatchType(str, Enum):
    """Defines the available comparison operators for datetime fields.

    * GTE: Greater than or equal to (>=).

    * GT: Greater than (>).

    * LTE: Less than or equal to (<=).

    * LT: Less than (<).
    """

    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Return all available operator values for time filtering.

        Returns:
            set[str]: Set of all operator string values.
        """
        return {op.value for op in cls}


class TimeCriteria(SimpleFilterCriteriaBase):
    """A filter for a single, absolute datetime comparison.

    Inherits from SimpleFilterCriteriaBase. This class creates a filter for a datetime field against a specific point in
    time, using an operator like "greater than" or "less than". To create a
    fixed date range (e.g., from a start date to an end date), combine two
    instances of this class as attributes of a FilterSet.

    Args:
        field (str): The name of the SQLAlchemy model's datetime field.
        match_type (TimeMatchType): The comparison operator to use.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        description (Optional[str]): A custom description for the OpenAPI documentation.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.time import TimeCriteria, TimeMatchType
            from myapp.models import Post

            class PostFilterSet(FilterSet):
                published_after = TimeCriteria(
                    field="published_at",
                    alias="published_after",
                    match_type=TimeMatchType.GTE,
                    description="Filter posts published after a certain date"
                )
                published_before = TimeCriteria(
                    field="published_at",
                    alias="published_before",
                    match_type=TimeMatchType.LTE,
                    description="Filter posts published before a certain date"
                )
                class Meta:
                    orm_model = Post

            # GET /posts?published_after=2023-01-01&published_before=2023-12-31
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
        """Initialize the absolute time filter criterion.

        Args:
            field (str): The name of the SQLAlchemy model's datetime field.
            match_type (TimeMatchType): The comparison operator to use.
            alias (Optional[str]): The alias for the query parameter in the API.
            description (Optional[str]): A custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, datetime, **query_params)
        self.match_type = match_type

    def _get_default_description(self) -> str:
        """Generate a default description based on the filter's configuration.

        Returns:
            str: The default description for the filter.
        """
        op_map = {
            TimeMatchType.GTE: "on or after",
            TimeMatchType.GT: "after",
            TimeMatchType.LTE: "on or before",
            TimeMatchType.LT: "before",
        }
        desc = op_map.get(self.match_type, "matches")
        return f"Filter where '{self.field}' is {desc} the given datetime."

    def _validation_logic(self, orm_model):
        """Validate that the match_type is a valid TimeMatchType value.

        Args:
            orm_model: The SQLAlchemy ORM model class.
        """
        self._validate_enum_value(
            self.match_type, TimeMatchType.get_all_operators(), "match_type"
        )

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the time criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The datetime value from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        op_map = {
            TimeMatchType.GTE: model_field >= value,
            TimeMatchType.GT: model_field > value,
            TimeMatchType.LTE: model_field <= value,
            TimeMatchType.LT: model_field < value,
        }
        return op_map.get(self.match_type)
