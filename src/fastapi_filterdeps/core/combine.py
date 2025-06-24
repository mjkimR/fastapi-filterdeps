import inspect

from sqlalchemy import ColumnElement
from sqlalchemy.orm import DeclarativeBase

from typing import Callable, Any
from fastapi_filterdeps.core.base import SqlFilterCriteriaBase
from fastapi_filterdeps.core.exceptions import ConfigurationError, InvalidValueError


def create_combined_filter_dependency(
    *filter_options: SqlFilterCriteriaBase,
    orm_model: type[DeclarativeBase],
) -> Callable:
    """Dynamically creates a single FastAPI dependency from multiple filter criteria.

    This function allows you to combine multiple filter criteria (subclasses of `SqlFilterCriteriaBase`) into a single FastAPI dependency. This enables clean, DRY, and type-safe filtering logic in your API endpoints, with full OpenAPI documentation support.

    Typical usage:
        1. Compose filter criteria (e.g., `StringCriteria`, `NumericCriteria`) as arguments to `create_combined_filter_dependency`.
        2. Pass the resulting dependency to your FastAPI route using `Depends()`.
        3. Use the resulting list of SQLAlchemy filter conditions in your query.

    Example:
        .. code-block:: python

            from fastapi import FastAPI, Depends
            from sqlalchemy import select
            from fastapi_filterdeps.core.combine import create_combined_filter_dependency
            from fastapi_filterdeps.filters.column import StringCriteria, NumericCriteria, StringMatchType, NumericMatchType
            from myapp.models import User

            app = FastAPI()

            user_filters = create_combined_filter_dependency(
                StringCriteria(
                    field="username",
                    alias="name",
                    match_type=StringMatchType.CONTAINS,
                    case_sensitive=False
                ),
                NumericCriteria(
                    field="karma",
                    alias="min_karma",
                    match_type=NumericMatchType.GREATER_THAN_OR_EQUAL
                ),
                orm_model=User,
            )

            @app.get("/users/")
            async def list_users(filters=Depends(user_filters)):
                query = select(User).where(*filters)
                # ... execute query and return results ...

            # The endpoint can be called like: /users/?name=john&min_karma=100

    Args:
        *filter_options (SqlFilterCriteriaBase): A sequence of filter criteria
            instances that define the available filters for the endpoint.
        orm_model (type[DeclarativeBase]): The SQLAlchemy ORM model class that
            the filters will be applied against.

    Returns:
        A FastAPI dependency. When injected into an endpoint, it
        yields a list of SQLAlchemy `ColumnElement` expressions. This list
        can be directly passed to a SQLAlchemy query's `.where()` clause
        using the `*` splat operator.

    Raises:
        ConfigurationError: If two or more filter criteria are configured with the
            same query parameter alias.
    """
    param_definitions: dict[str, Any] = {}
    filter_builders_with_metadata: list[dict] = []
    used_parameter_aliases = set()
    unique_param_id_counter = 0

    for filter_option in filter_options:
        filter_builder_func = filter_option.build_filter(orm_model)
        filter_metadata = {
            "func": filter_builder_func,
            "params": {},
        }

        signature = inspect.signature(filter_builder_func)
        func_parameters = signature.parameters

        for param_name, param_object in func_parameters.items():
            # Create a unique internal parameter name to avoid conflicts.
            unique_param_name = f"{filter_option.__class__.__name__.lower()}_{param_name}_{unique_param_id_counter}"
            unique_param_id_counter += 1
            if unique_param_name in param_definitions:
                raise ConfigurationError(
                    f"Duplicate parameter name '{param_name}' found."
                )

            # Check for duplicate aliases.
            alias = (
                param_object.default.alias
                if hasattr(param_object.default, "alias")
                else param_object.name
            )
            if alias in used_parameter_aliases:
                raise InvalidValueError(
                    f"Duplicate alias '{alias}' found in filter parameters."
                )
            used_parameter_aliases.add(alias)

            # Store the parameter definition for the signature.
            param_definitions[unique_param_name] = (
                param_object.annotation,
                param_object.default,
            )
            filter_metadata["params"][unique_param_name] = param_object.name
        filter_builders_with_metadata.append(filter_metadata)

    def _combined_filter_dependency(**params):
        collected_filter_conditions = []

        for filter_spec in filter_builders_with_metadata:
            builder = filter_spec["func"]
            param_name_mapping = filter_spec["params"]
            builder_arguments = {}

            for param_key in param_name_mapping.keys():
                if param_key in params:
                    builder_arguments[param_name_mapping[param_key]] = params[param_key]
            collected_filter_conditions.append(builder(**builder_arguments))

        return combine_filter_conditions(*collected_filter_conditions)

    dependency_parameters = []
    for name, (type_hint, query_object_or_default) in param_definitions.items():
        # Create an inspect.Parameter for each collected query parameter.
        # This allows FastAPI to understand the expected parameters, their types, and defaults.
        dependency_parameters.append(
            inspect.Parameter(
                name=name,
                kind=inspect.Parameter.KEYWORD_ONLY,  # Ensures parameters must be passed by keyword,
                default=query_object_or_default,
                annotation=type_hint,
            )
        )

    # Create a new inspect.Signature object from the list of parameters.
    # This represents the complete signature of the function we are dynamically constructing.
    new_signature = inspect.Signature(parameters=dependency_parameters)

    # Assign the dynamically created signature to our core logic function.
    # This is crucial for FastAPI. FastAPI inspects this __signature__ attribute
    # to understand how to call the dependency, validate inputs, and generate
    # accurate OpenAPI (Swagger/Redoc) documentation.
    _combined_filter_dependency.__signature__ = new_signature
    _combined_filter_dependency.__annotations__ = {
        p.name: p.annotation for p in dependency_parameters
    }

    return _combined_filter_dependency


def combine_filter_conditions(*filters) -> list[ColumnElement]:
    """Flattens and merges multiple filter conditions into a single list.

    This utility function is used internally by the dependency created by
    `create_combined_filter_dependency`. It takes the results from individual
    filter builders—which might be `None`, a single SQLAlchemy expression, or a
    list of expressions—and consolidates them into a single, flat list that is
    safe to use with a `.where()` clause.

    Args:
        *filters: A sequence of filter conditions to merge. An item can be
            `None`, a single `ColumnElement`, or a list of `ColumnElement`s.

    Returns:
        A flat list containing all non-None filter
        conditions.
    """
    results = []
    for f in filters:
        if f is None:
            continue
        if isinstance(f, list):
            for item in f:
                if item is not None:
                    results.append(item)
        else:
            results.append(f)
    return results
