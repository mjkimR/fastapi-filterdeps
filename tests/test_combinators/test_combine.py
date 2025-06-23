from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.simple.binary import BinaryCriteria, BinaryFilterType
from fastapi_filterdeps.simple.numeric import NumericCriteria, NumericFilterType
from fastapi_filterdeps.simple.string import StringCriteria, StringMatchType
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


class TestCombineCriteria(BaseFilterTest):
    def test_and_operator(self):
        """
        Tests the AND operator.
        It should return items that are in category 'A' AND are active.
        """
        # Define individual filters
        category_filter = StringCriteria(
            field="category", alias="category", match_type=StringMatchType.EXACT
        )
        active_filter = BinaryCriteria(
            field="is_active", alias="active", filter_type=BinaryFilterType.IS_TRUE
        )

        # Combine them with AND operator
        combined_filter = category_filter & active_filter
        filter_deps = create_combined_filter_dependency(
            combined_filter, orm_model=BasicModel
        )
        self.setup_filter(filter_deps=filter_deps)

        # Act
        response = self.client.get(
            "/test-items", params={"category": "A", "active": "true"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["category"] == "A"
        assert data[0]["is_active"] is True

    def test_or_operator(self):
        """
        Tests the OR operator.
        It should return items that are in category 'A' OR have a count >= 25.
        """
        # Define individual filters
        category_filter = StringCriteria(
            field="category", alias="category", match_type=StringMatchType.EXACT
        )
        count_filter = NumericCriteria(
            field="count",
            alias="min_count",
            numeric_type=int,
            operator=NumericFilterType.GTE,
        )

        # Combine them with OR operator
        combined_filter = category_filter | count_filter
        filter_deps = create_combined_filter_dependency(
            combined_filter, orm_model=BasicModel
        )
        self.setup_filter(filter_deps=filter_deps)

        # Act
        response = self.client.get(
            "/test-items", params={"category": "A", "min_count": 25}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Expected: Item 1 (cat A), Item 2 (cat A), Item 4 (count 30), Item 5 (count 25)
        assert len(data) == 4
        returned_ids = {item["id"] for item in data}
        assert returned_ids == {1, 2, 4, 5}

    def test_chained_and_operator(self):
        """
        Tests chaining multiple AND operators.
        It should return items in category 'C' AND count >= 25 AND is_active is False.
        """
        category_filter = StringCriteria(
            field="category", alias="category", match_type=StringMatchType.EXACT
        )
        count_filter = NumericCriteria(
            field="count",
            alias="min_count",
            numeric_type=int,
            operator=NumericFilterType.GTE,
        )
        inactive_filter = BinaryCriteria(
            field="is_active", alias="inactive", filter_type=BinaryFilterType.IS_FALSE
        )

        # Chain multiple AND operators
        combined_filter = category_filter & count_filter & inactive_filter
        filter_deps = create_combined_filter_dependency(
            combined_filter, orm_model=BasicModel
        )
        self.setup_filter(filter_deps=filter_deps)

        # Act
        response = self.client.get(
            "/test-items", params={"category": "C", "min_count": 25, "inactive": "true"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Expected: Item 5 (category='C', count=25, is_active=False)
        assert len(data) == 1
        assert data[0]["id"] == 5

    def test_nested_and_or_operator(self):
        """
        Tests nested logic: active AND (category 'B' OR category 'C').
        """
        active_filter = BinaryCriteria(
            field="is_active", alias="active", filter_type=BinaryFilterType.IS_TRUE
        )
        cat_b_filter = StringCriteria(
            field="category", alias="cat_b", match_type=StringMatchType.EXACT
        )
        cat_c_filter = StringCriteria(
            field="category", alias="cat_c", match_type=StringMatchType.EXACT
        )

        # Create nested logic: active AND (B OR C)
        combined_filter = active_filter & (cat_b_filter | cat_c_filter)
        filter_deps = create_combined_filter_dependency(
            combined_filter, orm_model=BasicModel
        )
        self.setup_filter(filter_deps=filter_deps)

        # Act
        response = self.client.get(
            "/test-items", params={"active": "true", "cat_b": "B", "cat_c": "C"}
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        # Expected: Item 4 (active=True, category='C')
        assert len(data) == 1
        assert data[0]["id"] == 4
