from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.simple.numeric import (
    NumericCriteria,
    NumericFilterType,
)
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


class TestNumericCriteria(BaseFilterTest):
    """Test suite for the refactored NumericCriteria."""

    def test_filter_greater_than_or_equal(self):
        """Tests the '>=' functionality (e.g., min_count)."""
        filter_deps = create_combined_filter_dependency(
            NumericCriteria(
                field="count",
                alias="min_count",
                numeric_type=int,
                operator=NumericFilterType.GTE,  # Use 'greater than or equal' operator
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"min_count": 10})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["count"] >= 10 for item in data)

    def test_filter_less_than_or_equal(self):
        """Tests the '<=' functionality (e.g., max_count)."""
        filter_deps = create_combined_filter_dependency(
            NumericCriteria(
                field="count",
                alias="max_count",
                numeric_type=int,
                operator=NumericFilterType.LTE,  # Use 'less than or equal' operator
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"max_count": 20})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["count"] <= 20 for item in data)

    def test_filter_range_inclusive(self):
        """Tests an inclusive range by combining 'ge' and 'le' criteria."""
        filter_deps = create_combined_filter_dependency(
            NumericCriteria(
                field="count",
                alias="min_count",
                numeric_type=int,
                operator=NumericFilterType.GTE,
            ),
            NumericCriteria(
                field="count",
                alias="max_count",
                numeric_type=int,
                operator=NumericFilterType.LTE,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"min_count": 10, "max_count": 20}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(10 <= item["count"] <= 20 for item in data)

    def test_filter_range_exclusive(self):
        """Tests an exclusive range by combining 'gt' and 'lt' criteria."""
        filter_deps = create_combined_filter_dependency(
            NumericCriteria(
                field="count",
                alias="min_count_exclusive",
                numeric_type=int,
                operator=NumericFilterType.GT,  # Use 'greater than' operator
            ),
            NumericCriteria(
                field="count",
                alias="max_count_exclusive",
                numeric_type=int,
                operator=NumericFilterType.LT,  # Use 'less than' operator
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items",
            params={"min_count_exclusive": 10, "max_count_exclusive": 20},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(10 < item["count"] < 20 for item in data)

    def test_filter_exact_match(self):
        """Tests for exact value matching using the 'eq' operator."""
        filter_deps = create_combined_filter_dependency(
            NumericCriteria(
                field="count",
                alias="count",
                numeric_type=int,
                operator=NumericFilterType.EQ,  # Use 'equal' operator
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"count": 10})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["count"] == 10 for item in data)

    def test_filter_not_equal(self):
        """Tests for non-equality using the 'ne' operator."""
        filter_deps = create_combined_filter_dependency(
            NumericCriteria(
                field="count",
                alias="count_ne",
                numeric_type=int,
                operator=NumericFilterType.NE,  # Use 'not equal' operator
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"count_ne": 10})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["count"] != 10 for item in data)

    def test_filter_no_param_provided(self):
        """Tests that if no query parameter is provided, all items are returned."""
        filter_deps = create_combined_filter_dependency(
            NumericCriteria(
                field="count",
                alias="count",
                numeric_type=int,
                operator=NumericFilterType.EQ,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        # Should return all items as no filter is active
        assert len(response.json()) == len(self.test_data["items"])
