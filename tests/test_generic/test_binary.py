from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.simple.binary import (
    BinaryCriteria,
    BinaryFilterType,
)
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


class TestBinaryCriteria(BaseFilterTest):
    def test_filter_is_true(self):
        filter_deps = create_combined_filter_dependency(
            BinaryCriteria(
                field="is_active",
                alias="is_active",
                filter_type=BinaryFilterType.IS_TRUE,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"is_active": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is True for item in response.json())

        response = self.client.get("/test-items", params={"is_active": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is False for item in response.json())

    def test_filter_is_false(self):
        filter_deps = create_combined_filter_dependency(
            BinaryCriteria(
                field="is_active",
                alias="is_active",
                filter_type=BinaryFilterType.IS_FALSE,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"is_active": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is False for item in response.json())

        response = self.client.get("/test-items", params={"is_active": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is True for item in response.json())

    def test_filter_is_none(self):
        filter_deps = create_combined_filter_dependency(
            BinaryCriteria(
                field="is_active", alias="is_null", filter_type=BinaryFilterType.IS_NONE
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"is_null": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is None for item in response.json())

        response = self.client.get("/test-items", params={"is_null": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is not None for item in response.json())

    def test_filter_is_not_none(self):
        filter_deps = create_combined_filter_dependency(
            BinaryCriteria(
                field="is_active",
                alias="is_not_null",
                filter_type=BinaryFilterType.IS_NOT_NONE,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"is_not_null": "true"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is not None for item in response.json())

        response = self.client.get("/test-items", params={"is_not_null": "false"})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["is_active"] is None for item in response.json())
