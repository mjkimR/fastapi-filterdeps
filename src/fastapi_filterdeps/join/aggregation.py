from typing import Optional, Callable
from sqlalchemy import select, and_, tuple_
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement, BinaryExpression
from fastapi import Depends
from fastapi_filterdeps.base import (
    SqlFilterCriteriaBase,
    create_combined_filter_dependency,
)


class JoinAggregateCriteria(SqlFilterCriteriaBase):
    """A filter criteria that uses aggregate functions on joined tables for filtering.

    This criteria allows filtering records based on aggregate functions (COUNT, SUM, AVG, etc.)
    applied to related records. It supports various aggregate functions and custom having conditions.

    Args:
        join_condition (ColumnElement): SQLAlchemy join condition
        join_model (type[DeclarativeBase]): The SQLAlchemy model to join with
        having_expression (BinaryExpression): SQLAlchemy expression for HAVING clause
        additional_criteria (list[SqlFilterCriteriaBase], optional): Additional filters for joined table
        is_outer (bool, optional): If True, performs LEFT OUTER JOIN. Defaults to False.
        description (Optional[str], optional): Description of the filter. Defaults to None.

    Example:
        ```python
        # Filter posts that have more than 5 comments
        criteria = JoinAggregateCriteria(
            join_condition=Post.id == Comment.post_id,
            join_model=Comment,
            having_expression=func.count(functions.star()) > 5
        )

        # Filter products with average rating above 4.5
        criteria = JoinAggregateCriteria(
            join_condition=Product.id == Review.product_id,
            join_model=Review,
            having_expression=func.avg(Review.rating) >= 4.5
        )
        ```
    """

    def __init__(
        self,
        join_condition: ColumnElement,
        join_model: type[DeclarativeBase],
        having_expression: BinaryExpression,
        additional_criteria: Optional[list[SqlFilterCriteriaBase]] = None,
        is_outer: bool = False,
        description: Optional[str] = None,
    ):
        self.join_condition = join_condition
        self.join_model = join_model
        self.having_expression = having_expression
        self.additional_criteria = additional_criteria or []
        self.is_outer = is_outer
        self.description = description

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Build a FastAPI dependency for filtering based on aggregate conditions.

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
            # Build subquery with aggregation
            subquery = (
                select(*primary_keys)
                .select_from(orm_model)
                .join(self.join_model, self.join_condition, isouter=self.is_outer)
                .group_by(*primary_keys)
                .having(self.having_expression)
            )

            # Add additional filters if any
            if additional_filters:
                subquery = subquery.where(and_(*additional_filters))

            return tuple_(*primary_keys).in_(subquery)

        return filter_dependency
