from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.numeric import NumericCriteria, NumericFilterType
from fastapi_filterdeps.generic.string import StringCriteria, StringMatchType
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


class TestInvertCriteria(BaseFilterTest):
    def test_invert_string_filter(self):
        """
        Tests NOT logic on a string filter.
        It should return all items where the name is NOT 'Item 1'.
        """
        # Define a standard string filter
        name_filter = StringCriteria(
            field="name", alias="name", match_type=StringMatchType.EXACT
        )

        # Create the dependency with the inverted filter
        filter_deps = create_combined_filter_dependency(
            ~name_filter, orm_model=BasicModel
        )
        self.setup_filter(filter_deps=filter_deps)

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
        # Define a numeric filter for count >= 20
        count_filter = NumericCriteria(
            field="count",
            alias="min_count",
            numeric_type=int,
            operator=NumericFilterType.GTE,
        )

        # Create the dependency with the inverted filter
        filter_deps = create_combined_filter_dependency(
            ~count_filter, orm_model=BasicModel
        )
        self.setup_filter(filter_deps=filter_deps)

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
        filter_deps = create_combined_filter_dependency(
            ~count_filter, orm_model=BasicModel
        )
        self.setup_filter(filter_deps=filter_deps)

        # Act: Make a request without the 'min_count' param
        response = self.client.get("/test-items")

        # Assert
        assert response.status_code == 200
        # Should return all items as the filter is not active
        assert len(response.json()) == len(self.test_data["items"])
