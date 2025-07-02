from fastapi_filterdeps.filters.column.order import (
    OrderCriteria,
    OrderType,
)
from fastapi_filterdeps import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestOrderCriteria(BaseFilterTest):
    def test_filter_max_global(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            count_max = OrderCriteria(
                field="count",
                order_type=OrderType.MAX,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"count_max": "true"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        max_count = max(item["count"] for item in data)
        assert data[0]["count"] == max_count

    def test_filter_min_global(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            count_min = OrderCriteria(
                field="count",
                order_type=OrderType.MIN,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        min_count = min(item["count"] for item in data)
        assert data[0]["count"] == min_count

    def test_filter_max_partitioned(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            count_max = OrderCriteria(
                field="count",
                partition_by=["category"],
                order_type=OrderType.MAX,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"count_max": "true"})
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
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            count_min = OrderCriteria(
                field="count",
                partition_by=["category"],
                order_type=OrderType.MIN,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"count_min": "true"})
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
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            count_max = OrderCriteria(
                field="count",
                order_type=OrderType.MAX,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"count_max": "false"})
        assert response.status_code == 200
        assert (
            len(response.json()) > 0
        )  # Should return all items when filter is disabled
