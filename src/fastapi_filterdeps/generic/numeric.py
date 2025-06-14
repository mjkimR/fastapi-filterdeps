import operator
from enum import Enum
from typing import Any, Callable, Optional, Union

from fastapi import Query
from sqlalchemy import ColumnElement


from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.exceptions import InvalidValueError


class NumericFilterType(str, Enum):
    """Enum for numeric comparison operators."""

    gt = ">"
    ge = ">="
    lt = "<"
    le = "<="
    eq = "=="
    ne = "!="

    @classmethod
    def get_all_operators(cls) -> set[str]:
        return set(op.value for op in cls)


class NumericCriteria(SqlFilterCriteriaBase):
    """A filter criterion for numeric fields."""

    def __init__(
        self,
        *,
        field: str,
        alias: str,
        numeric_type: type[Union[int, float]],
        operator: NumericFilterType,
        description: Optional[str] = None,
    ):
        """
        Args:
            field (str): The ORM model field name to filter on.
            alias (str): The alias for the query parameter in the API.
            numeric_type (type[T]): The type of the numeric value (e.g., int, float).
            operator (NumericFilterType): The comparison operator to use.
            description (Optional[str]): The description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.numeric_type = numeric_type
        self.operator = operator
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Generate default description based on filter type."""
        if self.operator == NumericFilterType.eq:
            return f"Filter records where {self.field} is equal"
        elif self.operator == NumericFilterType.ne:
            return f"Filter records where {self.field} is not equal"
        elif self.operator == NumericFilterType.gt:
            return f"Filter records where {self.field} is greater than"
        elif self.operator == NumericFilterType.ge:
            return f"Filter records where {self.field} is greater than or equal"
        elif self.operator == NumericFilterType.lt:
            return f"Filter records where {self.field} is less than"
        elif self.operator == NumericFilterType.le:
            return f"Filter records where {self.field} is less than or equal"
        else:
            raise InvalidValueError(f"Invalid operator: {self.operator}")

    def build_filter(self, orm_model: type) -> ColumnElement[bool] | bool:
        """Build the sqlalchemy filter expression."""
        self._validate_field_exists(orm_model, self.field)
        self._validate_enum_value(
            self.operator, NumericFilterType.get_all_operators(), "operator"
        )

        orm_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[self.numeric_type] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            if value is None:
                return None

            if self.operator == NumericFilterType.eq:
                return orm_field == value
            elif self.operator == NumericFilterType.ne:
                return orm_field != value
            elif self.operator == NumericFilterType.gt:
                return orm_field > value
            elif self.operator == NumericFilterType.ge:
                return orm_field >= value
            elif self.operator == NumericFilterType.lt:
                return orm_field < value
            elif self.operator == NumericFilterType.le:
                return orm_field <= value
            else:
                raise InvalidValueError(f"Invalid operator: {self.operator}")

        return filter_dependency
