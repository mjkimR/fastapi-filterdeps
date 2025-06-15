from enum import Enum
from typing import Callable, Optional, Type, Union

from fastapi import Query
from sqlalchemy import ColumnElement
from sqlalchemy.orm import DeclarativeBase


from fastapi_filterdeps.base import SqlFilterCriteriaBase


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


class NumericCriteria(SqlFilterCriteriaBase):
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

    Examples:
        # In a FastAPI app, define filters for a 'Post' model with a
        # 'view_count' integer field.

        from .models import Post
        from fastapi_filterdeps import create_combined_filter_dependency

        post_filters = create_combined_filter_dependency(
            # Creates a 'views_exact' parameter for an exact match.
            # e.g., /posts?views_exact=100
            NumericCriteria(
                field="view_count",
                alias="views_exact",
                numeric_type=int,
                operator=NumericFilterType.EQ,
            ),
            # Creates a 'min_views' parameter for a "greater than or equal to"
            # filter, establishing the lower bound of a range.
            # e.g., /posts?min_views=50
            NumericCriteria(
                field="view_count",
                alias="min_views",
                numeric_type=int,
                operator=NumericFilterType.GTE,
                description="Filter posts with at least this many views."
            ),
            # Creates a 'max_views' parameter for a "less than or equal to"
            # filter, establishing the upper bound of a range.
            # e.g., /posts?max_views=1000
            NumericCriteria(
                field="view_count",
                alias="max_views",
                numeric_type=int,
                operator=NumericFilterType.LTE,
            ),
            orm_model=Post,
        )

        # @app.get("/posts")
        # def list_posts(filters=Depends(post_filters)):
        #     # A request like /posts?min_views=50&max_views=1000 will
        #     # find posts where view_count is between 50 and 1000.
        #     query = select(Post).where(*filters)
        #     ...
    """

    def __init__(
        self,
        *,
        field: str,
        alias: str,
        numeric_type: Type[Union[int, float]],
        operator: NumericFilterType,
        description: Optional[str] = None,
    ):
        """Initializes the numeric filter criterion.

        Args:
            field: The name of the SQLAlchemy model field to filter on.
            alias: The alias for the query parameter in the API.
            numeric_type: The Python type of the numeric value (e.g., `int`).
            operator: The comparison operator to use.
            description: The description for the filter parameter in OpenAPI.
        """
        self.field = field
        self.alias = alias
        self.numeric_type = numeric_type
        self.operator = operator
        self.description = description or self._get_default_description()

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

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for numeric comparison filtering.

        This method validates the provided field and operator, then creates a
        callable FastAPI dependency. This dependency will produce the correct

        SQLAlchemy filter expression when resolved by FastAPI during a request.

        Args:
            orm_model: The SQLAlchemy model class to apply the filter to.

        Returns:
            A FastAPI dependency that returns a SQLAlchemy filter
            condition (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the
                `orm_model`.
            InvalidValueError: If the `operator` is not a valid
                `NumericFilterType`.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_enum_value(
            self.operator, NumericFilterType.get_all_operators(), "operator"
        )

        orm_field = getattr(orm_model, self.field)

        def filter_dependency(
            value: Optional[self.numeric_type] = Query(  # type: ignore
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            """Generates a numeric comparison filter condition.

            Args:
                value: The numeric value from the query parameter. If None, no
                    filter is applied.

            Returns:
                A SQLAlchemy filter expression, or `None` if no value
                was provided.
            """
            if value is None:
                return None

            op_map = {
                NumericFilterType.EQ: orm_field == value,
                NumericFilterType.NE: orm_field != value,
                NumericFilterType.GT: orm_field > value,
                NumericFilterType.GTE: orm_field >= value,
                NumericFilterType.LT: orm_field < value,
                NumericFilterType.LTE: orm_field <= value,
            }
            return op_map[self.operator]

        return filter_dependency
