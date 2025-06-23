from typing import Callable, Dict, Any, Optional
from fastapi_filterdeps.base import (
    SqlFilterCriteriaBase,
    create_combined_filter_dependency,
)
from fastapi_filterdeps.exceptions import ConfigurationError


class FilterSet:
    """
    A base class for creating a collection of declarative filter criteria.

    This class provides a structured and reusable way to group related filters
    for a specific ORM model. By defining filter criteria as class attributes,
    developers can create a self-documenting and organized set of filters
    that can be easily converted into a single FastAPI dependency.

    The alias for each query parameter is automatically inferred from the
    attribute name, reducing boilerplate.

    Attributes:
        _filters (Dict[str, SqlFilterCriteriaBase]): A dictionary storing the
            filter criteria instances, keyed by their attribute names.
        _dependency (Optional[Callable]): A cached dependency function to avoid
            re-creation on every call.

    Raises:
        ConfigurationError: If the inner `Meta` class or the `orm_model`
            attribute within it is not defined.

    Examples:
        A basic example of creating and using a `FilterSet` for a `Post` model.

        .. code-block:: python

            from fastapi import FastAPI, Depends
            from sqlalchemy import select
            from sqlalchemy.orm import Session

            # Assume these are defined in your project
            from my_models import Post
            from my_database import get_db

            from fastapi_filterdeps.contrib.filterset import FilterSet
            from fastapi_filterdeps.generic.string import StringCriteria, StringMatchType
            from fastapi_filterdeps.generic.numeric import NumericCriteria, NumericFilterType

            # 1. Define your FilterSet by inheriting from the base class.
            class PostFilterSet(FilterSet):
                # The attribute 'title_contains' becomes the query parameter.
                # e.g., /posts?title_contains=fastapi
                title_contains = StringCriteria(
                    field="title",
                    match_type=StringMatchType.CONTAINS
                )

                # The attribute 'min_views' becomes the query parameter.
                # e.g., /posts?min_views=100
                min_views = NumericCriteria(
                    field="view_count",
                    operator=NumericFilterType.GTE,
                    numeric_type=int
                )

                class Meta:
                    # Link the FilterSet to your SQLAlchemy model.
                    orm_model = Post

            app = FastAPI()

            # 2. Use the FilterSet as a dependency in your endpoint.
            @app.get("/posts")
            def list_posts(
                db: Session = Depends(get_db),
                filters: list = Depends(PostFilterSet.as_dependency())
            ):
                # The 'filters' variable is a list of SQLAlchemy filter conditions.
                query = select(Post).where(*filters)
                results = db.execute(query).scalars().all()
                return results

    """

    _filters: Dict[str, SqlFilterCriteriaBase] = {}
    _dependency: Optional[Callable] = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """
        Initializes the subclass, collecting and configuring filter criteria.

        This method is called automatically when a new class inherits from
        `FilterSet`. It scans the subclass for attributes that are instances of
        `SqlFilterCriteriaBase`, sets their query parameter alias based on the
        attribute name, and stores them for later use.
        """
        super().__init_subclass__(**kwargs)

        cls._filters = {
            attr_name: attr_value
            for attr_name, attr_value in cls.__dict__.items()
            if isinstance(attr_value, SqlFilterCriteriaBase)
        }

        for attr_name, filter_instance in cls._filters.items():
            if hasattr(filter_instance, "alias") and filter_instance.alias is None:
                filter_instance.alias = attr_name

    @classmethod
    def as_dependency(cls) -> Callable[..., list[SqlFilterCriteriaBase]]:
        """
        Creates and returns a single, unified FastAPI dependency.

        This class method is the main entry point for using the FilterSet in an
        endpoint. It gathers all collected filter criteria and the specified ORM
        model from the `Meta` class, then uses the core
        `create_combined_filter_dependency` function to build the final dependency.

        The generated dependency is cached to ensure it's created only once.

        Returns:
            A callable FastAPI dependency that can be used with `Depends`.

        Raises:
            ConfigurationError: If the `Meta` class or `orm_model` is not defined.
        """
        if cls._dependency:
            return cls._dependency

        if not hasattr(cls, "Meta") or not hasattr(cls.Meta, "orm_model"):
            raise ConfigurationError(
                f"'{cls.__name__}' must have an inner 'Meta' class with an 'orm_model' attribute defined."
            )

        orm_model = cls.Meta.orm_model
        filter_instances = list(cls._filters.values())

        if not filter_instances:

            def no_op_dependency() -> list:
                return []

            cls._dependency = no_op_dependency
            return cls._dependency

        cls._dependency = create_combined_filter_dependency(
            *filter_instances, orm_model=orm_model
        )
        return cls._dependency
