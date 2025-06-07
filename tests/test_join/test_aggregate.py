from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.join.aggregation import JoinAggregateCriteria
from sqlalchemy import func
from tests.conftest import BaseFilterTest, Base, TestModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Integer, ForeignKey


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    score: Mapped[int] = mapped_column(Integer)
    post_id: Mapped[int] = mapped_column(Integer, ForeignKey("test_items.id"))


class TestJoinAggregateCriteria(BaseFilterTest):
    def build_test_data(self):
        """Build test data with posts and related votes."""
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

        # Now add votes
        votes = [
            Vote(score=5, post_id=posts[0].id),
            Vote(score=4, post_id=posts[0].id),
            Vote(score=3, post_id=posts[1].id),
            Vote(score=5, post_id=posts[1].id),
            Vote(score=5, post_id=posts[1].id),
        ]
        self.session.add_all(votes)

        return posts

    def test_aggregate_count(self):
        """Test filtering posts by vote count."""
        filter_deps = create_combined_filter_dependency(
            JoinAggregateCriteria(
                join_condition=TestModel.id == Vote.post_id,
                join_model=Vote,
                having_expression=func.count(Vote.id) > 2,
            ),
            orm_model=TestModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Should return only Post 2
        assert data[0]["name"] == "Post 2"

    def test_aggregate_avg(self):
        """Test filtering posts by average vote score."""
        filter_deps = create_combined_filter_dependency(
            JoinAggregateCriteria(
                join_condition=TestModel.id == Vote.post_id,
                join_model=Vote,
                having_expression=func.avg(Vote.score) >= 4.5,
            ),
            orm_model=TestModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Should return Post 1
        assert data[0]["name"] == "Post 1"

    def test_outer_join_aggregate(self):
        """Test filtering with outer join to include posts without votes."""
        filter_deps = create_combined_filter_dependency(
            JoinAggregateCriteria(
                join_condition=TestModel.id == Vote.post_id,
                join_model=Vote,
                having_expression=func.count(Vote.id) == 0,
                is_outer=True,
            ),
            orm_model=TestModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Should return Post 3
        assert data[0]["name"] == "Post 3"
