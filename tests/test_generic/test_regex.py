from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.regex import (
    RegexCriteria,
)
from tests.conftest import BaseFilterTest, TestModel


class TestRegexCriteria(BaseFilterTest):
    def test_filter_regex_case_sensitive(self):
        filter_deps = create_combined_filter_dependency(
            RegexCriteria(
                field="name",
                alias="name_pattern",
                case_sensitive=True,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"name_pattern": "^Item"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["name"].startswith("Item") for item in response.json())

    def test_filter_regex_case_insensitive(self):
        filter_deps = create_combined_filter_dependency(
            RegexCriteria(
                field="name",
                alias="name_pattern",
                case_sensitive=False,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"name_pattern": "^item"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["name"].lower().startswith("item") for item in response.json())

    def test_filter_regex_none(self):
        filter_deps = create_combined_filter_dependency(
            RegexCriteria(
                field="name",
                alias="name_pattern",
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) > 0
