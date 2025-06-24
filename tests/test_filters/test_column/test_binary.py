from fastapi_filterdeps.filters.column.binary import (
    BinaryCriteria,
    BinaryFilterType,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestBinaryCriteria(BaseFilterTest):
    def test_filter_is_true(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            is_active = BinaryCriteria(
                field="is_active",
                alias="is_active",
                filter_type=BinaryFilterType.IS_TRUE,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"is_active": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is True for item in response.json())

        response = self.client.get("/test-items", params={"is_active": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is False for item in response.json())

    def test_filter_is_false(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            is_active = BinaryCriteria(
                field="is_active",
                alias="is_active",
                filter_type=BinaryFilterType.IS_FALSE,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"is_active": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is False for item in response.json())

        response = self.client.get("/test-items", params={"is_active": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is True for item in response.json())

    def test_filter_is_none(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            is_active = BinaryCriteria(
                field="is_active",
                alias="is_null",
                filter_type=BinaryFilterType.IS_NONE,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"is_null": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is None for item in response.json())

        response = self.client.get("/test-items", params={"is_null": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is not None for item in response.json())

    def test_filter_is_not_none(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            is_active = BinaryCriteria(
                field="is_active",
                alias="is_not_null",
                filter_type=BinaryFilterType.IS_NOT_NONE,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"is_not_null": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is not None for item in response.json())

        response = self.client.get("/test-items", params={"is_not_null": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is None for item in response.json())
