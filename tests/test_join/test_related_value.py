from datetime import datetime, UTC
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.join.related_value import JoinRelatedValueCriteria
from tests.conftest import BaseFilterTest
from tests.models import BasicModel, Review


class TestJoinRelatedValueCriteria(BaseFilterTest):
    def build_test_data(self):
        """Build test data with posts and related reviews."""
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

        # Now add reviews with different timestamps
        base_time = datetime(2024, 1, 1, tzinfo=UTC)
        reviews = [
            Review(rating=5, post_id=posts[0].id, created_at=base_time),
            Review(rating=3, post_id=posts[0].id, created_at=base_time.replace(hour=1)),
            Review(rating=4, post_id=posts[1].id, created_at=base_time),
            Review(rating=5, post_id=posts[1].id, created_at=base_time.replace(hour=2)),
            Review(rating=2, post_id=posts[1].id, created_at=base_time.replace(hour=3)),
        ]
        self.session.add_all(reviews)

        return posts

    def test_latest_review_rating(self):
        """Test filtering posts by latest review rating."""
        filter_deps = create_combined_filter_dependency(
            JoinRelatedValueCriteria(
                join_condition=BasicModel.id == Review.post_id,
                join_model=Review,
                target_column=Review.rating,
                value_expression=Review.rating < 3,
                order_by=Review.created_at.desc(),
            ),
            orm_model=BasicModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Should return Post 2
        assert data[0]["name"] == "Post 2"

    def test_first_review_high_rating(self):
        """Test filtering posts by first review with high rating."""
        filter_deps = create_combined_filter_dependency(
            JoinRelatedValueCriteria(
                join_condition=BasicModel.id == Review.post_id,
                join_model=Review,
                target_column=Review.rating,
                value_expression=Review.rating >= 4,
                order_by=Review.created_at.asc(),
            ),
            orm_model=BasicModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2  # Should return Post 1 and Post 2
        assert {item["name"] for item in data} == {"Post 1", "Post 2"}

    def test_outer_join_no_reviews(self):
        """Test filtering with outer join to find posts without reviews."""
        filter_deps = create_combined_filter_dependency(
            JoinRelatedValueCriteria(
                join_condition=BasicModel.id == Review.post_id,
                join_model=Review,
                target_column=Review.id,
                value_expression=Review.id.is_(None),
                order_by=Review.created_at.asc(),
                is_outer=True,
            ),
            orm_model=BasicModel,
        )

        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1  # Should return Post 3
        assert data[0]["name"] == "Post 3"
