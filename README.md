# FastAPI-Filterdeps

`FastAPI-Filterdeps` leverages FastAPI's dependency injection system to seamlessly transform API query parameters into flexible SQLAlchemy filter conditions. Keep your API endpoints clean and your filtering logic organized and reusable.

## Core Features

* **Declarative & Reusable**: Define filters declaratively with `FilterSet`, cleanly separating query parameter handling from your application layers and eliminating repetitive boilerplate.

* **Essential Filters Included:** Comes with a suite of built-in filters for most common use cases, such as `StringCriteria`, `NumericCriteria`, `BinaryCriteria`, and `TimeCriteria`.

* **Create Custom Filters:** Easily build your own filters and plug them into the `FilterSet`.

<!-- ## Installation

```bash
pip install fastapi-filterdeps
``` -->

## Quick Example

Here’s how to quickly add filtering to your FastAPI application.

### 1\. Define your SQLAlchemy Model

```python
# models.py
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String, DateTime
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    view_count: Mapped[int] = mapped_column(Integer, default=0)
    is_published: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

### 2\. Create a `FilterSet`

Group your filters by creating a `FilterSet`. Each attribute defines a query parameter and its filtering logic.

```python
# filters.py
from fastapi_filterdeps import FilterSet
from fastapi_filterdeps.filters.column.string import StringCriteria, StringMatchType
from fastapi_filterdeps.filters.column.numeric import NumericCriteria, NumericFilterType
from fastapi_filterdeps.filters.column.binary import BinaryCriteria
from .models import Post

class PostFilterSet(FilterSet):
    # GET /posts?title=hello
    title = StringCriteria(
        field="title",
        match_type=StringMatchType.CONTAINS,
    )

    # GET /posts?min_views=100
    min_views = NumericCriteria(
        field="view_count",
        operator=NumericFilterType.GTE,
        numeric_type=int
    )

    # GET /posts?is_published=true
    is_published = BinaryCriteria(
        field="is_published"
    )

    class Meta:
        orm_model = Post
```

### 3\. Use it in your API Endpoint

Inject the `FilterSet` as a dependency in your FastAPI route. The dependency will provide the SQLAlchemy filter conditions directly to your query's `.where()` clause.

```python
# main.py
from typing import List
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select

# Assuming you have these files from the steps above
from .models import Post
from .filters import PostFilterSet
from .database import get_db, engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

@app.get("/posts", response_model=List[PostReadSchema]) # Assuming a Pydantic schema PostReadSchema
async def list_posts(
    db: Session = Depends(get_db),
    filters: list = Depends(PostFilterSet),
):
    """
    List posts with filters.
    - title: Search for text in the post title.
    - min_views: Filter for posts with at least a minimum number of views.
    - is_published: Filter for published (true) or unpublished (false) posts.
    - order_by: Sort by 'view_count' or 'created_at'.
    """
    query = (
        select(Post)
        .where(*filters)
        .order_by(*order_by)
    )
    result = db.execute(query).scalars().all()
    return result

```

Now you can run your API and query it:

  * `GET /posts?title=FastAPI&min_views=1000`
  * `GET /posts?is_published=true&order_by=-view_count`


## Composing Reusable Filters

You can create abstract `FilterSet` classes to share common filters across different models. To do this, simply add `abstract = True` to your base `FilterSet`. These abstract sets don't need a `Meta` class.

### 1\. Define Abstract Base FilterSets

Create reusable filter collections. For example, you might have common filters for creation timestamps or titles that you want to apply to multiple models.

```python
# filters.py
from fastapi_filterdeps import FilterSet
from fastapi_filterdeps.filters.column.time import TimeCriteria, TimeMatchType
from fastapi_filterdeps.filters.column.string import StringCriteria, StringMatchType

class CreatedAtFilterSet(FilterSet):
    """A reusable filter set for timestamp fields."""
    abstract = True  # Mark this FilterSet as a reusable building block

    created_at_start = TimeCriteria(
        field="created_at",
        match_type=TimeMatchType.GTE,
    )
    created_at_end = TimeCriteria(
        field="created_at",
        match_type=TimeMatchType.LTE,
    )

class TitleFilterSet(FilterSet):
    """A reusable filter set for title fields."""
    abstract = True # This can also be inherited by other FilterSets

    title = StringCriteria(
        field="title",
        match_type=StringMatchType.CONTAINS,
    )
```

### 2\. Inherit and Create a Concrete FilterSet

Now, create a concrete `FilterSet` for a specific model by inheriting from your abstract sets. This concrete class **must** define the `Meta` class with the `orm_model`.

```python
# post_filters.py
from .filters import CreatedAtFilterSet, TitleFilterSet
from .models import Post
from fastapi_filterdeps.filters.column.binary import BinaryCriteria

