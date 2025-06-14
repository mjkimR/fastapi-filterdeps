from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.join.exists import JoinExistsCriteria
from tests.conftest import BaseFilterTest

from tests.models import BasicModel, Comment


class TestJoinExistsCriteria(BaseFilterTest):
    def test_include_unrelated_false(self):
        """Test filtering posts that have approved comments and exclude posts without comments"""
        filter_deps = create_combined_filter_dependency(
            JoinExistsCriteria(
                filter_condition=[Comment.is_approved == True],
                alias="has_approved_comments",
                join_model=Comment,
                join_condition=BasicModel.id == Comment.post_id,
                include_unrelated=False,
            ),
            orm_model=BasicModel,
        )

        self.setup_filter(filter_deps=filter_deps)
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
        """Test filtering posts that have approved comments and include posts without comments"""
        filter_deps = create_combined_filter_dependency(
            JoinExistsCriteria(
                filter_condition=[Comment.is_approved == True],
                alias="has_approved_comments",
                join_condition=BasicModel.id == Comment.post_id,
                join_model=Comment,
                include_unrelated=True,
            ),
            orm_model=BasicModel,
        )

        self.setup_filter(filter_deps=filter_deps)
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
