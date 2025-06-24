from fastapi_filterdeps.filters.json.path import JsonPathCriteria, JsonPathOperation
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest, Post


class TestJsonPathCriteria(BaseFilterTest):
    def test_equals_operation(self, json_strategy):
        """Test JSON path equals operation."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            value = JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "theme"],
                operation=JsonPathOperation.EQUALS,
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        response = self.client.get("/test-items", params={"value": "light"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["detail"]["settings"]["theme"] == "light" for item in data)

    def test_exists_operation(self, json_strategy):
        """Test JSON path exists operation."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            value = JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "notifications"],
                operation=JsonPathOperation.EXISTS,
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        response = self.client.get("/test-items", params={"value": True})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all("notifications" in item["detail"]["settings"] for item in data)

    def test_nested_path_equals(self, json_strategy):
        """Test filtering on deeply nested JSON path."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            value = JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "preferences", "language"],
                operation=JsonPathOperation.EQUALS,
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        response = self.client.get("/test-items", params={"value": "en"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(
            item["detail"]["settings"]["preferences"]["language"] == "en"
            for item in data
        )

    def test_number_filter(self, json_strategy):
        """Test filtering on numeric values."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            value = JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["metadata", "version"],
                operation=JsonPathOperation.EQUALS,
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        response = self.client.get("/test-items", params={"value": "1.0"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["detail"]["metadata"]["version"] == "1.0" for item in data)

    def test_invalid_path(self, json_strategy):
        """Test behavior with invalid JSON path."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            value = JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["nonexistent", "path"],
                operation=JsonPathOperation.EQUALS,
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        response = self.client.get("/test-items", params={"value": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # No items match the invalid path

    def test_complex_json_path(self, json_strategy):
        """Test complex JSON path with multiple levels."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            value = JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "preferences", "timezone"],
                operation=JsonPathOperation.EQUALS,
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        response = self.client.get("/test-items", params={"value": "Asia/Seoul"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(
            item["detail"]["settings"]["preferences"]["timezone"] == "Asia/Seoul"
            for item in data
        )
