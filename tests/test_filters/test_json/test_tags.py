from fastapi_filterdeps.filters.json.tags import JsonDictTagsCriteria
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest, Post


class TestJsonDictTagsCriteria(BaseFilterTest):
    def test_filter_by_boolean_tag(self, json_strategy):
        """Test filtering by boolean tag existence."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            tags = JsonDictTagsCriteria(
                field="detail",
                alias="tags",
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        # Test single boolean tag
        response = self.client.get("/test-items", params={"tags": ["urgent"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all("urgent" in item["detail"]["tags"] for item in data)

    def test_filter_by_value_tag(self, json_strategy):
        """Test filtering by tag with specific value."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            tags = JsonDictTagsCriteria(
                field="detail",
                alias="tags",
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        # Test tag with value
        response = self.client.get("/test-items", params={"tags": ["language:en"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["detail"]["tags"]["language"] == "en" for item in data)

    def test_filter_by_multiple_tags(self, json_strategy):
        """Test filtering by multiple tags combination."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            tags = JsonDictTagsCriteria(
                field="detail",
                alias="tags",
                strategy=json_strategy,
            )

        self.setup_filter(filter_deps=TestFilerSet)

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