class PostFilterSet(CreatedAtFilterSet, TitleFilterSet): # Inherit from base sets
    """A concrete FilterSet for the Post model."""
    
    # Add filters specific to Post
    is_published = BinaryCriteria(
        field="is_published"
    )

    class Meta:
        # This concrete class links the filters to a specific model
        orm_model = Post
```

### 3\. Use in an Endpoint

The `PostFilterSet` now contains all filters from `CreatedAtFilterSet`, `TitleFilterSet`, and its own `is_published` filter. You can use it just like any other `FilterSet`.

```python
# main.py

# ... (imports and app setup)

@app.get("/posts")
async def list_posts(
    db: Session = Depends(get_db),
    filters: list = Depends(PostFilterSet) # Use the composed filter set
):
    query = select(Post).where(*filters)
    result = db.execute(query).scalars().all()
    return result
```

You can now filter posts with combined query parameters:

  * `GET /posts?title=news&created_at_start=2025-01-01T00:00:00`
  * `GET /posts?is_published=true&created_at_end=2025-07-03T23:59:59`


## Creating Custom Filters

`FastAPI-Filterdeps` offers two primary ways to create custom filters, giving you the flexibility to choose the best approach for your needs.

### 1\. (Recommended) Using the `@filter_for` Decorator

For most simple custom filters, the `@filter_for` decorator is the recommended approach. It allows you to quickly turn a function into a filter criterion, keeping your code concise and readable.

#### **Define a Filter Function**

Create a function that accepts the `orm_model` and the `value` from the query parameter, and returns a SQLAlchemy filter condition. Use the `@filter_for` decorator to define its API behavior.

```python
# examples/blog/api/posts.py
from fastapi_filterdeps import filter_for

@filter_for(
    field="view_count",
    alias="is_popular",
    description="Filter for popular posts (view_count >= 10)",
    bound_type=bool
)
def custom_filter(orm_model, value):
    """Custom filter logic example."""
    if value is None:
        return None
    return orm_model.view_count >= 10 if value else orm_model.view_count < 10

# You can now add `custom_filter` to any FilterSet.
```

### 2\. The Equivalent `SqlFilterCriteriaBase` Class

The decorator is a convenient shortcut. To gain a deeper understanding and unlock more advanced customization, you can implement the same logic by inheriting from `SqlFilterCriteriaBase`. This is the most fundamental **'building block'** for creating new filters.

This approach gives you full control over the filter's dependencies using FastAPI's `Depends` system. The `build_filter` method's sole responsibility is to **return a dependency function**. FastAPI then resolves this function for each request. The code below is functionally equivalent to the decorated function above.

```python
# The class-based equivalent using the core building block
from fastapi import Query
from fastapi_filterdeps.core.base import SqlFilterCriteriaBase
from typing import Optional, Any, Callable
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.elements import ColumnElement

class PopularPostFilter(SqlFilterCriteriaBase):
    """
    A custom filter built directly on SqlFilterCriteriaBase for maximum control.
    """
    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """
        This method constructs and returns the actual dependency function
        that FastAPI will resolve.
        """

        # This inner function IS the dependency.
        def filter_dependency(
            # Define the FastAPI query parameter explicitly.
            is_popular: Optional[bool] = Query(
                default=None,
                alias="is_popular",
                description="Filter for popular posts (view_count >= 10)",
            ),
        ) -> Optional[ColumnElement]:
            """
            This logic runs for each request, applying a filter based on
            the 'is_popular' query parameter.
            """
            if is_popular is None:
                return None  # No filter applied if the parameter is not provided

            # The `orm_model` from the outer scope is used here.
            return orm_model.view_count >= 10 if is_popular else orm_model.view_count < 10

        return filter_dependency
```

### 3\. Use in a `FilterSet`

Whether you use the decorator or the full class, you add it to your `FilterSet` in the same way.

```python
# examples/blog/api/posts.py
from .models import Post
from .filters import custom_filter # Import the decorated function
# from .filters import PopularPostFilter # Or import the custom class

class PostFilterSet(FilterSet):
    # ... other filters

    # Using the decorated function
    is_popular = custom_filter

    # Or, using the equivalent class instance
    # is_popular = PopularPostFilter()

    class Meta:
        orm_model = Post
```

Now, your endpoint accepts a new boolean parameter that is fully controlled by your custom logic.

  * `GET /posts?is_popular=true`

## Examples

For more advanced and detailed use cases, please check out the complete runnable examples in the `/examples` directory.


## License

This project is licensed under the MIT License.