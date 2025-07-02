from sqlalchemy import func
from fastapi_filterdeps.filters.relation.having import GroupByHavingCriteria
from fastapi_filterdeps.filters.relation.nested import JoinNestedFilterCriteria
from fastapi_filterdeps.filters.column.binary import BinaryCriteria, BinaryFilterType
from fastapi_filterdeps import FilterSet
from tests.conftest import BaseFilterTest, Post
from tests.models import Post, Comment, Vote


class TestJoinNestedFilterCriteria(BaseFilterTest):
    def test_include_unrelated_false(self):
        """Test filtering item that have approved comments and exclude item without comments"""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            is_approved = JoinNestedFilterCriteria(
                filter_criteria=[
                    BinaryCriteria(
                        field="is_approved",
                        alias="is_approved",
                        filter_type=BinaryFilterType.IS_TRUE,
                    )
                ],
                join_condition=Post.id == Comment.post_id,
                join_model=Comment,
                include_unrelated=False,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"is_approved": "true"})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_nested_aggregate_filter(self):
        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            avg_value_gt = JoinNestedFilterCriteria(
                filter_criteria=[
                    GroupByHavingCriteria(
                        alias="avg_value_gt",
                        value_type=float,
                        having_builder=lambda x: func.avg(Vote.score) >= x,
                        group_by_cols=[Vote.post_id],
                    )
                ],
                join_condition=Post.id == Vote.post_id,
                join_model=Vote,
                include_unrelated=False,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get("/test-items", params={"avg_value_gt": 4.5})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
