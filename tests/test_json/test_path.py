from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.json.path import JsonPathCriteria, JsonPathOperation
from tests.conftest import BaseFilterTest, BasicModel


class TestJsonPathCriteria(BaseFilterTest):
    def test_equals_operation(self, db_type: str):
        """Test JSON path equals operation."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "theme"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=db_type == "sqlite",  # Use JSON extract for SQLite
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "light"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["detail"]["settings"]["theme"] == "light" for item in data)

    def test_exists_operation(self, db_type: str):
        """Test JSON path exists operation."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "notifications"],
                operation=JsonPathOperation.EXISTS,
                use_json_extract=db_type == "sqlite",  # Use JSON extract for SQLite
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": True})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all("notifications" in item["detail"]["settings"] for item in data)

    def test_nested_path_equals(self, db_type: str):
        """Test filtering on deeply nested JSON path."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "preferences", "language"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=db_type == "sqlite",  # Use JSON extract for SQLite
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "en"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(
            item["detail"]["settings"]["preferences"]["language"] == "en"
            for item in data
        )

    def test_number_filter(self, db_type: str):
        """Test filtering on numeric values."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["metadata", "version"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=db_type == "sqlite",  # Use JSON extract for SQLite
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "1.0"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["detail"]["metadata"]["version"] == "1.0" for item in data)

    def test_invalid_path(self, db_type: str):
        """Test behavior with invalid JSON path."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["nonexistent", "path"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=db_type == "sqlite",  # Use JSON extract for SQLite
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "test"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 0  # No items match the invalid path

    def test_complex_json_path(self, db_type: str):
        """Test complex JSON path with multiple levels."""
        filter_deps = create_combined_filter_dependency(
            JsonPathCriteria(
                field="detail",
                alias="value",
                json_path=["settings", "preferences", "timezone"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=db_type == "sqlite",  # Use JSON extract for SQLite
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        response = self.client.get("/test-items", params={"value": "Asia/Seoul"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(
            item["detail"]["settings"]["preferences"]["timezone"] == "Asia/Seoul"
            for item in data
        )
