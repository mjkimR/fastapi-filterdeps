import pytest
from fastapi_filterdeps import FilterSet
from fastapi_filterdeps.filters.column.string import StringCriteria
from fastapi_filterdeps.core.exceptions import ConfigurationError
from tests.models import Post


class AbstractFilterSet(FilterSet):
    abstract = True
    foo = StringCriteria(field="id")


class ConcreteFilterSet(FilterSet):
    foo = StringCriteria(field="id")

    class Meta:
        orm_model = Post


def test_abstract_filterset():
    with pytest.raises(ConfigurationError):
        AbstractFilterSet()


def test_concrete_filterset():
    # Should not raise
    ConcreteFilterSet()


def test_missing_meta_raises():

    with pytest.raises(ConfigurationError):

        class BadFilterSet(FilterSet):
            foo = StringCriteria(field="id")
