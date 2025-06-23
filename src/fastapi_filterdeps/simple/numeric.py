from enum import Enum
from typing import Any, Optional, Type, Union


from fastapi_filterdeps.base import SimpleFilterCriteriaBase


class NumericFilterType(str, Enum):
    """Defines the available numeric comparison operators.

    This enum specifies the comparison strategy for the `NumericCriteria` class.

    Attributes:
        GT: Greater than (>).
        GTE: Greater than or equal to (>=).
        LT: Less than (<).
        LTE: Less than or equal to (<=).
        EQ: Equal to (==).
        NE: Not equal to (!=).
    """

    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    EQ = "eq"
    NE = "ne"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Returns a set of all available operator values."""
        return {op.value for op in cls}


class NumericCriteria(SimpleFilterCriteriaBase):
    """A filter for numeric comparisons (e.g., >, <, ==).

    This class creates a filter for a single numeric comparison on a field, such
    as checking if a value is greater than, less than, or equal to a given
    number.

    To create complex conditions like a numeric range (e.g., value is between 10
    and 100), combine two instances of this class within a single
    `create_combined_filter_dependency` call.

    Attributes:
        field (str): The name of the SQLAlchemy model field to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        numeric_type (Type[Union[int, float]]): The expected Python data type
            of the query parameter's value (e.g., `int`, `float`).
        operator (NumericFilterType): The comparison operator to apply.
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        In a FastAPI app, define filters for a 'Product' model::

            from .models import Product
            from fastapi_filterdeps import create_combined_filter_dependency
            from fastapi_filterdeps.generic.numeric import NumericCriteria, NumericFilterType

            product_filters = create_combined_filter_dependency(
                NumericCriteria(
                    field="price",
                    alias="min_price",
                    numeric_type=float,
                    operator=NumericFilterType.GTE,
                    description="Filter products with price >= min_price"
                ),
                NumericCriteria(
                    field="price",
                    alias="max_price",
                    numeric_type=float,
                    operator=NumericFilterType.LTE,
                    description="Filter products with price <= max_price"
                ),
                orm_model=Product,
            )

            # In your endpoint, a request like GET /products?min_price=10&max_price=100
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
        """Initializes the numeric filter criterion.

        Args:
            field: The name of the SQLAlchemy model field to filter on.
            alias: The alias for the query parameter in the API.
            numeric_type: The Python type of the numeric value (e.g., `int`).
            operator: The comparison operator to use.
            description: The description for the filter parameter in OpenAPI.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        super().__init__(field, alias, description, numeric_type, **query_params)
        self.operator = operator
        self.numeric_type = numeric_type

    def _get_default_description(self) -> str:
        """Generates a default description based on the filter's operator."""
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
        self._validate_enum_value(
            self.operator, NumericFilterType.get_all_operators(), "operator"
        )

    def _filter_logic(self, orm_model, value):
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
