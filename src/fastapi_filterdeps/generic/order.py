from enum import Enum
from typing import Optional
from fastapi import Query
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, func, tuple_

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class OrderType(str, Enum):
    """Order types for filtering.

    Available types:
    - MAX: Get instances with maximum value. For datetime fields, this will get the latest records.
    - MIN: Get instances with minimum value. For datetime fields, this will get the oldest records.
    """

    MAX = "max"
    MIN = "min"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        return set(op.value for op in cls)


class OrderCriteria(SqlFilterCriteriaBase):
    """Base filter for getting instances with maximum/minimum values.

    Provides filtering capabilities to get instances that have the maximum
    or minimum value for a specific field using window functions (ROW_NUMBER).
    This is particularly useful for scenarios like:
    - Getting the highest/lowest value per partition
    - Finding the latest/oldest record per group
    - Selecting records with extreme values based on any comparable field

    The filter uses ROW_NUMBER() window function to rank records within their
    partitions, then selects only the top ranked record from each partition.
    This approach is generally more efficient than using subqueries with GROUP BY.

    For consistent results when multiple records have the same value, the filter
    automatically includes primary keys in the ordering criteria. This ensures:
    1. Deterministic ordering even with duplicate values
    2. Consistent results across multiple queries
    3. Stable sorting within each partition

    Examples:
        # Get most expensive product per category
        # If multiple products have the same price, ordering by PK ensures consistency
        max_price_filter = OrderCriteria(
            field="price",
            partition_by=["category_id"],
            order_type=OrderType.MAX
        )

        # Get oldest order per customer
        # If multiple orders have the same timestamp, they'll be ordered by PK
        oldest_order_filter = OrderCriteria(
            field="created_at",
            partition_by=["customer_id"],
            order_type=OrderType.MIN
        )

        # Get latest status update per ticket
        # Primary key ordering ensures consistent results for simultaneous updates
        latest_status_filter = OrderCriteria(
            field="updated_at",
            partition_by=["ticket_id"],
            order_type=OrderType.MAX
        )

        # Get most recent record per user without partitioning
        latest_record_filter = OrderCriteria(
            field="updated_at",
            order_type=OrderType.MAX
        )
    """

    def __init__(
        self,
        field: str,
        partition_by: Optional[list[str]] = None,
        order_type: OrderType = OrderType.MAX,
        alias: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """Initialize the order filter.

        Args:
            field (str): Model field name to filter on. Can be any comparable field
                        (numeric, datetime, string, etc.)
            partition_by (Optional[list[str]]): List of fields to partition by. These fields define
                                              the context in which to find the max/min values.
                                              If None, finds global max/min.
            order_type (OrderType): Type of ordering to apply (MAX or MIN)
            alias (Optional[str]): Query parameter name to use in API endpoints
            description (Optional[str]): Custom description for the filter parameter
        """
        self.field = field
        self.partition_by = partition_by or []
        self.order_type = order_type
        self.alias = alias or f"{field}_{order_type.value}"
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        Returns:
            str: Default description based on the filter configuration
        """
        if not self.partition_by:
            return f"Filter instances where {self.field} is {self.order_type.value} globally"

        partition_fields = ", ".join(self.partition_by)
        return (
            f"Filter instances where {self.field} is {self.order_type.value} "
            f"within each partition of {partition_fields}"
        )

    def _get_order_by_criteria(
        self, model_field: ColumnElement, orm_model: type[DeclarativeBase]
    ) -> list[ColumnElement]:
        """Get the complete ordering criteria including primary keys.

        This method creates a list of columns to order by, ensuring consistent
        results even when multiple records have the same value in the target field.
        The ordering is:
        1. The target field (ascending/descending based on order_type)
        2. Primary keys (in the same direction as the target field) if available

        If the model doesn't have primary keys (e.g., log tables), the ordering
        will only use the target field.

        Args:
            model_field: The field to order by
            orm_model: The SQLAlchemy model class

        Returns:
            list[ColumnElement]: List of columns to use in ORDER BY clause

        Raises:
            InvalidFieldError: If the model doesn't have primary key(s)
        """
        order_by = []

        # Add main ordering field
        if self.order_type == OrderType.MAX:
            order_by.append(model_field.desc())
        else:
            order_by.append(model_field.asc())

        # Add primary keys for consistent ordering
        pk_columns = self.get_primary_keys(orm_model)
        if self.order_type == OrderType.MAX:
            order_by.extend(pk.desc() for pk in pk_columns)
        else:
            order_by.extend(pk.asc() for pk in pk_columns)

        return order_by

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for order-based filtering.

        Note:
            This implementation requires the model to have primary key(s).
            The primary keys are used to ensure consistent and correct filtering
            when multiple records have the same value in the target field.

        Args:
            orm_model (type[DeclarativeBase]): SQLAlchemy model class to create filter for

        Returns:
            callable: FastAPI dependency function that returns SQLAlchemy filter condition

        Raises:
            InvalidFieldError: If the specified field or partition_by fields don't exist on the model or the model doesn't have primary key(s)
        """
        # Validate field existence
        self._validate_field_exists(orm_model, self.field)

        # Validate partition_by fields existence
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
            )
        ) -> Optional[ColumnElement]:
            """Generate a filter condition for maximum/minimum values.

            Args:
                enabled (bool): Whether to apply the filter

            Returns:
                Optional[ColumnElement]: SQLAlchemy filter condition or None if filtering is disabled
            """
            if not enabled:
                return None

            # Create window function for ranking with PK-based ordering
            order_by = self._get_order_by_criteria(model_field, orm_model)
            row_number = (
                func.row_number()
                .over(partition_by=partition_fields, order_by=order_by)
                .label("row_number")
            )

            # Create subquery with row numbers
            subq = select(orm_model, row_number).subquery()

            # Filter using primary keys with IN clause
            pk_attrs = [
                getattr(orm_model, pk.name) for pk in self.get_primary_keys(orm_model)
            ]
            subq_pk_attrs = [
                getattr(subq.c, pk.name) for pk in self.get_primary_keys(orm_model)
            ]

            return tuple_(*pk_attrs).in_(
                select(*subq_pk_attrs).where(subq.c.row_number == 1)
            )

        return filter_dependency
