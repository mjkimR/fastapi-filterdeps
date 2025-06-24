from enum import Enum
from typing import Optional

from fastapi import Depends
from sqlalchemy import ColumnElement, and_, or_
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.core.base import SqlFilterCriteriaBase
from fastapi_filterdeps.core.combine import create_combined_filter_dependency
from fastapi_filterdeps.core.exceptions import ConfigurationError


class CombineOperator(str, Enum):
    """Logical operators for combining filter criteria."""

    AND = "and"
    OR = "or"


class CombineCriteria(SqlFilterCriteriaBase):
    """Combines multiple criteria with a logical AND or OR operator.

    This class is essential for creating complex queries by combining multiple
    filter criteria. While `FilterSet` defaults to an AND combination, this class
    allows for explicit `OR` conditions or the nesting of `AND` and `OR` groups.

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

    Example:
        Define an OR filter for a 'Post' model. Only the combined filter is exposed as a query parameter::

            .. code-block:: python

                from fastapi_filterdeps.filtersets import FilterSet
                from fastapi_filterdeps.filters.column.string import StringCriteria, StringMatchType
                from fastapi_filterdeps.filters.column.numeric import NumericCriteria, NumericFilterType
                from myapp.models import Post

                class PostFilterSet(FilterSet):
                    combined = (
                        StringCriteria(
                            field="title",
                            alias="title_is_new",
                            match_type=StringMatchType.PREFIX,
                            description="Filter for titles starting with '[NEW]'"
                        )
                        | NumericCriteria(
                            field="views",
                            alias="views_popular",
                            operator=NumericFilterType.GTE,
                            numeric_type=int,
                            description="Filter for posts with views >= 1000"
                        )
                    )
                    class Meta:
                        orm_model = Post

                # In your endpoint:
                # GET /posts?combined=[NEW]
                # will filter for posts that are either new or very popular.
    """

    def __init__(self, operator: CombineOperator, *criteria: SqlFilterCriteriaBase):
        """Initializes the CombineCriteria.

        Args:
            operator (CombineOperator): The logical operator (`AND` or `OR`) to
                use for combining the criteria.
            *criteria (SqlFilterCriteriaBase): A sequence of two or more filter
                criteria instances to combine.

        Raises:
            ConfigurationError: If the criteria list is less than 2.
        """
        if len(criteria) < 2:
            raise ConfigurationError("CombineCriteria requires at least two criteria.")
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

        Example:
            .. code-block:: python

                class MyFilterSet(FilterSet):
                    combined = (
                        StringCriteria(...)
                        & NumericCriteria(...)
                    )
                    class Meta:
                        orm_model = MyModel
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

        Example:
            .. code-block:: python

                class MyFilterSet(FilterSet):
                    combined = (
                        StringCriteria(...)
                        & NumericCriteria(...)
                    )
                    class Meta:
                        orm_model = MyModel
        """
        if self.operator == CombineOperator.AND:
            self.criteria_list.append(other)
            return self
        return CombineCriteria(CombineOperator.AND, self, other)

    def __or__(self, other: "SqlFilterCriteriaBase") -> "CombineCriteria":
        """Creates a logical OR condition with another filter criterion.

        Allows chaining filters with the `|` operator.

        Example:
            .. code-block:: python

                class MyFilterSet(FilterSet):
                    combined = (
                        StringCriteria(...)
                        | NumericCriteria(...)
                    )
                    class Meta:
                        orm_model = MyModel
        """
        if self.operator == CombineOperator.OR:
            self.criteria_list.append(other)
            return self
        return CombineCriteria(CombineOperator.OR, self, other)
