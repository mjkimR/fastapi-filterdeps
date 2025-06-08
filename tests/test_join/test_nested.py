from sqlalchemy import func
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.having import GroupByHavingCriteria
from fastapi_filterdeps.join.nested import JoinNestedFilterCriteria
from fastapi_filterdeps.generic.binary import BinaryCriteria, BinaryFilterType
from tests.conftest import BaseFilterTest, BasicModel
from tests.models import BasicModel, Comment, Vote


class TestJoinNestedFilterCriteria(BaseFilterTest):
    def build_test_data(self):
        """Build test data with posts and related comments."""
        posts = [
            BasicModel(
                name="Post 1",
                category="A",
                value=100,
                is_active=True,
            ),
            BasicModel(
                name="Post 2",
                category="B",
                value=200,
                is_active=True,
            ),
            BasicModel(
                name="Post 3",
                category="C",
                value=300,
                is_active=True,
            ),
        ]

        # Add posts first to get their IDs
        self.session.add_all(posts)
        self.session.flush()

        # Now add comments
        comments = [
            Comment(
                content="Comment 1 on Post 1", post_id=posts[0].id, is_approved=True
            ),
            Comment(
                content="Comment 2 on Post 1", post_id=posts[0].id, is_approved=False
            ),
            Comment(
                content="Comment 1 on Post 2", post_id=posts[1].id, is_approved=True
            ),
        ]
        self.session.add_all(comments)

        votes = [
            Vote(score=5, post_id=posts[0].id),
            Vote(score=4, post_id=posts[0].id),
            Vote(score=3, post_id=posts[1].id),
            Vote(score=5, post_id=posts[1].id),
            Vote(score=5, post_id=posts[1].id),
        ]
        self.session.add_all(votes)

        return posts

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
        assert len(data) == 2  # Should return Post 1 and Post 2
        assert {item["name"] for item in data} == {"Post 1", "Post 2"}

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
        assert len(data) == 1  # Should return Post 1
        assert data[0]["name"] == "Post 1"
