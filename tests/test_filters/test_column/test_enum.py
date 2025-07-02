from enum import Enum

import pytest
from fastapi_filterdeps.filters.column.enum import (
    EnumCriteria,
    MultiEnumCriteria,
)
from fastapi_filterdeps import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class StatusType(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class TestEnumCriteria(BaseFilterTest):
    @pytest.mark.parametrize(
        "status_value",
        [
            StatusType.ACTIVE,
            StatusType.INACTIVE,
            StatusType.PENDING,
        ],
    )
    def test_filter_enum(self, status_value):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            status = EnumCriteria(
                field="status",
                alias="status",
                enum_class=StatusType,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"status": status_value.value})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["status"] == status_value.value for item in response.json())

    def test_filter_enum_none(self, datasets):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            status = EnumCriteria(
                field="status",
                alias="status",
                enum_class=StatusType,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) == len(datasets["items"])

    def test_filter_enum_invalid(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            status = EnumCriteria(
                field="status",
                alias="status",
                enum_class=StatusType,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"status": "invalid"})
        assert response.status_code == 422


class TestMultiEnumCriteria(BaseFilterTest):
    def test_filter_enum_multiple(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            status = MultiEnumCriteria(
                field="status",
                alias="status",
                enum_class=StatusType,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get(
            "/test-items", params={"status": ["active", "inactive"]}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["status"] in ["active", "inactive"] for item in response.json())
        assert {item["status"] for item in response.json()} == {"active", "inactive"}

    def test_filter_enum_empty_list(self, datasets):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            status = MultiEnumCriteria(
                field="status",
                alias="status",
                enum_class=StatusType,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"status": []})
        assert response.status_code == 200
        assert len(response.json()) == len(datasets["items"])
