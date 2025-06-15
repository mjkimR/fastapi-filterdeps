from enum import Enum
from typing import Optional

from fastapi import Depends
from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import (
    SqlFilterCriteriaBase,
    create_combined_filter_dependency,
)


class CombineOperator(str, Enum):
    """Logical operators for combining filter criteria."""

    AND = "and"
    OR = "or"


class CombineCriteria(SqlFilterCriteriaBase):
    """Combines multiple criteria with a logical AND or OR operator.

    This class is essential for creating complex queries by combining multiple
    filter criteria. While `create_combined_filter_dependency` defaults to an
    AND combination, this class allows for explicit `OR` conditions or the
    nesting of `AND` and `OR` groups.

    It is most commonly used via the `&` (AND) and `|` (OR) operators for a more
    intuitive and readable syntax.

    Note:
        When criteria are combined, the descriptions for the individual query
        parameters in the OpenAPI documentation are not automatically updated to
        reflect the combined logic. It is recommended to add a clear description
        to the FastAPI path operation's docstring to explain how the filter
        parameters are intended to work together for API consumers.

    Attributes:
        operator (CombineOperator): The logical operator to apply (`AND` or `OR`).
        criteria_list (List[SqlFilterCriteriaBase]): The filter criteria instances
            to be combined.

    Examples:
        # Define an OR filter for a 'Post' model. This is a key use case, as
        # create_combined_filter_dependency defaults to AND.
        # This example finds posts that are new OR are very popular.

        from fastapi_filterdeps.generic.string import StringCriteria, StringMatchType
        from fastapi_filterdeps.generic.numeric import NumericCriteria, NumericFilterType

        # Use the `|` operator to create a logical OR.
        post_filters = create_combined_filter_dependency(
            StringCriteria(
                field="title",
                alias="title_is_new",
                match_type=StringMatchType.PREFIX,
                description="Filter for titles starting with '[NEW]'"
            ) | NumericCriteria(
                field="view_count",
                alias="is_popular",
                numeric_type=int,
                operator=NumericFilterType.GT,
                description="Filter for posts with more than 10000 views"
            ),
            orm_model=Post,
        )

        # In your endpoint:
        @app.get("/posts/featured")
        def list_featured_posts(filters=Depends(post_filters)):
            \"\"\"
            Lists featured posts.

            A post is featured if it meets **either** of the following criteria:
            - **title_is_new**: The title starts with `[NEW]`.
            - **is_popular**: The view count is over 10000.
            \"\"\"
            # `filters` will contain a single SQLAlchemy `OR` clause.
            query = select(Post).where(*filters)
            ...
    """

    def __init__(self, operator: CombineOperator, *criteria: SqlFilterCriteriaBase):
        """Initializes the CombineCriteria.

        Args:
            operator (CombineOperator): The logical operator (`AND` or `OR`) to
                use for combining the criteria.
            *criteria (SqlFilterCriteriaBase): A sequence of two or more filter
                criteria instances to combine.
        """
        if len(criteria) < 2:
            raise ValueError("CombineCriteria requires at least two criteria.")
        self.operator = operator
        self.criteria_list = list(criteria)

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Builds a FastAPI dependency that combines nested filters.

        This method constructs a dependency that, when resolved, will apply the
        specified logical operator (`AND` or `OR`) to the results of all
        the nested filter criteria.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class that the
                filters will be applied to.

        Returns:
            Callable: A FastAPI dependency that returns a single combined
                SQLAlchemy filter expression (`ColumnElement`) or `None` if no
                nested filters are active.
        """
        combined_dependency = create_combined_filter_dependency(
            *self.criteria_list, orm_model=orm_model
        )

        def filter_dependency(
            filters: list[ColumnElement] = Depends(combined_dependency),
        ) -> Optional[ColumnElement]:
            """Applies the logical operator to the collected filter conditions."""
            if not filters:
                return None

            if self.operator == CombineOperator.AND:
                return and_(*filters)
            elif self.operator == CombineOperator.OR:
                return or_(*filters)
            return None

        return filter_dependency

    def __and__(self, other: "SqlFilterCriteriaBase") -> "CombineCriteria":
        """Creates a logical AND condition with another filter criterion.

        Allows chaining filters with the `&` operator.
        Usage: `StringCriteria(...) & NumericCriteria(...)`
        """
        if self.operator == CombineOperator.AND:
            self.criteria_list.append(other)
            return self
        return CombineCriteria(CombineOperator.AND, self, other)

    def __or__(self, other: "SqlFilterCriteriaBase") -> "CombineCriteria":
        """Creates a logical OR condition with another filter criterion.

        Allows chaining filters with the `|` operator.
        Usage: `StringCriteria(...) | NumericCriteria(...)`
        """
        if self.operator == CombineOperator.OR:
            self.criteria_list.append(other)
            return self
        return CombineCriteria(CombineOperator.OR, self, other)
