from sqlalchemy import func
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.having import GroupByHavingCriteria
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


class TestGroupByHavingCriteria(BaseFilterTest):
    def build_test_data(self):
        """Build test data with values outside the 10-20 range."""
        return [
            BasicModel(
                name="Item 1",
                category="A",
                value=100,
                count=5,
                is_active=True,
                status="active",
                detail={"settings": {"theme": "light"}},
            ),
            BasicModel(
                name="Item 2",
                category="A",
                value=200,
                count=25,
                is_active=False,
                status="inactive",
                detail={"settings": {"theme": "dark"}},
            ),
            BasicModel(
                name="Item 3",
                category="B",
                value=130,
                count=15,
                is_active=None,
                status="pending",
                detail={"settings": {"theme": "custom"}},
            ),
        ]

    def test_filter_avg_value_gt(self):
        filter_deps = create_combined_filter_dependency(
            GroupByHavingCriteria(
                alias="avg_value_gt",
                value_type=int,
                having_builder=lambda x: func.avg(BasicModel.value) >= x,
                group_by_cols=[BasicModel.category],
            ),
            orm_model=BasicModel,
        )
        self.setup_filter(filter_deps=filter_deps)
        response = self.client.get("/test-items", params={"avg_value_gt": 150})
        assert response.status_code == 200
        assert len(response.json()) == 2
