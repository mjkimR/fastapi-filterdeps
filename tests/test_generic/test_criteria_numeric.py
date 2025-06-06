from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.criteria_numeric import (
    GenericNumericRangeCriteria,
    GenericNumericExactCriteria,
)
from tests.conftest import BaseFilterTest, TestModel


class TestGenericNumericRangeCriteria(BaseFilterTest):
    def build_test_data(self):
        """Build test data with values outside the 10-20 range."""
        return [
            TestModel(
                name="Item 1",
                category="A",
                value=100,
                count=5,  # Less than 10
                is_active=True,
                status="active",
                detail={"settings": {"theme": "light"}},
            ),
            TestModel(
                name="Item 2",
                category="A",
                value=200,
                count=25,  # Greater than 20
                is_active=False,
                status="inactive",
                detail={"settings": {"theme": "dark"}},
            ),
            TestModel(
                name="Item 3",
                category="B",
                value=150,
                count=15,  # Within range (will be excluded)
                is_active=None,
                status="pending",
                detail={"settings": {"theme": "custom"}},
            ),
        ]

    def test_filter_range_inclusive(self):
        filter_deps = create_combined_filter_dependency(
            GenericNumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=True,
                include_max_bound=True,
            ),
            orm_model=TestModel,
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
            GenericNumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=False,
                include_max_bound=False,
            ),
            orm_model=TestModel,
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
            GenericNumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=True,
                include_max_bound=True,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"min_count": 10})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["count"] >= 10 for item in response.json())

    def test_filter_range_exclude(self):
        filter_deps = create_combined_filter_dependency(
            GenericNumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                exclude=True,
            ),
            orm_model=TestModel,
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
            GenericNumericRangeCriteria(
                field="count",
                min_alias="min_count",
                max_alias="max_count",
                numeric_type=int,
                include_min_bound=True,
                include_max_bound=False,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"min_count": 10, "max_count": 20}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(10 <= item["count"] < 20 for item in response.json())


class TestGenericNumericExactCriteria(BaseFilterTest):
    def test_filter_exact_match(self):
        filter_deps = create_combined_filter_dependency(
            GenericNumericExactCriteria(
                field="count",
                alias="count",
                numeric_type=int,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"count": 10})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["count"] == 10 for item in response.json())

    def test_filter_exact_exclude(self):
        filter_deps = create_combined_filter_dependency(
            GenericNumericExactCriteria(
                field="count",
                alias="count",
                exclude=True,
                numeric_type=int,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"count": 10})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(item["count"] != 10 for item in response.json())

    def test_filter_exact_none(self):
        filter_deps = create_combined_filter_dependency(
            GenericNumericExactCriteria(
                field="count",
                alias="count",
                numeric_type=int,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) > 0
