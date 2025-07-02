from fastapi_filterdeps.filters.column.numeric import (
    NumericCriteria,
    NumericFilterType,
)
from fastapi_filterdeps import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post
import pytest


class TestNumericCriteria(BaseFilterTest):
    """Test suite for the refactored NumericCriteria."""

    @pytest.mark.parametrize(
        "alias,operator,param,assert_func",
        [
            ("min_count", NumericFilterType.GTE, 10, lambda x: x >= 10),
            ("max_count", NumericFilterType.LTE, 20, lambda x: x <= 20),
            ("count", NumericFilterType.EQ, 10, lambda x: x == 10),
            ("count_ne", NumericFilterType.NE, 10, lambda x: x != 10),
            ("gt_count", NumericFilterType.GT, 10, lambda x: x > 10),
            ("lt_count", NumericFilterType.LT, 20, lambda x: x < 20),
        ],
    )
    def test_numeric_single_operator(self, alias, operator, param, assert_func):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            criteria = NumericCriteria(
                field="count",
                alias=alias,
                numeric_type=int,
                operator=operator,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={alias: param})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(assert_func(item["count"]) for item in data)

    @pytest.mark.parametrize(
        "min_alias,max_alias,min_param,max_param,assert_func",
        [
            ("min_count", "max_count", 10, 20, lambda x: 10 <= x <= 20),
            (
                "min_count_exclusive",
                "max_count_exclusive",
                10,
                20,
                lambda x: 10 < x < 20,
            ),
        ],
    )
    def test_numeric_range(
        self, min_alias, max_alias, min_param, max_param, assert_func
    ):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            min_criteria = NumericCriteria(
                field="count",
                alias=min_alias,
                numeric_type=int,
                operator=(
                    NumericFilterType.GT
                    if "exclusive" in min_alias
                    else NumericFilterType.GTE
                ),
            )
            max_criteria = NumericCriteria(
                field="count",
                alias=max_alias,
                numeric_type=int,
                operator=(
                    NumericFilterType.LT
                    if "exclusive" in max_alias
                    else NumericFilterType.LTE
                ),
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get(
            "/test-items", params={min_alias: min_param, max_alias: max_param}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all(assert_func(item["count"]) for item in data)

    def test_filter_no_param_provided(self):
        """Tests that if no query parameter is provided, all items are returned."""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            count = NumericCriteria(
                field="count",
                alias="count",
                numeric_type=int,
                operator=NumericFilterType.EQ,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items")
        assert response.status_code == 200
        assert len(response.json()) == len(self.test_data["items"])
