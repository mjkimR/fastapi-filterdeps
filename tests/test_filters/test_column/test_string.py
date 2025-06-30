from fastapi_filterdeps.filters.column.string import (
    StringCriteria,
    StringSetCriteria,
    StringMatchType,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post
import pytest


class TestStringCriteria(BaseFilterTest):
    @pytest.mark.parametrize(
        "match_type,param,assert_func",
        [
            (StringMatchType.EXACT, "Item 1", lambda x: x == "Item 1"),
            (StringMatchType.CONTAINS, "item", lambda x: "item" in x.lower()),
            (StringMatchType.PREFIX, "Item", lambda x: x.startswith("Item")),
            (StringMatchType.SUFFIX, "1", lambda x: x.endswith("1")),
            (StringMatchType.NOT_EQUAL, "Item 1", lambda x: x != "Item 1"),
            (StringMatchType.NOT_CONTAINS, "AA", lambda x: "AA" not in x.lower()),
        ],
    )
    def test_filter_string(self, match_type, param, assert_func):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name = StringCriteria(field="name", alias="name", match_type=match_type)

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"name": param})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(assert_func(item["name"]) for item in response.json())


class TestStringSetCriteria(BaseFilterTest):
    def test_filter_string_set_exact(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            category = StringSetCriteria(field="category", alias="category")

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"category": ["A", "B"]})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["category"] in ["A", "B"] for item in response.json())
