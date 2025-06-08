from typing import Optional, Callable

from fastapi import Query
from sqlalchemy import select, not_, and_, or_, exists as sql_exists
from fastapi_filterdeps.base import SqlFilterCriteriaBase
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement


class JoinExistsCriteria(SqlFilterCriteriaBase):
    """A filter criteria that checks for the existence (or non-existence) of related records.

    This criteria filters records based on whether related records in `join_model` (connected via
    `join_condition`) exist that also satisfy the `filter_condition`. It uses correlated
    subqueries with SQL `EXISTS`.

    Args:
        alias (str): The alias for the query parameter used to activate this filter (e.g., "has_comments").
        filter_condition (list[ColumnElement]): A list of SQLAlchemy expressions to be applied as
                                                filters on the `join_model` within the subquery.
        join_condition (ColumnElement): SQLAlchemy expression defining the relationship between
                                        the main model and `join_model` (e.g., `ParentModel.id == ChildModel.parent_id`).
                                        This condition is used to correlate the subquery.
        join_model (type[DeclarativeBase]): The SQLAlchemy model class for the related records.
        include_unrelated (bool, optional): If True, the filter will include records that do not have any related records.
        description (Optional[str], optional): Custom description for the API documentation.
                                               If `None`, a default description is generated.

    Example:
        ```python
        # Filter posts based on the existence of approved comments.
        criteria = JoinExistsCriteria(
            alias="has_approved_comments",
            filter_condition=[Comment.is_approved == True],
            join_condition=Post.id == Comment.post_id,
            join_model=Comment,
            include_unrelated=True
        )
        ```
    """

    def __init__(
        self,
        alias: str,
        filter_condition: list[ColumnElement],
        join_condition: ColumnElement,
        join_model: type[DeclarativeBase],
        include_unrelated: bool = False,
        description: Optional[str] = None,
    ):
        """Initialize the join exists criteria.

        Args:
            alias: The alias for the query parameter (e.g., "has_approved_comments").
            filter_condition: List of SQLAlchemy filter conditions to apply to the `join_model`.
            join_condition: SQLAlchemy expression defining the relationship between `orm_model`
                            and `join_model`.
            join_model: The SQLAlchemy model class to check for related records.
            include_unrelated: If True, the filter will include records that do not have any related records.
            description: Optional description for API documentation. If None, a default is generated.
        """
        self.alias = alias
        self.filter_condition = filter_condition
        self.join_condition = join_condition
        self.join_model = join_model
        self.include_unrelated = include_unrelated
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        return "Filter by the existence of related records. If False, the filter is inverted."

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
            exists: Optional[bool] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            if exists is None:
                return None

            stmt_related_satisfies_fc = (
                select(self.join_model)
                .where(self.join_condition)
                .where(*self.filter_condition)
            )
            cond_related_satisfies_fc = sql_exists(stmt_related_satisfies_fc)

            if not self.include_unrelated:
                if exists:
                    return cond_related_satisfies_fc
                else:
                    return not_(cond_related_satisfies_fc)
            else:
                stmt_any_related = select(self.join_model).where(self.join_condition)
                cond_any_related = sql_exists(stmt_any_related)

                if exists:
                    return or_(cond_related_satisfies_fc, not_(cond_any_related))
                else:
                    return and_(cond_any_related, not_(cond_related_satisfies_fc))

        return filter_dependency
