"""
Main entry point for declarative filtering in FastAPI + SQLAlchemy APIs.

This module provides the `FilterSet` base class, which allows you to define composable, reusable, and type-safe filter logic for SQLAlchemy models in FastAPI applications.

A `FilterSet` is a declarative collection of filter criteria (subclasses of `SqlFilterCriteriaBase`) that can be directly injected as a FastAPI dependency. This enables clean, DRY, and testable filtering in your API endpoints, with full OpenAPI documentation support.

Typical usage:
    1. Subclass `FilterSet` and declare filter criteria as class attributes.
    2. For reusable filter sets, set `abstract = True` and inherit from them.
    3. For concrete filter sets, define an inner `Meta` class with an `orm_model` attribute.
    4. Use your `FilterSet` as a dependency in FastAPI routes.

Example:
    .. code-block:: python

        from fastapi_filterdeps.filtersets import FilterSet
        from fastapi_filterdeps.filters.column.string import StringCriteria, StringMatchType
        from myapp.models import Post

        class PostFilterSet(FilterSet):
            title = StringCriteria(
                field="title",
                alias="title",
                match_type=StringMatchType.CONTAINS,
            )
            class Meta:
                orm_model = Post

        @app.get("/posts")
        async def list_posts(filters=Depends(PostFilterSet)):
            query = select(Post).where(*filters)
            ...

See also:
    - `examples/blog/api/posts.py` and `examples/blog/api/filters.py` for real-world usage.
    - Filter criteria classes in `fastapi_filterdeps.filters.column.*` and `fastapi_filterdeps.filters.relation.*`.
"""

import inspect
from typing import Any, Callable, Dict

from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.core.base import SqlFilterCriteriaBase
from fastapi_filterdeps.core.combine import create_combined_filter_dependency
from fastapi_filterdeps.core.exceptions import ConfigurationError, FilterDependencyError


class FilterSetMeta(type):
    """
    Metaclass for `FilterSet` (not used directly).

    Collects all filter criteria defined as class attributes and assembles them into a unified FastAPI dependency. Enforces the presence of a `Meta.orm_model` for concrete filter sets, and supports abstract base filter sets for composition.

    Attributes:
        _filters (list[SqlFilterCriteriaBase]):
            The list of filter criteria for this filter set, including inherited ones.
        _dependency_func (Callable):
            The FastAPI dependency function that returns a list of SQLAlchemy filter conditions.

    Raises:
        ConfigurationError: If a concrete FilterSet is missing a Meta.orm_model definition.
    """

    def __new__(mcs, name: str, bases: tuple, dct: Dict[str, Any]):
        cls = super().__new__(mcs, name, bases, dct)

        try:
            current_filters = []
            for attr_name, attr_value in dct.items():
                if isinstance(attr_value, SqlFilterCriteriaBase):
                    if hasattr(attr_value, "alias") and attr_value.alias is None:
                        attr_value.alias = attr_name
                    current_filters.append(attr_value)

            filters = list(current_filters)
            for base in bases:
                if hasattr(base, "_filters"):
                    filters.extend(base._filters)
            cls._filters = filters

            if dct.get("abstract", False):
                return cls

            if not hasattr(cls, "Meta") or not hasattr(cls.Meta, "orm_model"):
                raise ConfigurationError(
                    f"Concrete FilterSet must have an inner 'Meta' class with an 'orm_model' attribute defined,"
                    " or it must be declared as abstract (using `abstract = True` option in Abstract FilterSet class)."
                )
            orm_model = cls.Meta.orm_model

            if not cls._filters:

                def no_op_dependency() -> list:
                    return []

                dependency_func = no_op_dependency
            else:
                dependency_func = create_combined_filter_dependency(
                    *cls._filters, orm_model=orm_model
                )

            cls._dependency_func = dependency_func
            cls.__signature__ = inspect.signature(dependency_func)
        except FilterDependencyError as e:
            # Add context about which FilterSet raised the error
            raise type(e)(f"{type(e).__name__} in '{name}': {str(e)}") from None
        except NotImplementedError as e:
            # Add context about which FilterSet raised the error and mention it's likely due to missing implementation
            raise NotImplementedError(
                f"Implementation error in '{name}' FilterSet: {str(e)}. "
                "This is likely because a required method or attribute is not implemented."
            ) from None

        return cls

    def __call__(cls, *args: Any, **kwargs: Any) -> list[Any]:
        """
        Makes the class itself callable for FastAPI's dependency injection.

        Returns:
            list[Any]: The list of SQLAlchemy filter conditions generated by the dependency.

        Raises:
            FilterDependencyError: Enriched with FilterSet name context if raised during execution.
            NotImplementedError: Enriched with FilterSet name context if a required implementation is missing.
        """
        try:
            if not hasattr(cls, "Meta") or not hasattr(cls.Meta, "orm_model"):
                raise ConfigurationError(
                    f"Cannot instantiate abstract FilterSet '{cls.__name__}'. "
                    "Use a concrete subclass with a defined Meta.orm_model."
                )
            return cls._dependency_func(*args, **kwargs)
        except FilterDependencyError as e:
            # Add context about which FilterSet raised the error
            raise type(e)(f"{type(e).__name__} in '{cls.__name__}': {str(e)}") from None
        except NotImplementedError as e:
            # Add context about which FilterSet raised the error
            raise NotImplementedError(
                f"Implementation error in '{cls.__name__}' FilterSet: {str(e)}. "
                "This is likely because a required method or attribute is not implemented."
            ) from None


class FilterSet(metaclass=FilterSetMeta):
    """
    Main API for building composable filter logic in FastAPI + SQLAlchemy projects.

    Subclass this and declare filter criteria as class attributes. For reusable filter sets, set `abstract = True` and inherit from them. Concrete filter sets must define an inner `Meta` class with an `orm_model` attribute specifying the SQLAlchemy model.

    Example:

        .. code-block:: python

            class MyFilterSet(FilterSet):
                my_field = StringCriteria(...)
                class Meta:
                    orm_model = MyModel

    Attributes:
        _dependency_func (Callable): The FastAPI dependency function for this filter set.
    """

    abstract: bool = True
    _dependency_func: Callable

    class Meta:
        orm_model: type[DeclarativeBase]
