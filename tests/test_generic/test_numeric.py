from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.numeric import (
    NumericRangeCriteria,
    NumericExactCriteria,
)
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


class TestNumericRangeCriteria(BaseFilterTest):
    def test_filter_range_inclusive(self):
        filter_deps = create_combined_filter_dependency(
            NumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=True,
                include_max_bound=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"min_count": 10, "max_count": 20}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(10 <= item["count"] <= 20 for item in response.json())

    def test_filter_range_exclusive(self):
        filter_deps = create_combined_filter_dependency(
            NumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=False,
                include_max_bound=False,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"min_count": 10, "max_count": 20}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(10 < item["count"] < 20 for item in response.json())

    def test_filter_range_min_only(self):
        filter_deps = create_combined_filter_dependency(
            NumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=True,
                include_max_bound=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"min_count": 10})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["count"] >= 10 for item in response.json())

    def test_filter_range_exclude(self):
        filter_deps = create_combined_filter_dependency(
            NumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                exclude=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"min_count": 10, "max_count": 20}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["count"] < 10 or item["count"] > 20 for item in response.json())

    def test_filter_range_mixed_bounds(self):
        filter_deps = create_combined_filter_dependency(
            NumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=True,
                include_max_bound=False,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"min_count": 10, "max_count": 20}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(10 <= item["count"] < 20 for item in response.json())


class TestNumericExactCriteria(BaseFilterTest):
    def test_filter_exact_match(self):
        filter_deps = create_combined_filter_dependency(
            NumericExactCriteria(
                field="count",
                alias="count",
                numeric_type=int,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"count": 10})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["count"] == 10 for item in response.json())

    def test_filter_exact_exclude(self):
        filter_deps = create_combined_filter_dependency(
            NumericExactCriteria(
                field="count",
                alias="count",
                exclude=True,
                numeric_type=int,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"count": 10})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["count"] != 10 for item in response.json())

    def test_filter_exact_none(self):
        filter_deps = create_combined_filter_dependency(
            NumericExactCriteria(
                field="count",
                alias="count",
                numeric_type=int,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) > 0
