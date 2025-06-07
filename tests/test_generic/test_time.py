from datetime import datetime, timedelta, UTC
from dateutil.relativedelta import relativedelta
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.time import (
    TimeRangeCriteria,
    RelativeTimeCriteria,
    TimeUnit,
)
from tests.conftest import BaseFilterTest, TestModel


class TestTimeRangeCriteria(BaseFilterTest):
    def build_test_data(self):
        now = datetime.now(UTC)
        return [
            TestModel(
                name="Item 1",
                category="A",
                value=100,
                created_at=now - timedelta(days=10),
            ),
            TestModel(
                name="Item 2",
                category="A",
                value=200,
                created_at=now - timedelta(days=5),
            ),
            TestModel(
                name="Item 3",
                category="B",
                value=150,
                created_at=now - timedelta(days=1),
            ),
            TestModel(name="Item 4", category="B", value=300, created_at=now),
        ]

    def test_filter_time_range_inclusive(self):
        filter_deps = create_combined_filter_dependency(
            TimeRangeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        start = datetime.now(UTC) - timedelta(days=7)
        end = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_start": start.isoformat(),
                "created_at_end": end.isoformat(),
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            start
            <= datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            <= end
            for item in response.json()
        )

    def test_filter_time_range_exclusive(self):
        filter_deps = create_combined_filter_dependency(
            TimeRangeCriteria(
                field="created_at",
                include_start_bound=False,
                include_end_bound=False,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        start = datetime.now(UTC) - timedelta(days=7)
        end = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_start": start.isoformat(),
                "created_at_end": end.isoformat(),
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            start < datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC) < end
            for item in response.json()
        )

    def test_filter_time_range_start_only(self):
        filter_deps = create_combined_filter_dependency(
            TimeRangeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=True,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        start = datetime.now(UTC) - timedelta(days=7)

        response = self.client.get(
            "/test-items", params={"created_at_start": start.isoformat()}
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC) >= start
            for item in response.json()
        )

    def test_filter_time_range_mixed_bounds(self):
        filter_deps = create_combined_filter_dependency(
            TimeRangeCriteria(
                field="created_at",
                include_start_bound=True,
                include_end_bound=False,
            ),
            orm_model=TestModel,
        )
        self.setup_filter(filter_deps=filter_deps)

        start = datetime.now(UTC) - timedelta(days=7)
        end = datetime.now(UTC)

        response = self.client.get(
            "/test-items",
            params={
                "created_at_start": start.isoformat(),
                "created_at_end": end.isoformat(),
            },
        )
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(
            start
            <= datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            < end
            for item in response.json()
        )


class TestRelativeTimeCriteria(BaseFilterTest):
    def build_test_data(self):
        now = datetime.now(UTC)
        return [
            TestModel(
                name="Item 1",
                category="A",
                value=100,
                created_at=now - timedelta(days=30),
            ),
            TestModel(
                name="Item 2",
                category="A",
                value=200,
                created_at=now - timedelta(days=14),
            ),
            TestModel(
                name="Item 3",
                category="B",
                value=150,
                created_at=now - timedelta(days=7),
            ),
            TestModel(
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
            orm_model=TestModel,
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
            orm_model=TestModel,
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
            orm_model=TestModel,
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
            orm_model=TestModel,
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
            orm_model=TestModel,
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
            orm_model=TestModel,
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
