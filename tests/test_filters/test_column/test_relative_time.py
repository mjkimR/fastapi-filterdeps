import pytest
from datetime import datetime, timedelta, UTC
from dateutil.relativedelta import relativedelta
import operator
import re

from fastapi_filterdeps.filters.column.relative_time import (
    RelativeTimeCriteria,
    RelativeTimeMatchType,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestRelativeTimeCriteria(BaseFilterTest):
    """Test suite for the new string-based RelativeTimeCriteria."""

    # --- Tests for RANGE_TO_NOW ---
    @pytest.mark.parametrize(
        "input_val, expected_delta",
        [
            ("-3d", timedelta(days=-3)),
            ("-2w", timedelta(weeks=-2)),
            ("-1m", relativedelta(months=-1)),
            ("-1y", relativedelta(years=-1)),
        ],
    )
    @pytest.mark.parametrize("include_bound", [True, False])
    def test_range_to_now(self, input_val, expected_delta, include_bound):
        """Tests RANGE_TO_NOW with various units and bounds."""

        class TestFilterSet(FilterSet):
            class Meta:
                orm_model = Post

            created_range = RelativeTimeCriteria(
                field="created_at",
                match_type=RelativeTimeMatchType.RANGE_TO_NOW,
                include_bound=include_bound,
            )

        self.setup_filter(filter_deps=TestFilterSet)
        response = self.client.get("/test-items", params={"created_range": input_val})
        assert response.status_code == 200
        data = response.json()

        op_start = operator.ge if include_bound else operator.gt
        op_end = operator.le if include_bound else operator.lt

        now = datetime.now(UTC)
        match = re.match(r"([+-]?)(\d+)", input_val)
        offset = int(f"{match.group(1)}{match.group(2)}")
        target_date = now + expected_delta

        start_date, end_date = (target_date, now) if offset <= 0 else (now, target_date)

        assert len(data) > 0, f"No results for input {input_val}"
        for item in data:
            item_time = datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            if offset <= 0:
                assert op_start(item_time, start_date)
            else:
                assert op_end(item_time, end_date)

    # --- Tests for BEFORE ---
    @pytest.mark.parametrize("include_bound", [True, False])
    def test_before(self, include_bound):
        """Tests BEFORE match type with and without inclusive bounds."""

        class TestFilterSet(FilterSet):
            class Meta:
                orm_model = Post

            created_before = RelativeTimeCriteria(
                field="created_at",
                match_type=RelativeTimeMatchType.BEFORE,
                include_bound=include_bound,
            )

        self.setup_filter(filter_deps=TestFilterSet)
        response = self.client.get("/test-items", params={"created_before": "-3d"})
        assert response.status_code == 200
        data = response.json()

        now = datetime.now(UTC)
        op = operator.le if include_bound else operator.lt
        target_date = now + timedelta(days=-3)

        assert len(data) > 0
        for item in data:
            item_time = datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            assert op(item_time, target_date)

    # --- Tests for AFTER ---
    @pytest.mark.parametrize("include_bound", [True, False])
    def test_after(self, include_bound):
        """Tests AFTER match type with and without inclusive bounds."""

        class TestFilterSet(FilterSet):
            class Meta:
                orm_model = Post

            created_after = RelativeTimeCriteria(
                field="created_at",
                match_type=RelativeTimeMatchType.AFTER,
                include_bound=include_bound,
            )

        self.setup_filter(filter_deps=TestFilterSet)
        response = self.client.get("/test-items", params={"created_after": "-8d"})
        assert response.status_code == 200
        data = response.json()

        now = datetime.now(UTC)
        op = operator.ge if include_bound else operator.gt
        target_date = now + timedelta(days=-8)

        assert len(data) > 0
        for item in data:
            item_time = datetime.fromisoformat(item["created_at"]).replace(tzinfo=UTC)
            assert op(item_time, target_date)

    # --- Edge case and validation tests ---
    def test_no_input_returns_all(self):
        """Tests that if no query parameter is provided, all items are returned."""

        class TestFilterSet(FilterSet):
            class Meta:
                orm_model = Post

            created_within = RelativeTimeCriteria(field="created_at")

        self.setup_filter(filter_deps=TestFilterSet)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) == len(self.test_data["items"])

    @pytest.mark.parametrize(
        "invalid_value",
        ["7", "-d", "1week", "foo", "+-7d", "-7x"],
    )
    def test_invalid_format_raises_422(self, invalid_value):
        """Tests that improperly formatted strings are rejected by FastAPI validation."""

        class TestFilterSet(FilterSet):
            class Meta:
                orm_model = Post

            created_within = RelativeTimeCriteria(field="created_at")

        self.setup_filter(filter_deps=TestFilterSet)
        response = self.client.get(
            "/test-items", params={"created_within": invalid_value}
        )
        assert response.status_code == 422

    def test_sign_behavior(self):
        """Tests that an explicit '+' and no sign are treated as positive offsets."""

        class TestFilterSet(FilterSet):
            class Meta:
                orm_model = Post

            created_range = RelativeTimeCriteria(
                field="created_at", match_type=RelativeTimeMatchType.RANGE_TO_NOW
            )

        self.setup_filter(filter_deps=TestFilterSet)

        # In the provided code, no sign defaults to positive.
        # Let's verify "3d" and "+3d" produce the same result.
        response_no_sign = self.client.get(
            "/test-items", params={"created_range": "3d"}
        )
        response_plus_sign = self.client.get(
            "/test-items", params={"created_range": "+3d"}
        )

        assert response_no_sign.status_code == 200
        assert response_plus_sign.status_code == 200
        assert response_no_sign.json() == response_plus_sign.json()

        # And this result should be different from a negative offset
        response_minus_sign = self.client.get(
            "/test-items", params={"created_range": "-3d"}
        )
        assert response_minus_sign.status_code == 200
        assert response_no_sign.json() != response_minus_sign.json()
