from enum import Enum
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.enum import (
    EnumCriteria,
    MultiEnumCriteria,
)
from tests.conftest import BaseFilterTest, TestModel


class TestStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class TestEnumCriteria(BaseFilterTest):
    def test_filter_enum_single(self):
        filter_deps = create_combined_filter_dependency(
            EnumCriteria(
                field="status",
                alias="status",
                enum_class=TestStatus,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"status": "active"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["status"] == TestStatus.ACTIVE for item in response.json())

    def test_filter_enum_none(self):
        filter_deps = create_combined_filter_dependency(
            EnumCriteria(
                field="status",
                alias="status",
                enum_class=TestStatus,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) > 0


class TestMultiEnumCriteria(BaseFilterTest):
    def test_filter_enum_multiple(self):
        filter_deps = create_combined_filter_dependency(
            MultiEnumCriteria(
                field="status",
                alias="status",
                enum_class=TestStatus,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"status": ["active", "inactive"]}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["status"] in ["active", "inactive"] for item in response.json())

    def test_filter_enum_empty_list(self):
        filter_deps = create_combined_filter_dependency(
            MultiEnumCriteria(
                field="status",
                alias="status",
                enum_class=TestStatus,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"status": []})
        assert response.status_code == 200
        assert len(response.json()) > 0
