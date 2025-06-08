from typing import Optional, Callable

from fastapi import Depends
from sqlalchemy import select, and_, or_, not_, exists as sql_exists
from fastapi_filterdeps.base import (
    SqlFilterCriteriaBase,
    create_combined_filter_dependency,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement


class JoinNestedFilterCriteria(SqlFilterCriteriaBase):
    """A filter criteria that checks for the existence (or non-existence) of related records
    that match nested criteria, using correlated subqueries with SQL `EXISTS`.

    When any of the join criteria returns None (meaning no filtering should be applied),
    this filter will also return None to indicate no filtering should occur.

    Args:
        filter_criteria (List[SqlFilterCriteriaBase]): List of filter criteria to apply on the joined table
        join_condition (ColumnElement): SQLAlchemy expression defining the relationship between
                                        the main model and `join_model` (e.g., `ParentModel.id == ChildModel.parent_id`).
                                        This condition is used to correlate the subquery.
        join_model (type[DeclarativeBase]): The SQLAlchemy model to join with
        exclude (bool, optional): If True, excludes matching records instead of including them.
        include_unrelated (bool, optional): If True, the filter will include records that do not have any related records.
        description (Optional[str], optional): Description of the filter criteria. Defaults to None.

    Example:
        ```python
        # Filter posts that have approved comments.
        # If exclude=False, is_outer=True, and "is_approved" filter is active:
        #   - Includes posts with approved comments
        #   - Includes posts with no comments at all
        criteria = JoinNestedFilterCriteria(
            filter_criteria=[CommentFilterCriteria(...)],
            join_condition=Post.id == Comment.post_id,
            join_model=Comment,
            include_unrelated=True
        )
        ```
    """

    def __init__(
        self,
        filter_criteria: list[SqlFilterCriteriaBase],
        join_condition: ColumnElement,
        join_model: type[DeclarativeBase],
        exclude: bool = False,
        include_unrelated: bool = False,
        description: Optional[str] = None,
    ):
        """Initialize the join exists criteria.

        Args:
            join_criteria: List of filter criteria to apply to the joined table
            join_condition: SQLAlchemy expression defining the join condition
            join_model: The SQLAlchemy model class to join with.
            exclude: If True, inverts the existence check (e.g., `NOT EXISTS` or complex logic with `is_outer`).
                     Defaults to False.
            include_unrelated: If True, the filter will include records that do not have any related records.
            description: Optional description of the filter for API documentation.
        """
        self.filter_criteria = filter_criteria
        self.join_condition = join_condition
        self.join_model = join_model
        self.exclude = exclude
        self.include_unrelated = include_unrelated
        self.description = description

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Build a FastAPI dependency for filtering based on joined table conditions.

        Args:
            orm_model: The main SQLAlchemy model class to create filter for

        Returns:
            A FastAPI dependency function that returns an SQLAlchemy filter condition
            or None if no filtering should be applied
        """

        def filter_dependency(
            filter_criteria=Depends(
                create_combined_filter_dependency(
                    *self.filter_criteria, orm_model=self.join_model
                )
            )
        ) -> Optional[ColumnElement]:
            """Generate a filter condition based on joined table criteria.

            Args:
                filter_criteria: Filter conditions from the filter_criteria dependencies.
                             Will be None if no criteria are active.

            Returns:
                SQLAlchemy filter condition or None if no filtering should be applied.
                Returns None when filter_criteria is None or empty, making this filter
                truly optional - it won't affect the query at all in this case.
            """
            if not filter_criteria:
                return None

            stmt_related_satisfies_filters = (
                select(self.join_model.id)
                .where(self.join_condition)
                .where(*filter_criteria)
            )
            cond_related_satisfies_filters = sql_exists(stmt_related_satisfies_filters)

            if not self.include_unrelated:
                if self.exclude:
                    return not_(cond_related_satisfies_filters)
                else:
                    return cond_related_satisfies_filters
            else:
                stmt_any_related = select(self.join_model.id).where(self.join_condition)
                cond_any_related = sql_exists(stmt_any_related)

                if not self.exclude:
                    return or_(cond_related_satisfies_filters, not_(cond_any_related))
                else:
                    return and_(cond_any_related, not_(cond_related_satisfies_filters))

        return filter_dependency
