from fastapi_filterdeps.filters.relation.exists import JoinExistsCriteria
from fastapi_filterdeps import FilterSet
from tests.conftest import BaseFilterTest
from tests.models import Post, Comment


class TestJoinExistsCriteria(BaseFilterTest):
    def test_include_unrelated_false(self):
        """Test filtering item that have approved comments and exclude item without comments"""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            has_approved_comments = JoinExistsCriteria(
                filter_condition=[Comment.is_approved == True],
                alias="has_approved_comments",
                join_model=Comment,
                join_condition=Post.id == Comment.post_id,
                include_unrelated=False,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get(
            "/test-items", params={"has_approved_comments": "true"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        response = self.client.get(
            "/test-items", params={"has_approved_comments": "false"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_include_unrelated_true(self):
        """Test filtering item that have approved comments and include item without comments"""

        class TestFilerSet(FilterSet):
            class Meta:
                orm_model = Post

            has_approved_comments = JoinExistsCriteria(
                filter_condition=[Comment.is_approved == True],
                alias="has_approved_comments",
                join_condition=Post.id == Comment.post_id,
                join_model=Comment,
                include_unrelated=True,
            )

        self.setup_filter(filter_deps=TestFilerSet)
        response = self.client.get(
            "/test-items", params={"has_approved_comments": "true"}
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

        response = self.client.get(
            "/test-items", params={"has_approved_comments": "false"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
