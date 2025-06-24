from enum import Enum
from typing import Any, List, Optional

from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase


class OrderType(str, Enum):
    """Specifies the ordering direction for the `OrderCriteria` filter.

    Attributes:
        MAX: Selects the record with the highest value in the ordering field.
        MIN: Selects the record with the lowest value in the ordering field.
    """

    MAX = "max"
    MIN = "min"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Return all available operator values for ordering.

        Returns:
            set[str]: Set of all operator string values.
        """
        return {op.value for op in cls}


class OrderCriteria(SimpleFilterCriteriaBase):
    """A filter to select records with the maximum or minimum value in a group.

    Inherits from SimpleFilterCriteriaBase. This filter uses a `ROW_NUMBER()` window function to find the single
    top-ranked (or bottom-ranked) record within specified partitions. This is
    highly efficient for tasks like finding the latest status update for each
    ticket, the most expensive product in each category, or the oldest user
    in each country.

    The filter works by ranking records within each group and selecting only the
    one ranked number 1. For determinism, if multiple records share the same
    value in the ordering field, the model's primary key(s) are automatically
    used as a tie-breaker. This guarantees stable and consistent results.

    The generated API query parameter is a boolean flag that enables or disables
    this filter. It is enabled by default.

    Args:
        field (str): The name of the SQLAlchemy model field to use for ordering.
        partition_by (Optional[List[str]]): A list of field names to define the groups (partitions).
        order_type (OrderType): The ordering direction, either `OrderType.MAX` or `OrderType.MIN`. Defaults to `OrderType.MAX`.
        alias (Optional[str]): The alias for the boolean query parameter in the API.
        description (Optional[str]): A custom description for the OpenAPI documentation. A default is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.column.order import OrderCriteria, OrderType
            from myapp.models import Post

            class PostFilterSet(FilterSet):
                latest_per_user = OrderCriteria(
                    field="created_at",
                    partition_by=["user_id"],
                    order_type=OrderType.MAX,
                    alias="latest_per_user",
                    description="Select the latest post per user."
                )
                class Meta:
                    orm_model = Post

            # GET /posts?latest_per_user=true
            # will select the latest post per user.
    """

    def __init__(
        self,
        field: str,
        partition_by: Optional[List[str]] = None,
        order_type: OrderType = OrderType.MAX,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initialize the order filter criterion.

        Args:
            field (str): The model field name for ordering.
            partition_by (Optional[List[str]]): A list of field names to partition the data by. If None, a global max/min is found.
            order_type (OrderType): The direction of ordering (`MAX` or `MIN`). Defaults to `OrderType.MAX`.
            alias (Optional[str]): The alias for the query parameter. Auto-generated if None.
            description (Optional[str]): Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        super().__init__(field, alias, description, bool, **query_params)
        self.partition_by = partition_by or []
        self.order_type = order_type

    def _get_default_description(self) -> str:
        """Generate a default description for the filter.

        Returns:
            str: The default description for the OpenAPI documentation.
        """
        order_str = "maximum" if self.order_type == OrderType.MAX else "minimum"
        if not self.partition_by:
            return f"Filter for the record with the {order_str} value of '{self.field}' globally."
        partition_fields = ", ".join(self.partition_by)
        return f"Filter for records with the {order_str} value of '{self.field}' within each partition of '{partition_fields}'."

    def _get_order_by_criteria(
        self, model_field: ColumnElement, orm_model: type[DeclarativeBase]
    ) -> List[ColumnElement]:
        """Construct the full ORDER BY clause, including primary key tie-breakers.

        This ensures that the `ROW_NUMBER()` function produces deterministic
        results even when multiple rows have the same value in the primary
        ordering field.

        Args:
            model_field: The SQLAlchemy column element to order by.
            orm_model: The SQLAlchemy model class, used to inspect primary keys.
        Returns:
            List[ColumnElement]: List of SQLAlchemy column elements for the `ORDER BY` clause.
        """
        order_by = []

        # Add main ordering field
        if self.order_type == OrderType.MAX:
            order_by.append(model_field.desc())
        else:
            order_by.append(model_field.asc())

        # Add primary keys for consistent ordering as a tie-breaker
        pk_columns = self.get_primary_keys(orm_model)
        if self.order_type == OrderType.MAX:
            order_by.extend(pk.desc() for pk in pk_columns)
        else:
            order_by.extend(pk.asc() for pk in pk_columns)

        return order_by

    def _validation_logic(self, orm_model):
        """Validate partition fields and primary key existence.

        Args:
            orm_model: The SQLAlchemy ORM model class.
        """
        # Validate field existence
        for partition_field in self.partition_by:
            self._validate_field_exists(orm_model, partition_field)

        # Validate primary key existence
        self._validate_model_has_primary_keys(orm_model)

    def _filter_logic(self, orm_model, value):
        """Generate the SQLAlchemy filter expression for the order criteria.

        Args:
            orm_model: The SQLAlchemy ORM model class.
            value: The boolean value from the query parameter.
        Returns:
            The SQLAlchemy filter expression or None if value is None.
        """
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        partition_fields = [getattr(orm_model, field) for field in self.partition_by]

        # Create window function for ranking with PK-based tie-breaking
        order_by_clause = self._get_order_by_criteria(model_field, orm_model)
        row_number_func = (
            func.row_number()
            .over(partition_by=partition_fields, order_by=order_by_clause)
            .label("row_number")
        )

        # Create subquery that includes the row number for each record
        subquery = select(orm_model, row_number_func).subquery()

        # Create the final filter: select the primary keys from the subquery
        # where the rank is 1, and filter the main query with an IN clause.
        pk_cols = self.get_primary_keys(orm_model)
        pk_attrs = [getattr(orm_model, pk.name) for pk in pk_cols]
        subq_pk_attrs = [getattr(subquery.c, pk.name) for pk in pk_cols]

        return tuple_(*pk_attrs).in_(
            select(*subq_pk_attrs).where(subquery.c.row_number == 1)
        )
