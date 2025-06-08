from typing import Any, Callable, Optional
from fastapi import Query
from sqlalchemy.sql.expression import ColumnElement
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import select, tuple_

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class GroupByHavingCriteria(SqlFilterCriteriaBase):
    def __init__(
        self,
        alias: str,
        value_type: type,
        group_by_cols: list[ColumnElement],
        having_builder: Callable[[Any], ColumnElement],
        description: Optional[str] = None,
    ):
        self.alias = alias
        self.value_type = value_type
        self.group_by_cols = group_by_cols
        self.having_builder = having_builder
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        return "Filter instances where the qualify by expression is met"

    def build_filter(self, orm_model: type[DeclarativeBase]):
        def filter_dependency(
            value: Optional[self.value_type] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            if value is None:
                return None

            having_expression = self.having_builder(value)
            return tuple_(*self.group_by_cols).in_(
                select(*self.group_by_cols)
                .group_by(*self.group_by_cols)
                .having(having_expression)
            )

        return filter_dependency
