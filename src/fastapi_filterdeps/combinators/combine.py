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
    """
    A filter that combines two or more filter criteria using a logical operator (AND, OR).
    It works by combining the dependencies of the nested criteria.
    """

    def __init__(self, operator: CombineOperator, *criteria: SqlFilterCriteriaBase):
        if len(criteria) < 2:
            raise ValueError("CombineCriteria requires at least two criteria.")
        self.operator = operator
        self.criteria_list = list(criteria)

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """
        Builds a combined filter dependency.
        The resulting dependency will depend on all sub-criteria dependencies.
        """
        combined_dependency = create_combined_filter_dependency(
            *self.criteria_list, orm_model=orm_model
        )

        def filter_dependency(
            filters: list[ColumnElement] = Depends(combined_dependency),
        ) -> Optional[ColumnElement]:
            """
            Applies the logical operator to the collected filter conditions.
            """
            if not filters:
                return None

            if self.operator == CombineOperator.AND:
                return and_(*filters)
            elif self.operator == CombineOperator.OR:
                return or_(*filters)
            return None

        return filter_dependency

    def __and__(self, other: "SqlFilterCriteriaBase"):
        if self.operator == CombineOperator.AND:
            self.criteria_list.append(other)
            return self
        return CombineCriteria(CombineOperator.AND, self, other)

    def __or__(self, other: "SqlFilterCriteriaBase"):
        if self.operator == CombineOperator.OR:
            self.criteria_list.append(other)
            return self
        return CombineCriteria(CombineOperator.OR, self, other)
