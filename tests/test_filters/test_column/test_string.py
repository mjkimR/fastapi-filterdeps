from fastapi_filterdeps.filters.column.string import (
    StringCriteria,
    StringSetCriteria,
    StringMatchType,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestStringCriteria(BaseFilterTest):
    def test_filter_string_exact(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name = StringCriteria(
                field="name", alias="name", match_type=StringMatchType.EXACT
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"name": "Item 1"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["name"] == "Item 1" for item in response.json())

    def test_filter_string_contains(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name = StringCriteria(
                field="name",
                alias="name",
                match_type=StringMatchType.CONTAINS,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"name": "item"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all("item" in item["name"].lower() for item in response.json())


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
