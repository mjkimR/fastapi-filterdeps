from datetime import datetime, timedelta, UTC
from dateutil.relativedelta import relativedelta
from fastapi_filterdeps.filters.advanced.relative_time import (
    RelativeTimeCriteria,
    TimeUnit,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestRelativeTimeCriteria(BaseFilterTest):
    def build_test_data(self):
        now = datetime.now(UTC)
        return [
            Post(
                name="Item 1",
                category="A",
                value=100,
                created_at=now - timedelta(days=30),
            ),
            Post(
                name="Item 2",
                category="A",
                value=200,
                created_at=now - timedelta(days=14),
            ),
            Post(
                name="Item 3",
                category="B",
                value=150,
                created_at=now - timedelta(days=7),
            ),
            Post(
                name="Item 4",
                category="B",
                value=300,
                created_at=now - timedelta(days=1),
            ),
        ]

    def test_filter_relative_time_days(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_at = RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            )

        self.setup_filter(filter_deps=TestFilerSet)

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
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_at = RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            )

        self.setup_filter(filter_deps=TestFilerSet)

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
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_at = RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            )

        self.setup_filter(filter_deps=TestFilerSet)

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
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_at = RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            )

        self.setup_filter(filter_deps=TestFilerSet)

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
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_at = RelativeTimeCriteria(
                field="created_at",
                include_start_bound=False,
                include_end_bound=False,
            )

        self.setup_filter(filter_deps=TestFilerSet)

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
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            created_at = RelativeTimeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=False,
            )

        self.setup_filter(filter_deps=TestFilerSet)

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
