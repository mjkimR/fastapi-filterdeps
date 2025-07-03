from enum import Enum
from typing import Any, Optional, Type, Union

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase


class NumericFilterType(str, Enum):
    """Defines the available numeric comparison operators.

    This enum specifies the comparison strategy for the `NumericCriteria` class.

    * GT: Greater than (>).

    * GTE: Greater than or equal to (>=).

    * LT: Less than (<).

    * LTE: Less than or equal to (<=).

    * EQ: Equal to (==).

    * NE: Not equal to (!=).
    """

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NE = "ne"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Return all available operator values for numeric filtering.

        Returns:
            set[str]: Set of all operator string values.
        """
        return {op.value for op in cls}


class NumericCriteria(SimpleFilterCriteriaBase):
    """A filter for numeric comparisons (e.g., >, <, ==).

    Inherits from SimpleFilterCriteriaBase. This class creates a filter for a single numeric comparison on a field, such
    as checking if a value is greater than, less than, or equal to a given
    number.

    To create complex conditions like a numeric range (e.g., value is between 10
    and 100), combine two instances of this class as attributes of a FilterSet.

    Args:
        field (str): The name of the SQLAlchemy model field to filter on.
        numeric_type (Type[Union[int, float]]): The expected Python data type of the query parameter's value (e.g., `int`, `float`).
        operator (NumericFilterType): The comparison operator to apply.
        alias (Optional[str]): The alias for the query parameter in the API endpoint.
        description (Optional[str]): A custom description for the OpenAPI documentation. A default is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.numeric import NumericCriteria, NumericFilterType
            from myapp.models import Product

            class ProductFilterSet(FilterSet):
                min_price = NumericCriteria(
                    field="price",
                    alias="min_price",
                    numeric_type=float,
                    operator=NumericFilterType.GTE,
                    description="Filter products with price >= min_price"
                )
                max_price = NumericCriteria(
                    field="price",
                    alias="max_price",
                    numeric_type=float,
                    operator=NumericFilterType.LTE,
                    description="Filter products with price <= max_price"
                )
                class Meta:
                    orm_model = Product

            # GET /products?min_price=10&max_price=100
            # will filter for products with price between 10 and 100.
    """

    def __init__(
        self,
        *,
        field: str,
        numeric_type: Type[Union[int, float]],
        operator: NumericFilterType,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initialize the numeric filter criterion.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            numeric_type (Type[Union[int, float]]): The Python type of the numeric value (e.g., `int`).
            operator (NumericFilterType): The comparison operator to use.
            alias (Optional[str]): The alias for the query parameter in the API.
            description (Optional[str]): The description for the filter parameter in OpenAPI.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, numeric_type, **query_params)
        self.operator = operator
        self.numeric_type = numeric_type

    def _get_default_description(self) -> str:
        """Generate a default description based on the filter's operator.

        Returns:
            str: The default description for the filter.
        """
        op_map = {
            NumericFilterType.EQ: "is equal to",
            NumericFilterType.NE: "is not equal to",
            NumericFilterType.GT: "is greater than",
            NumericFilterType.GTE: "is greater than or equal to",
            NumericFilterType.LT: "is less than",
            NumericFilterType.LTE: "is less than or equal to",
        }
        desc = op_map.get(self.operator, f"uses operator {self.operator} on")
        return f"Filter records where '{self.field}' {desc} the given value."

    def _validation_logic(self, orm_model):
        """Validate that the operator is a valid NumericFilterType value.

        Args:
            orm_model: The SQLAlchemy ORM model class.
        """
        self._validate_enum_value(
            self.operator, NumericFilterType.get_all_operators(), "operator"
        )

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the numeric criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The numeric value from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        op_map = {
            NumericFilterType.EQ: model_field == value,
            NumericFilterType.NE: model_field != value,
            NumericFilterType.GT: model_field > value,
            NumericFilterType.GTE: model_field >= value,
            NumericFilterType.LT: model_field < value,
            NumericFilterType.LTE: model_field <= value,
        }
        return op_map[self.operator]
