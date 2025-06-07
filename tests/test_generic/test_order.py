from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.order import (
    OrderCriteria,
    OrderType,
)
from tests.conftest import BaseFilterTest, TestModel


class TestOrderCriteria(BaseFilterTest):
    def test_filter_max_global(self):
        filter_deps = create_combined_filter_dependency(
            OrderCriteria(
                field="count",
                order_type=OrderType.MAX,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        max_count = max(item["count"] for item in data)
        assert data[0]["count"] == max_count

    def test_filter_min_global(self):
        filter_deps = create_combined_filter_dependency(
            OrderCriteria(
                field="count",
                order_type=OrderType.MIN,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        min_count = min(item["count"] for item in data)
        assert data[0]["count"] == min_count

    def test_filter_max_partitioned(self):
        filter_deps = create_combined_filter_dependency(
            OrderCriteria(
                field="count",
                partition_by=["category"],
                order_type=OrderType.MAX,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        data = response.json()

        # Group items by category and verify max values
        categories = {}
        for item in data:
            category = item["category"]
            if category not in categories:
                categories[category] = item["count"]
            else:
                assert item["count"] <= categories[category]

    def test_filter_min_partitioned(self):
        filter_deps = create_combined_filter_dependency(
            OrderCriteria(
                field="count",
                partition_by=["category"],
                order_type=OrderType.MIN,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        data = response.json()

        # Group items by category and verify min values
        categories = {}
        for item in data:
            category = item["category"]
            if category not in categories:
                categories[category] = item["count"]
            else:
                assert item["count"] >= categories[category]

    def test_filter_disabled(self):
        filter_deps = create_combined_filter_dependency(
            OrderCriteria(
                field="count",
                order_type=OrderType.MAX,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"count_max": "false"})
        assert response.status_code == 200
        assert (
            len(response.json()) > 0
        )  # Should return all items when filter is disabled
