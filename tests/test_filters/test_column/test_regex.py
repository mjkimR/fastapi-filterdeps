from fastapi_filterdeps.filters.column.regex import (
    RegexCriteria,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post
import pytest


class TestRegexCriteria(BaseFilterTest):
    @pytest.mark.parametrize(
        "case_sensitive,param,assert_func",
        [
            (True, "^Item", lambda x: x.startswith("Item")),
            (False, "^item", lambda x: x.lower().startswith("item")),
        ],
    )
    def test_filter_regex(self, case_sensitive, param, assert_func):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name_pattern = RegexCriteria(
                field="name",
                alias="name_pattern",
                case_sensitive=case_sensitive,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"name_pattern": param})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(assert_func(item["name"]) for item in response.json())

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
