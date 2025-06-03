from typing import Optional
from fastapi import Query

from fastapi_filterdeps.base import SqlFilterCriteriaBase, create_combined_filter_dependency
from .conftest import TestModel, generate_app_client


class NameFilter(SqlFilterCriteriaBase):
    def build_filter(self, orm_model: type[TestModel]):
        def filter_by_name(
                name: Optional[str] = Query(None, alias="name", description="Filter by name")
        ):
            if name:
                return orm_model.name == name
            return None

        return filter_by_name


class CategoryFilter(SqlFilterCriteriaBase):
    def build_filter(self, orm_model: type[TestModel]):
        def filter_by_category(
                category: Optional[str] = Query(None, alias="category", description="Filter by category")
        ):
            if category:
                return orm_model.category == category
            return None

        return filter_by_category


async def test_single_filter(db_session):
    """Test single filter"""
    combined_filter = create_combined_filter_dependency(
        NameFilter(),
        orm_model=TestModel
    )
    client = generate_app_client(combined_filter, db_session)

    # Search for Item 1
    response = client.get("/test-items?name=Item%201")
    assert response.status_code == 200
    result = response.json()

    assert len(result) == 1
    assert result[0]["name"] == "Item 1"


async def test_multiple_filters(db_session):
    """Test multiple filters"""

    # Combine name and category filters
    combined_filter = create_combined_filter_dependency(
        NameFilter(),
        CategoryFilter(),
        orm_model=TestModel
    )
    client = generate_app_client(combined_filter, db_session)

    # Search for Item 2 in category A
    response = client.get("/test-items?name=Item%202&category=A")
    assert response.status_code == 200
    result = response.json()

    assert len(result) == 1
    assert result[0]["name"] == "Item 2"
    assert result[0]["category"] == "A"


async def test_filter_no_results(db_session):
    """Test case with no results"""

    combined_filter = create_combined_filter_dependency(
        NameFilter(),
        CategoryFilter(),
        orm_model=TestModel
    )
    client = generate_app_client(combined_filter, db_session)

    # Search with non-existent name
    response = client.get("/test-items?name=Non-existent%20Item")
    assert response.status_code == 200
    result = response.json()

    assert len(result) == 0


async def test_filter_partial_params(db_session):
    """Test using partial parameters"""

    combined_filter = create_combined_filter_dependency(
        NameFilter(),
        CategoryFilter(),
        orm_model=TestModel
    )
    client = generate_app_client(combined_filter, db_session)

    # Search by category only
    response = client.get("/test-items?category=A")
    assert response.status_code == 200
    result = response.json()

    assert len(result) == 2
    assert all(item["category"] == "A" for item in result)


async def test_filter_with_empty_params(db_session):
    """Test with empty filter parameters"""
    combined_filter = create_combined_filter_dependency(
        NameFilter(),
        CategoryFilter(),
        orm_model=TestModel
    )
    client = generate_app_client(combined_filter, db_session)

    # Request without any parameters should return all items
    response = client.get("/test-items")
    assert response.status_code == 200
    result = response.json()

    assert len(result) == 4  # Should return all test items


async def test_filter_case_sensitivity(db_session):
    """Test case sensitivity in filters"""
    combined_filter = create_combined_filter_dependency(
        NameFilter(),
        CategoryFilter(),
        orm_model=TestModel
    )
    client = generate_app_client(combined_filter, db_session)

    # Test with different case
    response = client.get("/test-items?category=a")  # lowercase 'a' instead of 'A'
    assert response.status_code == 200
    result = response.json()

    assert len(result) == 0  # Should return no results due to case mismatch


async def test_filter_invalid_params(db_session):
    """Test with invalid parameter values"""
    combined_filter = create_combined_filter_dependency(
        NameFilter(),
        CategoryFilter(),
        orm_model=TestModel
    )
    client = generate_app_client(combined_filter, db_session)

    # Test with special characters in parameters
    response = client.get("/test-items?name=Item%201%20%21@%23")
    assert response.status_code == 200
    result = response.json()

    assert len(result) == 0  # Should handle special characters gracefully
