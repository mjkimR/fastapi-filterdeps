from fastapi_filterdeps.filters.column.binary import (
    BinaryCriteria,
    BinaryFilterType,
)
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post
import pytest


class TestBinaryCriteria(BaseFilterTest):
    @pytest.mark.parametrize(
        "filter_type,alias,param,expected,assert_func",
        [
            (BinaryFilterType.IS_TRUE, "is_active", "true", True, lambda x: x is True),
            (BinaryFilterType.IS_TRUE, "is_active", "false", False, lambda x: x is False),
            (BinaryFilterType.IS_FALSE, "is_active", "true", False, lambda x: x is False),
            (BinaryFilterType.IS_FALSE, "is_active", "false", True, lambda x: x is True),
            (BinaryFilterType.IS_NONE, "is_null", "true", None, lambda x: x is None),
            (BinaryFilterType.IS_NONE, "is_null", "false", None, lambda x: x is not None),
            (BinaryFilterType.IS_NOT_NONE, "is_not_null", "true", None, lambda x: x is not None),
        ],
    )
    def test_filter_binary(self, filter_type, alias, param, expected, assert_func):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            is_active = BinaryCriteria(
                field="is_active",
                alias=alias,
                filter_type=filter_type,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={alias: param})
        assert response.status_code == 200
        assert len(response.json()) > 0
        assert all(assert_func(item["is_active"]) for item in response.json())
