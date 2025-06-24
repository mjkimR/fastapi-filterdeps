from typing import Any, Callable, List, Optional, Type

from fastapi import Query
from sqlalchemy import ColumnElement, tuple_
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select

from fastapi_filterdeps.core.base import SqlFilterCriteriaBase


class GroupByHavingCriteria(SqlFilterCriteriaBase):
    """A filter based on an aggregate condition using a GROUP BY/HAVING clause.

    This advanced filter creates a subquery that groups records, applies an
    aggregate function (e.g., AVG, COUNT, SUM), and filters those groups using a
    HAVING clause. The main query is then filtered to include only records
    that belong to the groups satisfying the HAVING condition.

    It works by generating a SQL condition like:
    `(grouping_columns) IN (SELECT grouping_columns FROM ... GROUP BY ... HAVING ...)`

    This is useful for filtering based on calculated metrics, such as finding
    all posts with an average rating above a certain value, or users with more
    than a specified number of comments.

    Attributes:
        value_type (Type): The expected data type of the query parameter's
            value (e.g., `int`, `float`).
        group_by_cols (List[ColumnElement]): A list of SQLAlchemy model columns
            to use in the `GROUP BY` clause of the subquery. These columns
            typically correlate the subquery with the main query's model.
        having_builder (Callable[[Any], ColumnElement]): A callable (like a
            lambda function) that accepts the query parameter's value and
            returns the SQLAlchemy `HAVING` clause expression.
        alias (Optional[str]): The alias for the query parameter in the API
            endpoint (e.g., "avg_vote_score").
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from sqlalchemy import func
            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.relation.having import GroupByHavingCriteria
            from myapp.models import Post, Vote

            class PostFilterSet(FilterSet):
                avg_vote_score = GroupByHavingCriteria(
                    alias="avg_vote_score",
                    value_type=float,
                    group_by_cols=[Post.id],
                    having_builder=lambda value: func.avg(Vote.score) >= value
                )
                class Meta:
                    orm_model = Post

            # GET /posts?avg_vote_score=4.0
            # will return all posts that have an average vote score of 4.0 or higher.
    """

    def __init__(
        self,
        value_type: Type,
        group_by_cols: List[ColumnElement],
        having_builder: Callable[[Any], ColumnElement],
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the GroupByHaving filter criteria.

        Args:
            alias (str): The alias for the query parameter in the API.
            value_type (Type): The data type of the API input value.
            group_by_cols (List[ColumnElement]): Columns for the GROUP BY clause.
            having_builder (Callable[[Any], ColumnElement]): A function that
                builds the HAVING clause from the input value.
            description (Optional[str]): Custom description for the OpenAPI docs.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        self.alias = alias
        self.value_type = value_type
        self.group_by_cols = group_by_cols
        self.having_builder = having_builder
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter.

        Returns:
            str: The default description for the OpenAPI documentation.
        """
        group_by_str = ", ".join([str(c.name) for c in self.group_by_cols])
        return f"Filter records based on an aggregate condition over grouped data. Grouped by: {group_by_str}."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for aggregate filtering.

        This method creates a callable FastAPI dependency that constructs a
        subquery with a GROUP BY and HAVING clause to filter the main query.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to which
                the filter will be applied. This parameter is part of the base
                interface but is not directly used in this implementation, as
                grouping columns are provided explicitly.

        Returns:
            Callable: A FastAPI dependency that, when resolved, returns a
                SQLAlchemy filter condition (`ColumnElement`) or `None`.
        """

        def filter_dependency(
            value: Optional[self.value_type] = Query(  # type: ignore
                default=None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates the aggregate filter condition.

            Args:
                value (Optional[Any]): The value provided in the query parameter.
                    If None, no filter is applied.

            Returns:
                Optional[ColumnElement]: A SQLAlchemy filter expression that uses
                    a subquery, or `None` if no value was provided.
            """
            if value is None:
                return None

            having_expression = self.having_builder(value)

            subquery = (
                select(*self.group_by_cols)
                .group_by(*self.group_by_cols)
                .having(having_expression)
            )

            return tuple_(*self.group_by_cols).in_(subquery)

        return filter_dependency
