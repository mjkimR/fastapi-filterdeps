import pytest
from datetime import datetime, timedelta, timezone
from dateutil.relativedelta import relativedelta
import operator
import re

from fastapi_filterdeps.filters.column.relative_time import (
    RelativeTimeCriteria,
    RelativeTimeMatchType,
)
from fastapi_filterdeps import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestRelativeTimeCriteria(BaseFilterTest):
    """Test suite for the new string-based RelativeTimeCriteria."""

    @pytest.mark.parametrize(
        "match_type,input_val,expected_delta",
        [
            (RelativeTimeMatchType.RANGE_TO_NOW, "-3d", timedelta(days=-3)),
            (RelativeTimeMatchType.RANGE_TO_NOW, "-2w", timedelta(weeks=-2)),
            (RelativeTimeMatchType.RANGE_TO_NOW, "-1m", relativedelta(months=-1)),
            (RelativeTimeMatchType.RANGE_TO_NOW, "-1y", relativedelta(years=-1)),
            (RelativeTimeMatchType.BEFORE, "-3d", timedelta(days=-3)),
            (RelativeTimeMatchType.AFTER, "-8d", timedelta(days=-8)),
        ],
    )
    @pytest.mark.parametrize(
        "include_bound,op_start,op_end,op",
        [
            (True, operator.ge, operator.le, operator.le),
            (False, operator.gt, operator.lt, operator.lt),
        ],
    )
    def test_relative_time_all_types(
        self, match_type, input_val, expected_delta, include_bound, op_start, op_end, op
    ):
        class TestFilterSet(FilterSet):
            class Meta:
                orm_model = Post

            created = RelativeTimeCriteria(
                field="created_at",
                match_type=match_type,
                include_bound=include_bound,
            )

        self.setup_filter(filter_deps=TestFilterSet)
        response = self.client.get("/test-items", params={"created": input_val})
        assert response.status_code == 200
        data = response.json()
        now = datetime.now(timezone.utc)
        if match_type == RelativeTimeMatchType.RANGE_TO_NOW:
            match = re.match(r"([+-]?)(\d+)", input_val)
            offset = int(f"{match.group(1)}{match.group(2)}")
            target_date = now + expected_delta
            start_date, end_date = (
                (target_date, now) if offset <= 0 else (now, target_date)
            )
            assert len(data) > 0, f"No results for input {input_val}"
            for item in data:
                item_time = datetime.fromisoformat(item["created_at"]).replace(
                    tzinfo=timezone.utc
                )
                if offset <= 0:
                    assert op_start(item_time, start_date)
                else:
                    assert op_end(item_time, end_date)
        elif match_type == RelativeTimeMatchType.BEFORE:
            target_date = now + expected_delta
            assert len(data) > 0
            for item in data:
                item_time = datetime.fromisoformat(item["created_at"]).replace(
                    tzinfo=timezone.utc
                )
                assert op(item_time, target_date)
        elif match_type == RelativeTimeMatchType.AFTER:
            target_date = now + expected_delta
            assert len(data) > 0
            for item in data:
                item_time = datetime.fromisoformat(item["created_at"]).replace(
                    tzinfo=timezone.utc
                )
                assert op_start(item_time, target_date)

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
