import abc
import inspect
from typing import Optional, Type, Any, Union, Callable, Sequence, TYPE_CHECKING

from sqlalchemy import Column, ColumnElement
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase
from fastapi import Query

from fastapi_filterdeps.exceptions import (
    ConfigurationError,
    InvalidFieldError,
    InvalidRelationError,
    InvalidColumnTypeError,
    MissingPrimaryKeyError,
    InvalidValueError,
)

if TYPE_CHECKING:
    from fastapi_filterdeps.combinators.invert import InvertCriteria
    from fastapi_filterdeps.combinators.combine import CombineCriteria


class SqlFilterCriteriaBase:
    """Abstract base class for creating declarative SQL filter criteria.

    This class serves as the foundation for all filter criteria. Subclasses
    must implement the `build_filter` method, which defines the specific
    filtering logic.

    Instances of `SqlFilterCriteriaBase` subclasses are stateless "building blocks"
    that describe how a particular field should be filtered based on API query
    parameters. They do not perform any database operations themselves.

    These building blocks are assembled into a single FastAPI dependency using the
    `create_combined_filter_dependency` factory function. This separation of
    concerns creates a pure, reusable, and testable filter layer.

    Filter criteria can be combined using logical operators: `&` (AND),
    `|` (OR), and `~` (NOT).

    Example:
        This is a conceptual example. `MyCustomFilter` would be a subclass.
        See specific criteria classes like `StringCriteria` for concrete usage::

            class MyCustomFilter(SqlFilterCriteriaBase):
                # ... implementation ...
                def build_filter(self, orm_model):
                    # ... returns a dependency callable ...
                    pass

            my_filter1 = MyCustomFilter(field="name", alias="name_filter")
            my_filter2 = MyCustomFilter(field="status", alias="status_filter")

            # Combine filters and create the final dependency
            CombinedFilter = create_combined_filter_dependency(
                my_filter1,
                ~my_filter2,  # Example of using the NOT operator
                orm_model=MyModel
            )

            @app.get("/items")
            def get_items(filters: list = Depends(CombinedFilter)):
                query = select(MyModel).where(*filters)
                # ... execute query and return results ...
    """

    @abc.abstractmethod
    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[Union[ColumnElement, list[ColumnElement]]]]:
        """Creates a FastAPI dependency that generates a filter condition.

        This abstract method must be implemented by all subclasses. The
        implementation should not return a filter condition directly. Instead,
        it must return a callable (a function) that FastAPI can use as a
        dependency. FastAPI will resolve this dependency for each incoming
        request, calling it with the appropriate query parameters to generate
        the live SQLAlchemy filter expression.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to
                which this filter will be applied.

        Returns:
            A FastAPI dependency. When called, it returns a SQLAlchemy
            filter condition (`ColumnElement`), a list of conditions, or
            `None` if the filter is not active for the current request.
        """
        raise NotImplementedError

    def _validate_field_exists(
        self, orm_model: type[DeclarativeBase], field: str
    ) -> None:
        """Validates that a field exists on the specified ORM model.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy ORM model to inspect.
            field (str): The name of the field to check for existence.

        Raises:
            InvalidFieldError: If the field does not exist on the model.
        """
        if not hasattr(orm_model, field):
            inspector = sqlalchemy.inspect(orm_model)
            available_fields = [c.name for c in inspector.columns]
            raise InvalidFieldError(
                f"Field '{field}' does not exist on model '{orm_model.__name__}'. "
                f"Available fields are: {', '.join(available_fields)}"
            )

    def _validate_relation_exists(
        self, orm_model: type[DeclarativeBase], relation: str
    ) -> None:
        """Validates that a relationship exists on the specified ORM model.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy ORM model to inspect.
            relation (str): The name of the relationship to check for existence.

        Raises:
            InvalidRelationError: If the relationship does not exist on the model.
        """
        if not hasattr(orm_model, relation) or not (
            inspect.isclass(getattr(orm_model, relation))
            or isinstance(getattr(orm_model, relation), property)
        ):
            inspector = sqlalchemy.inspect(orm_model)
            available_relations = [r.key for r in inspector.relationships]
            raise InvalidRelationError(
                f"Relation '{relation}' does not exist on model '{orm_model.__name__}'. "
                f"Available relations are: {', '.join(available_relations)}"
            )

    def _validate_column_type(
        self, orm_model: type[DeclarativeBase], field: str, expected_type: Type[Any]
    ) -> None:
        """Validates that a field's column type matches the expected type.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy ORM model to inspect.
            field (str): The name of the field to check.
            expected_type (Type[Any]): The expected SQLAlchemy column type (e.g., sqlalchemy.JSON).

        Raises:
            InvalidColumnTypeError: If the field's column type does not match the expected type.
        """
        self._validate_field_exists(orm_model, field)
        column = getattr(orm_model, field).expression
        if not isinstance(column.type, expected_type):
            raise InvalidColumnTypeError(
                f"Field '{field}' on model '{orm_model.__name__}' is of type "
                f"'{column.type.__class__.__name__}', but '{expected_type.__name__}' was expected."
            )

    def _validate_enum_value(
        self, value: str, valid_values: set[str], field_name: str
    ) -> None:
        """Validates that a given value is present in a set of allowed values.

        Args:
            value (str): The input value to validate.
            valid_values (set[str]): A set containing the valid string values.
            field_name (str): The conceptual name of the field being validated,
                used for generating a helpful error message.

        Raises:
            InvalidValueError: If `value` is not a member of `valid_values`.
        """
        if value not in valid_values:
            raise InvalidValueError(
                f"Invalid {field_name}: {value}. "
                f"Valid values are: {', '.join(sorted(valid_values))}"
            )

    def _validate_model_has_primary_keys(
        self, orm_model: type[DeclarativeBase]
    ) -> None:
        """Validates that the given SQLAlchemy model has at least one primary key.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy ORM model to inspect.

        Raises:
            MissingPrimaryKeyError: If the model does not have any primary key columns
                defined.
        """
        try:
            pk_columns = self.get_primary_keys(orm_model)
            if not pk_columns:
                raise MissingPrimaryKeyError(
                    f"Model '{orm_model.__name__}' must have primary key(s) for this filter type."
                )
        except InvalidFieldError:
            raise MissingPrimaryKeyError(
                f"Failed to get primary keys for model '{orm_model.__name__}'."
            )

    def _get_default_description(self) -> str:
        """Generates a default description for the OpenAPI documentation.

        This method can be overridden by subclasses to provide a more specific
        and user-friendly description for the filter's query parameter in
        the auto-generated API docs.

        Returns:
            A default description string for the filter.
        """
        return f"Filter by field '{self.field}'"

    @classmethod
    def get_primary_keys(cls, model: type[DeclarativeBase]) -> Sequence[Column]:
        """Retrieves the primary key columns for a given SQLAlchemy model.

        Args:
            model (type[DeclarativeBase]): The SQLAlchemy model class to inspect.

        Returns:
            A sequence of SQLAlchemy `Column` objects that constitute the
            primary key of the model.

        Raises:
            InvalidFieldError: If the model cannot be inspected or has no
                primary key columns.
        """
        inspector_result = sqlalchemy.inspect(model)
        if inspector_result is None:
            raise InvalidFieldError("Model inspection failed.")
        primary_key_columns: Sequence[Column] = inspector_result.mapper.primary_key
        if not primary_key_columns or len(primary_key_columns) == 0:
            raise InvalidFieldError(f"No primary key found for model {model.__name__}")
        return primary_key_columns

    def __invert__(self) -> "InvertCriteria":
        """Creates a negated representation of this filter criterion (NOT).

        This allows for inverting a filter's logic using the `~` operator.

        Usage:
            `~StringCriteria(field="name", alias="name_not_contains")`

        Returns:
            An `InvertCriteria` instance that wraps this filter.
        """
        from fastapi_filterdeps.combinators.invert import InvertCriteria

        return InvertCriteria(self)

    def __and__(self, other: "SqlFilterCriteriaBase") -> "CombineCriteria":
        """Combines this filter with another using a logical AND.

        This allows for chaining filters together using the `&` operator.

        Usage:
            `StringCriteria(...) & NumericCriteria(...)`

        Args:
            other (SqlFilterCriteriaBase): The other filter criterion to combine
                with this one.

        Returns:
            A `CombineCriteria` instance representing the logical AND.
        """
        from fastapi_filterdeps.combinators.combine import (
            CombineCriteria,
            CombineOperator,
        )

        if isinstance(other, CombineCriteria) and other.operator == CombineOperator.AND:
            return other.__and__(self)  # Chain it correctly
        return CombineCriteria(CombineOperator.AND, self, other)

    def __or__(self, other: "SqlFilterCriteriaBase") -> "CombineCriteria":
        """Combines this filter with another using a logical OR.

        This allows for chaining filters together using the `|` operator.

        Usage:
            `StringCriteria(...) | OtherStringCriteria(...)`

        Args:
            other (SqlFilterCriteriaBase): The other filter criterion to combine
                with this one.

        Returns:
            A `CombineCriteria` instance representing the logical OR.
        """
        from fastapi_filterdeps.combinators.combine import (
            CombineCriteria,
            CombineOperator,
        )

        if isinstance(other, CombineCriteria) and other.operator == CombineOperator.OR:
            return other.__or__(self)  # Chain it correctly
        return CombineCriteria(CombineOperator.OR, self, other)


class SimpleFilterCriteriaBase(SqlFilterCriteriaBase):
    def __init__(
        self,
        field: str,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        bound_type: Optional[type] = None,
        **query_params: Any,
    ):
        self.field = field
        self.alias = alias
        self.description = description
        self.bound_type = bound_type
        self.query_params = query_params

    def _get_default_description(self) -> str:
        return f"Filter by field '{self.field}'"

    @abc.abstractmethod
    def _filter_logic(self, orm_model, value):
        raise NotImplementedError

    def _validation_logic(self, orm_model):
        pass

    def build_filter(
        self, orm_model: DeclarativeBase
    ) -> Callable[..., ColumnElement | list[ColumnElement] | None]:
        self._validation_logic(orm_model)
        if self.alias is None:
            raise ConfigurationError("")
        if self.bound_type is None:
            raise ConfigurationError("")
        description = self.description or self._get_default_description()

        self._validate_field_exists(orm_model, self.field)

        def filter_dependency(
            value: Optional[self.bound_type] = Query(  # type: ignore
                default=None,
                alias=self.alias,
                description=description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            if value is None:
                return None
            return self._filter_logic(orm_model=orm_model, value=value)

        return filter_dependency
