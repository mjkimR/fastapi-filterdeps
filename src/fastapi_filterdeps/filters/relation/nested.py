from typing import Optional, Callable, List

from fastapi import Depends
from sqlalchemy import select, and_, or_, not_, exists as sql_exists
from fastapi_filterdeps.core.base import SqlFilterCriteriaBase
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.core.combine import create_combined_filter_dependency


class JoinNestedFilterCriteria(SqlFilterCriteriaBase):
    """Filters based on related records that match dynamic, nested criteria.

    This powerful criteria uses a correlated SQL EXISTS subquery to filter
    records based on attributes of their related records. Unlike
    `JoinExistsCriteria`, the conditions applied to the related records are
    not static; they are dynamically generated from other filter criteria
    that you provide.

    This allows you to create API endpoints where users can filter a parent
    resource (e.g., Posts) based on query parameters that apply to a child
    resource (e.g., Comments). For example, finding all posts that have
    comments containing the word "support".

    If none of the nested `filter_criteria` are activated by the user's query,
    this entire filter becomes inactive and will not affect the query.

    Attributes:
        filter_criteria (List[SqlFilterCriteriaBase]): A list of filter criteria
            instances (e.g., `StringCriteria`) to be dynamically applied to
            the `join_model`.
        join_condition (ColumnElement): The SQLAlchemy expression defining the
            relationship between the main model and `join_model` (e.g.,
            `Post.id == Comment.post_id`).
        join_model (type[DeclarativeBase]): The SQLAlchemy model class for the
            related records.
        exclude (bool): If True, the logic is inverted to find records where
            related items *do not* match the nested filters. Defaults to False.
        include_unrelated (bool): Controls how to treat records with no
            relations at all. Defaults to False.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.relation.nested import JoinNestedFilterCriteria
            from fastapi_filterdeps.filters.column.string import StringCriteria
            from fastapi_filterdeps.filters.column.binary import BinaryCriteria, BinaryFilterType
            from myapp.models import Post, Comment

            class PostFilterSet(FilterSet):
                comment_content_filter = StringCriteria(field="content", alias="comment_contains")
                comment_approved_filter = BinaryCriteria(field="is_approved", alias="comment_is_approved")
                comments_nested = JoinNestedFilterCriteria(
                    filter_criteria=[comment_content_filter, comment_approved_filter],
                    join_condition=Post.id == Comment.post_id,
                    join_model=Comment,
                )
                class Meta:
                    orm_model = Post

            # GET /posts?comment_contains=foo&comment_is_approved=true
            # will filter for posts that have comments containing 'foo' and are approved.
    """

    def __init__(
        self,
        filter_criteria: List[SqlFilterCriteriaBase],
        join_condition: ColumnElement,
        join_model: type[DeclarativeBase],
        exclude: bool = False,
        include_unrelated: bool = False,
    ):
        """Initializes the JoinNestedFilterCriteria.

        Args:
            filter_criteria (List[SqlFilterCriteriaBase]): A list of filter criteria
                to be applied to the `join_model`.
            join_condition (ColumnElement): The SQLAlchemy expression defining the
                relationship between the main model and `join_model`.
            join_model (type[DeclarativeBase]): The SQLAlchemy model class to join with.
            exclude (bool): If True, inverts the existence check (effectively
                applying a `NOT EXISTS` condition). Defaults to False.
            include_unrelated (bool): If True, the filter logic also includes
                records that do not have any relations. Defaults to False.
        """
        self.filter_criteria = filter_criteria
        self.join_condition = join_condition
        self.join_model = join_model
        self.exclude = exclude
        self.include_unrelated = include_unrelated

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency that filters based on nested criteria.

        This method constructs a dependency that itself depends on the result of
        the combined nested `filter_criteria`.

        Args:
            orm_model (type[DeclarativeBase]): The main SQLAlchemy model class that
                the filter will be applied to.

        Returns:
            Callable: A FastAPI dependency that, when resolved, produces an
                SQLAlchemy filter expression (`ColumnElement`) or `None`.
        """

        # This dependency combines all the nested filters for the JOINED model.
        nested_filters_dependency = create_combined_filter_dependency(
            *self.filter_criteria, orm_model=self.join_model
        )

        def filter_dependency(
            # FastAPI will first resolve the dependency for the nested filters.
            # `active_nested_filters` will be a list of ColumnElement if any of
            # the corresponding query params were provided, otherwise it will be empty.
            active_nested_filters: List[ColumnElement] = Depends(
                nested_filters_dependency
            ),
        ) -> Optional[ColumnElement]:
            """Generates the final filter condition if nested filters are active."""
            # If no nested filters were activated, this filter is a no-op.
            if not active_nested_filters:
                return None

            stmt_related_satisfies_filters = (
                select(self.join_model.id)
                .where(self.join_condition)
                .where(*active_nested_filters)
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
