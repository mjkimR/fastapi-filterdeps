from typing import Optional

from fastapi import Depends
from sqlalchemy import ColumnElement, and_, not_
from sqlalchemy.orm import DeclarativeBase


from fastapi_filterdeps.base import SqlFilterCriteriaBase, combine_filter_conditions


class InvertCriteria(SqlFilterCriteriaBase):
    """A filter that negates the result of a nested criteria."""

    def __init__(self, criteria: SqlFilterCriteriaBase):
        self.criteria = criteria

    def build_filter(self, orm_model: type[DeclarativeBase]):
        nested_filter_func = self.criteria.build_filter(orm_model)

        def filter_dependency(
            nested_filters=Depends(nested_filter_func),
        ) -> Optional[ColumnElement]:
            if nested_filters is None:
                return None

            combined = combine_filter_conditions(nested_filters)
            if not combined:
                return None

            return not_(and_(*combined))

        return filter_dependency
