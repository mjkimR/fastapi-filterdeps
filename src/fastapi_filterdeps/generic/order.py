from enum import Enum
from typing import Any, Callable, List, Optional

from fastapi import Query
from sqlalchemy import func, select, tuple_
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class OrderType(str, Enum):
    """Specifies the ordering direction for the `OrderCriteria` filter.

    Attributes:
        MAX: Selects the record with the highest value in the ordering field.
             For datetimes, this corresponds to the most recent record.
        MIN: Selects the record with the lowest value in the ordering field.
             For datetimes, this corresponds to the oldest record.
    """

    MAX = "max"
    MIN = "min"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Returns a set of all available operator values."""
        return {op.value for op in cls}


class OrderCriteria(SqlFilterCriteriaBase):
    """A filter to select records with the maximum or minimum value in a group.

    This filter uses a `ROW_NUMBER()` window function to find the single
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

    Attributes:
        field (str): The name of the SQLAlchemy model field to use for ordering
            (e.g., `created_at`, `price`).
        partition_by (Optional[List[str]]): A list of field names to define
            the groups (partitions). For each unique combination of these
            fields, one record will be selected. If omitted, the filter finds
            the single global maximum or minimum record.
        order_type (OrderType): The ordering direction, either `OrderType.MAX`
            to find the highest value or `OrderType.MIN` to find the lowest.
            Defaults to `OrderType.MAX`.
        alias (Optional[str]): The alias for the boolean query parameter in the
            API. If not provided, it is auto-generated (e.g., "created_at_max").
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        In a FastAPI app, select the latest post per user::

            from .models import Post
            from fastapi_filterdeps import create_combined_filter_dependency
            from fastapi_filterdeps.generic.order import OrderCriteria, OrderType

            post_filters = create_combined_filter_dependency(
                OrderCriteria(
                    field="created_at",
                    partition_by=["user_id"],
                    order_type=OrderType.MAX,
                    alias="latest_per_user",
                    description="Select the latest post per user."
                ),
                orm_model=Post,
            )

            # @app.get("/posts")
            # def list_posts(filters=Depends(post_filters)):
            #     query = select(Post).where(*filters)
            #     ...
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
        """Initializes the order filter criterion.

        Args:
            field: The model field name for ordering (e.g., a datetime or numeric
                field).
            partition_by: A list of field names to partition the data by. If
                None, a global max/min is found.
            order_type: The direction of ordering (`MAX` or `MIN`). Defaults
                to `OrderType.MAX`.
            alias: The alias for the query parameter. Auto-generated if None.
            description: Custom description for the OpenAPI documentation.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        self.field = field
        self.partition_by = partition_by or []
        self.order_type = order_type
        self.alias = alias or f"{field}_{order_type.value}"
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            The default description for the OpenAPI documentation.
        """
        order_str = "maximum" if self.order_type == OrderType.MAX else "minimum"
        if not self.partition_by:
            return f"Filter for the record with the {order_str} value of '{self.field}' globally."

        partition_fields = ", ".join(self.partition_by)
        return f"Filter for records with the {order_str} value of '{self.field}' within each partition of '{partition_fields}'."

    def _get_order_by_criteria(
        self, model_field: ColumnElement, orm_model: type[DeclarativeBase]
    ) -> List[ColumnElement]:
        """Constructs the full ORDER BY clause, including primary key tie-breakers.

        This ensures that the `ROW_NUMBER()` function produces deterministic
        results even when multiple rows have the same value in the primary
        ordering field.

        Args:
            model_field: The SQLAlchemy column element to order by.
            orm_model: The SQLAlchemy model class, used to inspect primary keys.

        Returns:
            A list of SQLAlchemy column elements for the `ORDER BY` clause.
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

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for order-based filtering.

        Note:
            This implementation requires the target model to have at least one
            primary key defined. The primary key is essential for ensuring
            consistent and correct filtering when multiple records have the same
            value in the ordering field.

        Args:
            orm_model: The SQLAlchemy model class to create the filter for.

        Returns:
            A FastAPI dependency that returns a SQLAlchemy filter condition
            or `None`.

        Raises:
            InvalidFieldError: If the `field` or any `partition_by` fields do not
                exist on the model, or if the model has no primary keys.
        """
        # Validate field existence
        self._validate_field_exists(orm_model, self.field)
        for partition_field in self.partition_by:
            self._validate_field_exists(orm_model, partition_field)

        # Validate primary key existence
        self._validate_model_has_primary_keys(orm_model)

        model_field = getattr(orm_model, self.field)
        partition_fields = [getattr(orm_model, field) for field in self.partition_by]

        def filter_dependency(
            enabled: bool = Query(
                default=True,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates a filter condition for maximum/minimum values.

            Args:
                enabled: The boolean flag from the query parameter that
                    activates the filter.

            Returns:
                A SQLAlchemy filter condition using a subquery, or `None` if
                filtering is disabled.
            """
            if not enabled:
                return None

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

        return filter_dependency
