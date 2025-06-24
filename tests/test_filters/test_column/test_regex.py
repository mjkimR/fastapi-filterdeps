from fastapi_filterdeps.filters.column.regex import (
    RegexCriteria,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestRegexCriteria(BaseFilterTest):
    def test_filter_regex_case_sensitive(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name_pattern = RegexCriteria(
                field="name",
                alias="name_pattern",
                case_sensitive=True,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"name_pattern": "^Item"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["name"].startswith("Item") for item in response.json())

    def test_filter_regex_case_insensitive(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name_pattern = RegexCriteria(
                field="name",
                alias="name_pattern",
                case_sensitive=False,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"name_pattern": "^item"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["name"].lower().startswith("item") for item in response.json())

    def test_filter_regex_none(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name_pattern = RegexCriteria(
                field="name",
                alias="name_pattern",
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) > 0
