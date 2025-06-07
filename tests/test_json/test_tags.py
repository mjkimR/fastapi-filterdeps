from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.json.tags import JsonDictTagsCriteria
from tests.conftest import BaseFilterTest, TestModel


class TestJsonDictTagsCriteria(BaseFilterTest):
    def build_test_data(self):
        """Override test data with JSON tag fields."""
        return [
            TestModel(
                name="Item 1",
                category="A",
                value=100,
                detail={"tags": {"urgent": True, "priority": "high", "language": "en"}},
            ),
            TestModel(
                name="Item 2",
                category="B",
                value=200,
                detail={
                    "tags": {"featured": True, "priority": "low", "language": "ko"}
                },
            ),
            TestModel(
                name="Item 3",
                category="C",
                value=300,
                detail={"tags": {"draft": True, "language": "en"}},
            ),
        ]

    def test_filter_by_boolean_tag(self):
        """Test filtering by boolean tag existence."""
        filter_deps = create_combined_filter_dependency(
            JsonDictTagsCriteria(
                field="detail",  # Use the JSON field name
                alias="tags",
                use_json_extract=True,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        # Test single boolean tag
        response = self.client.get("/test-items", params={"tags": ["urgent"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Item 1"
        assert data[0]["detail"]["tags"]["urgent"] is True

    def test_filter_by_value_tag(self):
        """Test filtering by tag with specific value."""
        filter_deps = create_combined_filter_dependency(
            JsonDictTagsCriteria(
                field="detail",  # Use the JSON field name
                alias="tags",
                use_json_extract=True,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        # Test tag with value
        response = self.client.get("/test-items", params={"tags": ["language:en"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert all(item["detail"]["tags"]["language"] == "en" for item in data)

    def test_filter_by_multiple_tags(self):
        """Test filtering by multiple tags combination."""
        filter_deps = create_combined_filter_dependency(
            JsonDictTagsCriteria(
                field="detail",  # Use the JSON field name
                alias="tags",
                use_json_extract=True,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        # Test multiple tags
        response = self.client.get(
            "/test-items", params={"tags": ["priority:high", "language:en"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Item 1"
        assert data[0]["detail"]["tags"]["priority"] == "high"
        assert data[0]["detail"]["tags"]["language"] == "en"

    def test_parse_tags_from_query(self):
        """Test tag query parsing functionality."""
        tags_query = ["urgent", "priority:high", "language:en"]
        parsed = JsonDictTagsCriteria.parse_tags_from_query(tags_query)

        assert parsed == {"urgent": True, "priority": "high", "language": "en"}
