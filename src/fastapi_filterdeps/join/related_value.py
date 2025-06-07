from typing import Callable, Optional, Union, List
from sqlalchemy import select, and_, tuple_, text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement, BinaryExpression
from fastapi import Depends
from fastapi_filterdeps.base import (
    SqlFilterCriteriaBase,
    create_combined_filter_dependency,
)


class JoinRelatedValueCriteria(SqlFilterCriteriaBase):
    """A filter criteria that filters records based on values from related records.

    This criteria allows filtering records based on specific values from related records,
    such as the latest/earliest date, maximum/minimum value, or any other ordered value
    from related records.

    Args:
        join_condition (ColumnElement): SQLAlchemy join condition
        join_model (type[DeclarativeBase]): The SQLAlchemy model to join with
        target_column (ColumnElement): Column to check the value from
        value_expression (BinaryExpression): SQLAlchemy expression for filtering the value
        order_by (Union[ColumnElement, List[ColumnElement]]): Columns to order by
        is_outer (bool, optional): If True, performs LEFT OUTER JOIN. Defaults to False.
        additional_criteria (list[SqlFilterCriteriaBase], optional): Additional filters for joined table
        description (Optional[str], optional): Description of the filter. Defaults to None.

    Example:
        ```python
        from datetime import datetime, timedelta
        from sqlalchemy import func

        # Filter users whose last login was within 24 hours
        one_day_ago = datetime.now() - timedelta(days=1)
        criteria = JoinRelatedValueCriteria(
            join_condition=User.id == LoginLog.user_id,
            join_model=LoginLog,
            target_column=LoginLog.created_at,
            order_by=LoginLog.created_at.desc(),
            value_expression=LoginLog.created_at > one_day_ago
        )

        # Filter products whose lowest price is under $10
        criteria = JoinRelatedValueCriteria(
            join_condition=Product.id == PriceHistory.product_id,
            join_model=PriceHistory,
            target_column=PriceHistory.price,
            order_by=PriceHistory.price.asc(),
            value_expression=PriceHistory.price < 10
        )

        # Filter posts with first comment from a specific user
        criteria = JoinRelatedValueCriteria(
            join_condition=Post.id == Comment.post_id,
            join_model=Comment,
            target_column=Comment.user_id,
            order_by=Comment.created_at.asc(),
            value_expression=Comment.user_id == target_user_id
        )
        ```
    """

    def __init__(
        self,
        join_condition: ColumnElement,
        join_model: type[DeclarativeBase],
        target_column: ColumnElement,
        value_expression: BinaryExpression,
        order_by: Union[ColumnElement, List[ColumnElement]],
        is_outer: bool = False,
        additional_criteria: Optional[list[SqlFilterCriteriaBase]] = None,
        description: Optional[str] = None,
    ):
        self.join_condition = join_condition
        self.join_model = join_model
        self.target_column = target_column
        self.value_expression = value_expression
        self.order_by = [order_by] if not isinstance(order_by, list) else order_by
        self.is_outer = is_outer
        self.additional_criteria = additional_criteria or []
        self.description = description

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Build a FastAPI dependency for filtering based on related record values.

        Args:
            orm_model: The main SQLAlchemy model class to create filter for

        Returns:
            A FastAPI dependency function that returns an SQLAlchemy filter condition
            or None if no filtering should be applied
        """
        self._validate_model_has_primary_keys(orm_model=orm_model)
        primary_keys = self.get_primary_keys(orm_model)

        def filter_dependency(
            additional_filters=(
                Depends(
                    create_combined_filter_dependency(
                        *self.additional_criteria, orm_model=self.join_model
                    )
                )
                if self.additional_criteria
                else None
            )
        ) -> Optional[ColumnElement]:
            # Build base query with join and ordering
            subquery = (
                select(*primary_keys)
                .select_from(orm_model)
                .join(self.join_model, self.join_condition, isouter=self.is_outer)
                .where(self.value_expression)
            )

            # Add additional filters if any
            if additional_filters:
                subquery = subquery.where(and_(*additional_filters))

            # Add ordering
            subquery = subquery.order_by(*self.order_by)

            return tuple_(*primary_keys).in_(subquery)

        return filter_dependency
