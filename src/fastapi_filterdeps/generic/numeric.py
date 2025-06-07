from typing import Optional, TypeVar, Union
from fastapi import Query
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import or_, and_

from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.exceptions import InvalidValueError


NumericType = TypeVar("NumericType", bound=Union[int, float])


class NumericRangeCriteria(SqlFilterCriteriaBase):
    """Base filter for numeric field range operations.

    Provides a generic implementation for filtering numeric fields using
    range conditions (between, not between).

    Attributes:
        field (str): Model field name to filter on.
        min_alias (str): Query parameter name for minimum value.
        max_alias (str): Query parameter name for maximum value.
        numeric_type (type[NumericType]): The type of numeric field to filter on.
        exclude (bool): Whether to use NOT BETWEEN instead of BETWEEN.
        include_min_bound (bool): Whether to include the minimum bound in the filter conditions.
        include_max_bound (bool): Whether to include the maximum bound in the filter conditions.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        # Filter products by price range (inclusive bounds)
        price_range_filter = NumericRangeCriteria(
            field="price",
            min_alias="min_price",
            max_alias="max_price",
            numeric_type=float,
            exclude=False,
            include_min_bound=True,
            include_max_bound=True
        )

        # Filter users by age range (exclusive bounds)
        age_range_filter = NumericRangeCriteria(
            field="age",
            min_alias="min_age",
            max_alias="max_age",
            numeric_type=int,
            exclude=False,
            include_min_bound=False,
            include_max_bound=False
        )

        # Filter items outside a specific quantity range
        quantity_range_filter = NumericRangeCriteria(
            field="quantity",
            min_alias="exclude_min_qty",
            max_alias="exclude_max_qty",
            numeric_type=int,
            exclude=True  # Will match items with quantity outside the range
        )
    """

    def __init__(
        self,
        field: str,
        min_alias: str,
        max_alias: str,
        numeric_type: type[NumericType],
        exclude: bool = False,
        include_min_bound: bool = True,
        include_max_bound: bool = True,
        description: Optional[str] = None,
    ):
        """Initialize the numeric range filter.

        Args:
            field (str): Model field name to filter on.
            min_alias (str): Query parameter name for minimum value.
            max_alias (str): Query parameter name for maximum value.
            numeric_type (type[NumericType]): The type of numeric field to filter on.
            exclude (bool): Whether to use NOT BETWEEN instead of BETWEEN.
            include_min_bound (bool): Whether to include the minimum bound in the filter conditions.
            include_max_bound (bool): Whether to include the maximum bound in the filter conditions.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.min_alias = min_alias
        self.max_alias = max_alias
        self.numeric_type = numeric_type
        self.exclude = exclude
        self.include_min_bound = include_min_bound
        self.include_max_bound = include_max_bound
        self.min_description = description or self._get_min_description()
        self.max_description = description or self._get_max_description()

    def _get_min_description(self) -> str:
        """Get default description for the minimum value filter.

        Returns:
            str: Default description for minimum value
        """
        bound_type = "inclusive" if self.include_min_bound else "exclusive"
        exclude_info = "not " if self.exclude else ""
        return f"{bound_type.capitalize()} minimum value for {self.field} ({exclude_info}between)"

    def _get_max_description(self) -> str:
        """Get default description for the maximum value filter.

        Returns:
            str: Default description for maximum value
        """
        bound_type = "inclusive" if self.include_max_bound else "exclusive"
        exclude_info = "not " if self.exclude else ""
        return f"{bound_type.capitalize()} maximum value for {self.field} ({exclude_info}between)"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for numeric range filtering.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for.

        Returns:
            callable: FastAPI dependency function that returns list of SQLAlchemy filter conditions.

        Raises:
            InvalidFieldError: If the specified field doesn't exist on the model.
            InvalidValueError: If the provided range values are invalid.
        """
        self._validate_field_exists(orm_model, self.field)
        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            min_value: Optional[self.numeric_type] = Query(
                default=None,
                alias=self.min_alias,
                description=self.min_description,
            ),
            max_value: Optional[self.numeric_type] = Query(
                default=None,
                alias=self.max_alias,
                description=self.max_description,
            ),
        ) -> Optional[ColumnElement]:
            """Generate numeric range filter conditions.

            Args:
                min_value (Optional[self.numeric_type]): Minimum value for range filter.
                max_value (Optional[self.numeric_type]): Maximum value for range filter.

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no filter is applied.

            Raises:
                InvalidValueError: If min_value is greater than max_value.
            """
            if min_value is not None and max_value is not None:
                if min_value > max_value:
                    raise InvalidValueError(
                        f"Minimum value ({min_value}) cannot be greater than maximum value ({max_value})"
                    )

            filters = []

            if min_value is not None:
                if self.exclude:
                    if self.include_min_bound:
                        filters.append(model_field < min_value)
                    else:
                        filters.append(model_field <= min_value)
                else:
                    if self.include_min_bound:
                        filters.append(model_field >= min_value)
                    else:
                        filters.append(model_field > min_value)

            if max_value is not None:
                if self.exclude:
                    if self.include_max_bound:
                        filters.append(model_field > max_value)
                    else:
                        filters.append(model_field >= max_value)
                else:
                    if self.include_max_bound:
                        filters.append(model_field <= max_value)
                    else:
                        filters.append(model_field < max_value)

            if not filters:
                return None

            # Combine filters with OR for exclude=True, AND for exclude=False
            if self.exclude:
                return or_(*filters)
            else:
                return and_(*filters)

        return filter_dependency


class NumericExactCriteria(SqlFilterCriteriaBase):
    """Base filter for exact numeric field matching.

    Provides a generic implementation for filtering numeric fields using
    exact value matching (equal or not equal).

    Attributes:
        field (str): Model field name to filter on.
        alias (str): Query parameter name to use in API endpoints.
        numeric_type (type[NumericType]): The type of numeric field to filter on.
        exclude (bool): Whether to use not equal instead of equal.
        description (Optional[str]): Custom description for the filter parameter.

    Examples:
        # Filter products by exact price
        exact_price_filter = NumericExactCriteria(
            field="price",
            alias="exact_price",
            numeric_type=float
        )

        # Filter orders by quantity not equal to specific value
        exclude_quantity_filter = NumericExactCriteria(
            field="quantity",
            alias="exclude_qty",
            numeric_type=int,
            exclude=True  # Will match orders where quantity != specified value
        )

        # Filter ratings by exact score
        rating_filter = NumericExactCriteria(
            field="score",
            alias="rating",
            numeric_type=float,
            description="Filter reviews by exact rating score"
        )
    """

    def __init__(
        self,
        field: str,
        alias: str,
        numeric_type: type[NumericType],
        exclude: bool = False,
        description: Optional[str] = None,
    ):
        """Initialize the numeric exact filter.

        Args:
            field (str): Model field name to filter on.
            alias (str): Query parameter name to use in API endpoints.
            numeric_type (type[NumericType]): The type of numeric field to filter on.
            exclude (bool): Whether to use not equal instead of equal.
            description (Optional[str]): Custom description for the filter parameter.
        """
        self.field = field
        self.alias = alias
        self.numeric_type = numeric_type
        self.exclude = exclude
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        return f"Filter {self.field} where value is {'not ' if self.exclude else ''}equal to the specified value"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for numeric exact filtering.

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
            value: Optional[self.numeric_type] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            """Generate numeric exact filter conditions.

            Args:
                value (Optional[self.numeric_type]): Value to match against.

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if no filter is applied.
            """
            if value is None:
                return None

            return model_field != value if self.exclude else model_field == value

        return filter_dependency
