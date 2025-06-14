from sqlalchemy import func
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.having import GroupByHavingCriteria
from fastapi_filterdeps.join.nested import JoinNestedFilterCriteria
from fastapi_filterdeps.generic.binary import BinaryCriteria, BinaryFilterType
from tests.conftest import BaseFilterTest, BasicModel
from tests.models import BasicModel, Comment, Vote


class TestJoinNestedFilterCriteria(BaseFilterTest):
    def test_include_unrelated_false(self):
        """Test filtering posts that have approved comments and exclude posts without comments"""
        filter_deps = create_combined_filter_dependency(
            JoinNestedFilterCriteria(
                filter_criteria=[
                    BinaryCriteria(
                        field="is_approved",
                        alias="is_approved",
                        filter_type=BinaryFilterType.IS_TRUE,
                    )
                ],
                join_condition=BasicModel.id == Comment.post_id,
                join_model=Comment,
                include_unrelated=False,
            ),
            orm_model=BasicModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"is_approved": "true"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_nested_aggregate_filter(self):
        filter_deps = create_combined_filter_dependency(
            JoinNestedFilterCriteria(
                filter_criteria=[
                    GroupByHavingCriteria(
                        alias="avg_value_gt",
                        value_type=float,
                        having_builder=lambda x: func.avg(Vote.score) >= x,
                        group_by_cols=[Vote.post_id],
                    )
                ],
                join_condition=BasicModel.id == Vote.post_id,
                join_model=Vote,
                include_unrelated=False,
            ),
            orm_model=BasicModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"avg_value_gt": 4.5})
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
