from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.json.tags import JsonDictTagsCriteria
from tests.conftest import BaseFilterTest, BasicModel


class TestJsonDictTagsCriteria(BaseFilterTest):
    def test_filter_by_boolean_tag(self, json_strategy):
        """Test filtering by boolean tag existence."""
        filter_deps = create_combined_filter_dependency(
            JsonDictTagsCriteria(
                field="detail",  # Use the JSON field name
                alias="tags",
                strategy=json_strategy,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        # Test single boolean tag
        response = self.client.get("/test-items", params={"tags": ["urgent"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all("urgent" in item["detail"]["tags"] for item in data)

    def test_filter_by_value_tag(self, json_strategy):
        """Test filtering by tag with specific value."""
        filter_deps = create_combined_filter_dependency(
            JsonDictTagsCriteria(
                field="detail",  # Use the JSON field name
                alias="tags",
                strategy=json_strategy,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        # Test tag with value
        response = self.client.get("/test-items", params={"tags": ["language:en"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["detail"]["tags"]["language"] == "en" for item in data)

    def test_filter_by_multiple_tags(self, json_strategy):
        """Test filtering by multiple tags combination."""
        filter_deps = create_combined_filter_dependency(
            JsonDictTagsCriteria(
                field="detail",  # Use the JSON field name
                alias="tags",
                strategy=json_strategy,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        # Test multiple tags
        response = self.client.get(
            "/test-items", params={"tags": ["priority:high", "language:en"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all("priority" in item["detail"]["tags"] for item in data)
        assert all(item["detail"]["tags"]["priority"] == "high" for item in data)
        assert all("language" in item["detail"]["tags"] for item in data)
        assert all(item["detail"]["tags"]["language"] == "en" for item in data)

    def test_parse_tags_from_query(self):
        """Test tag query parsing functionality."""
        tags_query = ["urgent", "priority:high", "language:en"]
        parsed = JsonDictTagsCriteria.parse_tags_from_query(tags_query)

        assert parsed == {"urgent": True, "priority": "high", "language": "en"}
