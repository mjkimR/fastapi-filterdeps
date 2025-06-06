from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.criteria_string import (
    GenericStringCriteria,
    GenericStringSetCriteria,
    StringMatchType,
)
from tests.conftest import BaseFilterTest, TestModel


class TestGenericStringCriteria(BaseFilterTest):
    def test_filter_string_exact(self):
        filter_deps = create_combined_filter_dependency(
            GenericStringCriteria(
                field="name", alias="name", match_type=StringMatchType.EXACT
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"name": "Item 1"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["name"] == "Item 1" for item in response.json())

    def test_filter_string_contains(self):
        filter_deps = create_combined_filter_dependency(
            GenericStringCriteria(
                field="name",
                alias="name",
                match_type=StringMatchType.CONTAINS,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"name": "item"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all("item" in item["name"].lower() for item in response.json())


class TestGenericStringSetCriteria(BaseFilterTest):
    def test_filter_string_set_exact(self):
        filter_deps = create_combined_filter_dependency(
            GenericStringSetCriteria(field="name", alias="name"),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"category": ["A", "B"]})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["category"] in ["A", "B"] for item in response.json())
