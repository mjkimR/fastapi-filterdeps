import abc
import inspect
from typing import Optional, Type, Any, Union, Callable, Sequence


from sqlalchemy import Column, ColumnElement, Sequence
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase


class SqlFilterCriteriaBase:
    """Base class for filter options.

    All filter option classes should inherit from this abstract class
    and implement the build_filter method.
    """

    @abc.abstractmethod
    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[Union[ColumnElement, list[ColumnElement]]]]:
        """Build a filter dependency for a given ORM model.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to create filter conditions for.

        Returns:
            callable: A FastAPI dependency function that returns SQLAlchemy filter conditions.
        """
        raise NotImplementedError

    def _validate_field_exists(
        self, orm_model: type[DeclarativeBase], field: str
    ) -> None:
        """Validate that a field exists on the model.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to check.
            field (str): The field name to validate.

        Raises:
            AttributeError: If the field doesn't exist on the model.
        """
        if not hasattr(orm_model, field):
            raise AttributeError(
                f"Field '{field}' does not exist on model '{orm_model.__name__}'"
            )

    def _validate_enum_value(
        self, value: str, valid_values: set[str], field_name: str
    ) -> None:
        """Validate that an enum value is valid.

        Args:
            value (str): The value to validate.
            valid_values (set[str]): Set of valid values.
            field_name (str): Name of the field for error messages.

        Raises:
            ValueError: If the value is not in valid_values.
        """
        if value not in valid_values:
            raise ValueError(
                f"Invalid {field_name}: {value}. "
                f"Valid values are: {', '.join(sorted(valid_values))}"
            )

    def _validate_model_has_primary_keys(
        self, orm_model: type[DeclarativeBase]
    ) -> None:
        """Validate that a model has primary keys.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to check.

        Raises:
            ValueError: If the model doesn't have primary keys.
        """
        try:
            pk_columns = self._get_primary_keys(orm_model)
            if not pk_columns:
                raise ValueError(
                    f"Model '{orm_model.__name__}' must have primary key(s)"
                )
        except Exception as e:
            raise ValueError(f"Failed to get primary keys: {str(e)}")

    def _get_default_description(self) -> str:
        """Get default description for the filter.

        This method should be overridden by subclasses to provide specific descriptions.
        The base implementation provides a generic description.

        Returns:
            str: Default description based on the filter configuration
        """
        return f"Filter by field '{self.field}'"

    @classmethod
    def _get_primary_keys(cls, model: type[DeclarativeBase]) -> Sequence[Column]:
        """Get primary key columns for the given model.

        Args:
            model: SQLAlchemy model class

        Returns:
            Sequence of primary key columns

        Raises:
            ValueError: If model inspection fails or no primary keys are found
        """
        inspector_result = sqlalchemy.inspect(model)
        if inspector_result is None:
            raise ValueError("Model inspection failed.")
        primary_key_columns: Sequence[Column] = inspector_result.mapper.primary_key
        if not primary_key_columns or len(primary_key_columns) == 0:
            raise ValueError(f"No primary key found for model {model.__name__}")
        return primary_key_columns


def create_combined_filter_dependency(
    *filter_options: SqlFilterCriteriaBase,
    orm_model: Type[DeclarativeBase],
):
    """Dynamically creates filter parameters and returns a FastAPI dependency.

    Creates a FastAPI dependency that processes multiple filter options and combines
    their conditions based on the provided filter options.

    Args:
        *filter_options (SqlFilterCriteriaBase): One or more filter option instances.
        orm_model (Type[DeclarativeBase]): The SQLAlchemy model class to create filter conditions for.

    Returns:
        callable: A FastAPI dependency function that returns combined SQLAlchemy filter conditions.

    Raises:
        ValueError: When duplicate parameter names or aliases are found in the filter options.

    Example:
        build_filter_conditions(FilterName(), FilterCreator(), orm_model=Memo)
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
                raise ValueError(f"Duplicate parameter name '{param_name}' found.")

            # Check for duplicate aliases.
            alias = (
                param_object.default.alias
                if hasattr(param_object.default, "alias")
                else param_object.name
            )
            if alias in used_parameter_aliases:
                raise ValueError(
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


def combine_filter_conditions(*filters):
    """Merges multiple filter conditions into a single list.

    Args:
        *filters: Filter conditions to merge. Can be None, individual conditions,
                 or lists of conditions.

    Returns:
        list: A flat list of all non-None filter conditions.
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
