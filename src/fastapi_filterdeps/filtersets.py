import inspect
from typing import Optional, Type, Any, Callable

from sqlalchemy import ColumnElement
from sqlalchemy.orm import DeclarativeBase

from typing import Callable, Dict, Any, Optional
from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.exceptions import ConfigurationError, InvalidValueError


def create_combined_filter_dependency(
    *filter_options: SqlFilterCriteriaBase,
    orm_model: Type[DeclarativeBase],
) -> Callable:
    """Dynamically creates a single FastAPI dependency from multiple filter criteria.

    This factory function is the primary user-facing interface of the library.
    It takes multiple `SqlFilterCriteriaBase` instances (like `StringCriteria`,
    `NumericCriteria`, etc.), inspects the query parameters required by each,
    and constructs a single, unified dependency function.

    This resulting function can be used directly with `fastapi.Depends` in an
    endpoint. FastAPI will use its signature to handle request validation,
    OpenAPI documentation generation, and dependency injection. When the endpoint
    is called, the function executes and returns a list of active SQLAlchemy
    filter conditions.

    Args:
        *filter_options (SqlFilterCriteriaBase): A sequence of filter criteria
            instances that define the available filters for the endpoint.
        orm_model (Type[DeclarativeBase]): The SQLAlchemy ORM model class that
            the filters will be applied against.

    Returns:
        A FastAPI dependency. When injected into an endpoint, it
        yields a list of SQLAlchemy `ColumnElement` expressions. This list
        can be directly passed to a SQLAlchemy query's `.where()` clause
        using the `*` splat operator.

    Raises:
        ConfigurationError: If two or more filter criteria are configured with the
            same query parameter alias.

    Examples:
        ```python
        # In your FastAPI application (e.g., main.py)

        from fastapi import FastAPI, Depends
        from sqlalchemy import select
        from fastapi_filterdeps import (
            create_combined_filter_dependency,
            StringCriteria,
            NumericCriteria,
            StringMatchType,
            NumericMatchType
        )
        # Assume `User` is a SQLAlchemy ORM model

        app = FastAPI()

        # 1. Create the combined filter dependency
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

        # 2. Use the dependency in an endpoint
        @app.get("/users/")
        async def list_users(filters: list = Depends(user_filters)):
            # `filters` will be a list like `[User.username.ilike('%search%')]`
            query = select(User).where(*filters)
            # ... execute query and return results ...
            return {"message": "Query would be executed with applied filters."}

        # The endpoint can be called like: /users/?name=john&min_karma=100
        ```
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
