from fastapi_filterdeps.filters.column.numeric import NumericCriteria, NumericFilterType
from fastapi_filterdeps.filters.column.string import StringCriteria, StringMatchType
from fastapi_filterdeps import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestInvertCriteria(BaseFilterTest):
    def test_invert_string_filter(self):
        """
        Tests NOT logic on a string filter.
        It should return all items where the name is NOT 'Item 1'.
        """
        name_filter = StringCriteria(
            field="name", alias="name", match_type=StringMatchType.EXACT
        )

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            name = ~name_filter

        self.setup_filter(filter_deps=TestFilerSet)

        # Act
        response = self.client.get("/test-items", params={"name": "Item 1"})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == len(self.test_data["items"]) - 1
        assert all(item["name"] != "Item 1" for item in data)

    def test_invert_numeric_filter(self):
        """
        Tests NOT logic on a numeric filter.
        It should return all items with a count LESS THAN 20.
        """
        count_filter = NumericCriteria(
            field="count",
            alias="min_count",
            numeric_type=int,
            operator=NumericFilterType.GTE,
        )

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            min_count = ~count_filter

        self.setup_filter(filter_deps=TestFilerSet)

        # Act
        response = self.client.get("/test-items", params={"min_count": "20"})

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(item["count"] < 20 for item in data)

    def test_invert_with_no_active_nested_filter(self):
        """
        Tests that if the nested filter is not activated (no query param),
        the inverted filter also remains inactive and returns all items.
        """
        count_filter = NumericCriteria(
            field="count",
            alias="min_count",
            numeric_type=int,
            operator=NumericFilterType.GTE,
        )

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            min_count = ~count_filter

        self.setup_filter(filter_deps=TestFilerSet)

        # Act: Make a request without the 'min_count' param
        response = self.client.get("/test-items")

        # Assert
        assert response.status_code == 200
        # Should return all items as the filter is not active
        assert len(response.json()) == len(self.test_data["items"])
