from enum import Enum
from typing import Any, Optional, List, Callable

from fastapi import Query
from sqlalchemy import ColumnElement
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.json.strategy import JsonStrategy


class JsonPathOperation(str, Enum):
    """Specifies the available operations for JSON field filtering.

    These operations define how a value at a given JSON path is compared.

    Attributes:
        EQUALS: Direct value comparison at the specified path (`==`).
        CONTAINS: Checks if a value is contained within a JSON object or array (`@>`).
            This operation is primarily supported by `JsonOperatorStrategy`.
        EXISTS: Checks if the specified path exists and its value is not JSON `null`.
        ARRAY_ANY: Checks if any element in a JSON array matches the value (`?|`).
            Requires `array_type=True` and is supported by `JsonOperatorStrategy`.
        ARRAY_ALL: Checks if all elements in a JSON array match the value (`?&`).
            Requires `array_type=True` and is supported by `JsonOperatorStrategy`.
    """

    EQUALS = "eq"
    CONTAINS = "contains"
    EXISTS = "exists"
    ARRAY_ANY = "any"
    ARRAY_ALL = "all"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Returns a set of all available operator values."""
        return {op.value for op in cls}


class JsonPathCriteria(SqlFilterCriteriaBase):
    """A filter for querying specific paths within a JSON/JSONB database column.

    This criteria allows for filtering records based on the value at a nested
    path within a JSON column. It supports multiple operations like equality,
    containment, and existence checks.

    The actual SQL generation is delegated to a `JsonStrategy` object, allowing
    this criteria to be compatible with different database backends (e.g.,
    PostgreSQL with `JsonOperatorStrategy` or SQLite with `JsonExtractStrategy`).

    Attributes:
        field (str): The name of the SQLAlchemy model's JSON column to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        json_path (List[str]): An ordered list of keys representing the path to
            the target value within the JSON object (e.g., `['settings', 'theme']`).
        operation (JsonPathOperation): The comparison operation to perform.
        strategy (JsonStrategy): The database-specific strategy for building the
            SQL filter expression.
        array_type (bool): If True, indicates that the target value at the
            `json_path` is an array. This is required for `CONTAINS`,
            `ARRAY_ANY`, and `ARRAY_ALL` operations to function correctly.
            Defaults to False.
        description (Optional[str]): A custom description for the OpenAPI documentation.
        **query_params: Additional keyword arguments to pass to FastAPI's Query.

    Examples:
        # In your FastAPI app, filter a `BasicModel` with a JSON `detail` field.
        # The JSON could look like: `{"settings": {"theme": "dark"}}`

        from fastapi_filterdeps.base import create_combined_filter_dependency
        from fastapi_filterdeps.json.strategy import JsonOperatorStrategy
        from your_models import BasicModel

        item_filters = create_combined_filter_dependency(
            # Create a filter that exposes a `?theme=` query parameter.
            JsonPathCriteria(
                field="detail",
                alias="theme",
                json_path=["settings", "theme"],
                operation=JsonPathOperation.EQUALS,
                strategy=JsonOperatorStrategy(), # Choose the appropriate strategy
            ),
            orm_model=BasicModel,
        )

        # In your endpoint:
        # A request to `/items?theme=dark` will filter for items where the
        # nested theme is "dark".
        @app.get("/items")
        def list_items(filters=Depends(item_filters)):
            query = select(BasicModel).where(*filters)
            # ... execute query ...
    """

    def __init__(
        self,
        field: str,
        alias: str,
        json_path: List[str],
        operation: JsonPathOperation,
        strategy: JsonStrategy,
        array_type: bool = False,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the JsonPathCriteria.

        Args:
            field (str): The name of the JSON field in the SQLAlchemy model.
            alias (str): The alias for the query parameter in the API.
            json_path (List[str]): The list of keys defining the path to the
                target value (e.g., `["settings", "theme"]`).
            operation (JsonPathOperation): The type of comparison to perform.
            strategy (JsonStrategy): The database-specific strategy instance for
                building the filter expression.
            array_type (bool): Set to True if the target at the path is an array.
                This affects array-specific operations. Defaults to False.
            description (Optional[str]): A custom description for the OpenAPI
                documentation. If None, a default is generated.
            **query_params: Additional keyword arguments to pass to FastAPI's Query.
        """
        self.field = field
        self.alias = alias
        self.path = json_path
        self.operation = operation
        self.strategy = strategy
        self.array_type = array_type
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter."""
        path_str = ".".join(self.path)
        return f"Filter on JSON path '{path_str}' using the '{self.operation.value}' operation."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for filtering by a JSON path.

        This method validates the model and configuration, then returns a
        dependency function. When called by FastAPI, this function will use the
        provided `strategy` to construct the appropriate SQLAlchemy filter
        expression based on the user's query parameters.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class that
                the filter will be applied to.

        Returns:
            Callable: A FastAPI dependency that, when resolved, produces an
                SQLAlchemy filter expression (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the `orm_model`.
            InvalidColumnTypeError: If the specified `field` is not a JSON type column.
            UnsupportedOperationError: If the chosen strategy does not support the
                requested operation.
            ConfigurationError: If an array-specific operation is used on a field
                not marked as `array_type=True`.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_column_type(orm_model, self.field, sqlalchemy.JSON)

        def filter_dependency(
            value: Optional[Any] = Query(
                None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[ColumnElement]:
            """Generates the JSON path filter condition."""
            # For EXISTS operation, the value is implicit (we just check for presence).
            # For all other operations, a value must be provided.
            if value is None and self.operation != JsonPathOperation.EXISTS:
                return None

            model_field = getattr(orm_model, self.field)
            return self.strategy.build_path_expression(
                field=model_field,
                path=self.path,
                operation=self.operation.value,
                value=value,
                array_type=self.array_type,
            )

        return filter_dependency
