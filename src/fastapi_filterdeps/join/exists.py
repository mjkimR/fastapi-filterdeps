from typing import Optional, Callable

from fastapi import Depends
from sqlalchemy import select, tuple_
from fastapi_filterdeps.base import (
    SqlFilterCriteriaBase,
    create_combined_filter_dependency,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement


class JoinExistsCriteria(SqlFilterCriteriaBase):
    """A filter criteria that checks for the existence of related records using JOIN operations.

    This criteria allows filtering records based on the existence of related records
    that match certain conditions. It supports both inner and left outer joins, and can be
    used to either include or exclude records based on the join results.

    When any of the join criteria returns None (meaning no filtering should be applied),
    this filter will also return None to indicate no filtering should occur.

    Args:
        join_criteria (List[SqlFilterCriteriaBase]): List of filter criteria to apply on the joined table
        join_condition (ColumnElement): SQLAlchemy join condition (e.g., Model.field == OtherModel.field)
        join_model (type[DeclarativeBase]): The SQLAlchemy model to join with
        exclude (bool, optional): If True, excludes matching records instead of including them. Defaults to False.
        is_outer (bool, optional): If True, performs a LEFT OUTER JOIN instead of an INNER JOIN.
                                 This is equivalent to SQLAlchemy's is_outer parameter which creates
                                 a LEFT OUTER JOIN. Defaults to False.
        description (Optional[str], optional): Description of the filter criteria. Defaults to None.

    Example:
        ```python
        # Filter posts that have comments matching certain criteria
        criteria = JoinExistsCriteria(
            join_criteria=[CommentFilterCriteria(...)],
            join_condition=Post.id == Comment.post_id,
            join_model=Comment,
            is_outer=True  # Will perform a LEFT OUTER JOIN
        )
        ```
    """

    def __init__(
        self,
        join_criteria: list[SqlFilterCriteriaBase],
        join_condition: ColumnElement,
        join_model: type[DeclarativeBase],
        exclude: bool = False,
        is_outer: bool = False,
        description: Optional[str] = None,
    ):
        """Initialize the join exists criteria.

        Args:
            join_criteria: List of filter criteria to apply to the joined table
            join_condition: SQLAlchemy expression defining the join condition
            join_model: The SQLAlchemy model class to join with
            exclude: If True, excludes matching records instead of including them
            is_outer: If True, performs a LEFT OUTER JOIN instead of an INNER JOIN
            description: Optional description of the filter for API documentation
        """
        self.join_criteria = join_criteria
        self.join_condition = join_condition
        self.join_model = join_model
        self.exclude = exclude
        self.is_outer = is_outer
        self.description = description

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Build a FastAPI dependency for filtering based on joined table conditions.

        This method creates a dependency that will:
        1. Apply the join_criteria to filter the joined table
        2. Use EXISTS or NOT EXISTS subquery to filter the main table
        3. Return None if no join_criteria are active, making the filter truly optional

        Args:
            orm_model: The main SQLAlchemy model class to create filter for

        Returns:
            A FastAPI dependency function that returns an SQLAlchemy filter condition
            or None if no filtering should be applied

        Raises:
            InvalidFieldError: If the model does not have primary keys
        """
        self._validate_model_has_primary_keys(orm_model=orm_model)
        primary_keys = self.get_primary_keys(orm_model)

        def filter_dependency(
            join_criteria=Depends(
                create_combined_filter_dependency(
                    *self.join_criteria, orm_model=self.join_model
                )
            )
        ) -> Optional[ColumnElement]:
            """Generate a filter condition based on joined table criteria.

            Args:
                join_criteria: Filter conditions from the join_criteria dependencies.
                             Will be None if no criteria are active.

            Returns:
                SQLAlchemy filter condition or None if no filtering should be applied.
                Returns None when join_criteria is None or empty, making this filter
                truly optional - it won't affect the query at all in this case.
            """
            if not join_criteria:
                return None

            subquery = (
                select(*primary_keys)
                .select_from(orm_model)
                .join(self.join_model, self.join_condition, isouter=self.is_outer)
                .where(*join_criteria)
            )

            if self.exclude:
                return tuple_(*primary_keys).notin_(subquery)
            else:
                return tuple_(*primary_keys).in_(subquery)

        return filter_dependency
