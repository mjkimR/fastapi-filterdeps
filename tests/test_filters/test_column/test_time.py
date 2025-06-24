from datetime import datetime, UTC
import pytest
from fastapi_filterdeps.filters.column.time import TimeCriteria, TimeMatchType
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestTimeCriteria(BaseFilterTest):
    """
    Tests for the updated TimeCriteria class.
    It verifies all comparison operations defined in TimeMatchType.
    """

    # Use parametrize to test all match types with a single test function
    @pytest.mark.parametrize(
        "match_type, operator",
        [
            (TimeMatchType.GTE, lambda a, b: a >= b),
            (TimeMatchType.GT, lambda a, b: a > b),
            (TimeMatchType.LTE, lambda a, b: a <= b),
            (TimeMatchType.LT, lambda a, b: a < b),
        ],
    )
    def test_filter_time_match_types(self, match_type, operator):
        """
        Verify that each TimeMatchType filters the datetime field correctly.
        """

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_since = TimeCriteria(
                field="created_at",
                alias="created_since",
                match_type=match_type,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        # Select a reference time from the test data for comparison
        reference_time = self.test_data["items"][2].created_at
        reference_time = reference_time.replace(tzinfo=UTC)

        # Make a request with the reference time
        response = self.client.get(
            "/test-items", params={"created_since": reference_time.isoformat()}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        # Assert that all returned items satisfy the condition
        for item in data:
            item_time = datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            assert operator(item_time, reference_time)

    def test_filter_time_no_value(self):
        """
        Verify that if no time value is provided, no filter is applied.
        """

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_since = TimeCriteria(
                field="created_at",
                alias="created_since",
                match_type=TimeMatchType.GTE,
            )

        self.setup_filter(filter_deps=TestFilerSet)

        # Make a request without the 'created_since' parameter
        response = self.client.get("/test-items")
        assert response.status_code == 200
        # All items should be returned
        assert len(response.json()) == len(self.test_data["items"])
