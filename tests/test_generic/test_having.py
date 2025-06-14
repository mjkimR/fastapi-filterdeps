from sqlalchemy import func
from fastapi_filterdeps.base import create_combined_filter_dependency
from fastapi_filterdeps.generic.having import GroupByHavingCriteria
from tests.conftest import BaseFilterTest
from tests.models import BasicModel


class TestGroupByHavingCriteria(BaseFilterTest):
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
        response = self.client.get("/test-items", params={"avg_value_gt": 250})
        assert response.status_code == 200
        assert len(response.json()) == 2
