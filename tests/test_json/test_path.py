from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.json.path import JsonPathCriteria, JsonPathOperation
from tests.conftest import BaseFilterTest, BasicModel


class TestJsonPathCriteria(BaseFilterTest):
    def build_test_data(self):
        """Override test data with nested JSON fields."""
        return [
            BasicModel(
                name="Item 1",
                category="A",
                value=100,
                detail={
                    "settings": {
                        "theme": "light",
                        "notifications": True,
                        "preferences": {"language": "en", "timezone": "UTC"},
                    },
                    "metadata": {"tags": ["important", "featured"], "version": "1.0"},
                },
            ),
            BasicModel(
                name="Item 2",
                category="B",
                value=200,
                detail={
                    "settings": {
                        "theme": "dark",
                        "notifications": False,
                        "preferences": {"language": "ko", "timezone": "Asia/Seoul"},
                    },
                    "metadata": {"tags": ["draft"], "version": "2.0"},
                },
            ),
            BasicModel(
                name="Item 3",
                category="C",
                value=300,
                detail={
                    "settings": {
                        "theme": "custom",
                        "notifications": True,
                        "preferences": {"language": "en", "timezone": "GMT"},
                    },
                    "metadata": {"tags": ["important"], "version": "1.1"},
                },
            ),
        ]

    def test_equals_operation(self):
        """Test JSON path equals operation."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "theme"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "light"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["detail"]["settings"]["theme"] == "light"

    def test_exists_operation(self):
        """Test JSON path exists operation."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "notifications"],
                operation=JsonPathOperation.EXISTS,
                use_json_extract=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": True})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("notifications" in item["detail"]["settings"] for item in data)

    def test_nested_path_equals(self):
        """Test filtering on deeply nested JSON path."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "preferences", "language"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "en"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(
            item["detail"]["settings"]["preferences"]["language"] == "en"
            for item in data
        )

    def test_number_filter(self):
        """Test filtering on numeric values."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["metadata", "version"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "1.0"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["detail"]["metadata"]["version"] == "1.0"

    def test_invalid_path(self):
        """Test behavior with invalid JSON path."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["nonexistent", "path"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # No items match the invalid path

    def test_complex_json_path(self):
        """Test complex JSON path with multiple levels."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "preferences", "timezone"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "Asia/Seoul"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["detail"]["settings"]["preferences"]["timezone"] == "Asia/Seoul"
