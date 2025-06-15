from datetime import datetime, timedelta, UTC
from dateutil.relativedelta import relativedelta
import pytest
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.time import (
    TimeCriteria,
    TimeMatchType,
    RelativeTimeCriteria,
    TimeUnit,
)
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


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
        filter_deps = create_combined_filter_dependency(
            TimeCriteria(
                field="created_at",
                alias="created_since",
                match_type=match_type,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

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
        filter_deps = create_combined_filter_dependency(
            TimeCriteria(
                field="created_at",
                alias="created_since",
                match_type=TimeMatchType.GTE,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        # Make a request without the 'created_since' parameter
        response = self.client.get("/test-items")
        assert response.status_code == 200
        # All items should be returned
        assert len(response.json()) == len(self.test_data["items"])


class TestRelativeTimeCriteria(BaseFilterTest):
    def build_test_data(self):
        now = datetime.now(UTC)
        return [
            BasicModel(
                name="Item 1",
                category="A",
                value=100,
                created_at=now - timedelta(days=30),
            ),
            BasicModel(
                name="Item 2",
                category="A",
                value=200,
                created_at=now - timedelta(days=14),
            ),
            BasicModel(
                name="Item 3",
                category="B",
                value=150,
                created_at=now - timedelta(days=7),
            ),
            BasicModel(
                name="Item 4",
                category="B",
                value=300,
                created_at=now - timedelta(days=1),
            ),
        ]

    def test_filter_relative_time_days(self):
        filter_deps = create_combined_filter_dependency(
            RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        reference = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_reference": reference.isoformat(),
                "created_at_unit": TimeUnit.DAY.value,
                "created_at_offset": -7,
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            reference - timedelta(days=7)
            <= datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            <= reference
            for item in response.json()
        )

    def test_filter_relative_time_weeks(self):
        filter_deps = create_combined_filter_dependency(
            RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        reference = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_reference": reference.isoformat(),
                "created_at_unit": TimeUnit.WEEK.value,
                "created_at_offset": -1,
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            reference - timedelta(weeks=1)
            <= datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            <= reference
            for item in response.json()
        )

    def test_filter_relative_time_months(self):
        filter_deps = create_combined_filter_dependency(
            RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        reference = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_reference": reference.isoformat(),
                "created_at_unit": TimeUnit.MONTH.value,
                "created_at_offset": -1,
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            reference - relativedelta(months=1)
            <= datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            <= reference
            for item in response.json()
        )

    def test_filter_relative_time_years(self):
        filter_deps = create_combined_filter_dependency(
            RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        reference = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_reference": reference.isoformat(),
                "created_at_unit": TimeUnit.YEAR.value,
                "created_at_offset": -1,
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0

    def test_filter_relative_time_exclusive_bounds(self):
        filter_deps = create_combined_filter_dependency(
            RelativeTimeCriteria(
                field="created_at",
                include_start_bound=False,
                include_end_bound=False,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        reference = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_reference": reference.isoformat(),
                "created_at_unit": TimeUnit.DAY.value,
                "created_at_offset": -7,
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            reference - timedelta(days=7)
            < datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            < reference
            for item in response.json()
        )

    def test_filter_relative_time_mixed_bounds(self):
        filter_deps = create_combined_filter_dependency(
            RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=False,
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        reference = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_reference": reference.isoformat(),
                "created_at_unit": TimeUnit.DAY.value,
                "created_at_offset": -7,
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            reference - timedelta(days=7)
            <= datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            < reference
            for item in response.json()
        )
