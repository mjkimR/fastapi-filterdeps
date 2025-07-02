from fastapi_filterdeps import FilterSet
from fastapi_filterdeps.filters.column.regex import RegexCriteria
from fastapi_filterdeps.filters.column.string import (
    StringCriteria,
    StringMatchType,
    StringSetCriteria,
)
from fastapi_filterdeps.filters.column.time import TimeCriteria, TimeMatchType


class CreatedAtFilterSet(FilterSet):
    abstract = True

    # Time range: created_at
    created_at_start = TimeCriteria(
        field="created_at",
        match_type=TimeMatchType.GTE,
    )
    created_at_end = TimeCriteria(
        field="created_at",
        match_type=TimeMatchType.LTE,
    )


class TitleFilterSet(FilterSet):
    abstract = True

    # String: title contains
    title = StringCriteria(
        field="title",
        match_type=StringMatchType.CONTAINS,
    )
    # String set: title in set
    titles = StringSetCriteria(
        field="title",
    )
    # Regex: title pattern
    title_pattern = RegexCriteria(
        field="title",
        case_sensitive=False,
    )
