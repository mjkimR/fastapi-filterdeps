from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.join.exists import JoinExistsCriteria
from fastapi_filterdeps.generic.binary import BinaryCriteria, BinaryFilterType
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, String, ForeignKey
from tests.conftest import BaseFilterTest, Base, TestModel


class Comment(Base):
    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content: Mapped[str] = mapped_column(String(200))
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_items.id"))
    is_approved: Mapped[bool] = mapped_column(default=True)


class TestJoinExistsCriteria(BaseFilterTest):
    def build_test_data(self):
        """Build test data with posts and related comments."""
        posts = [
            TestModel(
                name="Post 1",
                category="A",
                value=100,
                is_active=True,
            ),
            TestModel(
                name="Post 2",
                category="B",
                value=200,
                is_active=True,
            ),
            TestModel(
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

        return posts

    def test_inner_join_exists(self):
        """Test filtering posts that have approved comments using inner join."""
        filter_deps = create_combined_filter_dependency(
            JoinExistsCriteria(
                join_criteria=[
                    BinaryCriteria(
                        field="is_approved",
                        alias="has_approved_comments",
                        filter_type=BinaryFilterType.IS_TRUE,
                    )
                ],
                join_condition=TestModel.id == Comment.post_id,
                join_model=Comment,
                is_outer=False,
            ),
            orm_model=TestModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"has_approved_comments": "true"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Should return Post 1 and Post 2
        assert {item["name"] for item in data} == {"Post 1", "Post 2"}

    def test_outer_join_exists(self):
        """Test filtering posts with left outer join to include posts without comments."""
        filter_deps = create_combined_filter_dependency(
            JoinExistsCriteria(
                join_criteria=[
                    BinaryCriteria(
                        field="is_approved",
                        alias="has_approved_comments",
                        filter_type=BinaryFilterType.IS_TRUE,
                    )
                ],
                join_condition=TestModel.id == Comment.post_id,
                join_model=Comment,
                is_outer=True,
                exclude=True,  # Exclude posts with approved comments
            ),
            orm_model=TestModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get(
            "/test-items", params={"has_approved_comments": "true"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Should return only Post 3
        assert data[0]["name"] == "Post 3"

    def test_no_criteria_returns_none(self):
        """Test that when no join criteria are provided, the filter returns None."""
        filter_deps = create_combined_filter_dependency(
            JoinExistsCriteria(
                join_criteria=[],  # Empty criteria list
                join_condition=TestModel.id == Comment.post_id,
                join_model=Comment,
            ),
            orm_model=TestModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # Should return all posts since no filtering is applied
