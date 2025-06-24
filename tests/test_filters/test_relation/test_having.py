from sqlalchemy import func
from fastapi_filterdeps.filters.relation.having import GroupByHavingCriteria
from fastapi_filterdeps.filtersets import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post


class TestGroupByHavingCriteria(BaseFilterTest):
    def test_filter_avg_value_gt(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            avg_value_gt = GroupByHavingCriteria(
                alias="avg_value_gt",
                value_type=int,
                having_builder=lambda x: func.avg(Post.value) >= x,
                group_by_cols=[Post.category],
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"avg_value_gt": 250})
        assert response.status_code == 200
        assert len(response.json()) == 2
