from fastapi_filterdeps.core.decorators import filter_for
from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase
import pytest


def test_filter_for_decorator():
    @filter_for(field="foo", alias="foo_alias", description="desc", bound_type=str)
    def my_filter(model, value):
        return value == "bar"

    # Should return a SimpleFilterCriteriaBase subclass instance
    assert isinstance(my_filter, SimpleFilterCriteriaBase)
    assert my_filter.field == "foo"
    assert my_filter.alias == "foo_alias"
    assert my_filter.description == "desc"
    assert my_filter.bound_type == str
    # The filter logic should call the decorated function
    assert my_filter._filter_logic(None, "bar") is True
    assert my_filter._filter_logic(None, "baz") is False
