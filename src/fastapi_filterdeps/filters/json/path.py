from enum import Enum
from typing import Any, Optional

import sqlalchemy

from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase
from fastapi_filterdeps.filters.json.strategy import JsonStrategy


class JsonPathOperation(str, Enum):
    """Specifies the available operations for JSON field filtering.

    These operations define how a value at a given JSON path is compared.

    * EQUALS: Direct value comparison at the specified path (`==`).

    * CONTAINS: Checks if a value is contained within a JSON object or array (`@>`). This operation is primarily supported by `JsonOperatorStrategy`.

    * EXISTS: Checks if the specified path exists and its value is not JSON `null`.

    * ARRAY_ANY: Checks if any element in a JSON array matches the value (`?|`). Requires `array_type=True` and is supported by `JsonOperatorStrategy`.

    * ARRAY_ALL: Checks if all elements in a JSON array match the value (`?&`). Requires `array_type=True` and is supported by `JsonOperatorStrategy`.
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


class JsonPathCriteria(SimpleFilterCriteriaBase):
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
        json_path (list[str]): An ordered list of keys representing the path to
            the target value within the JSON object (e.g., `['settings', 'theme']`).
        operation (JsonPathOperation): The comparison operation to perform.
        strategy (JsonStrategy): The database-specific strategy for building the
            SQL filter expression.
        array_type (bool): If True, indicates that the target value at the JSON path is an array.
        description (Optional[str]): A custom description for the OpenAPI documentation.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        .. code-block:: python

            from fastapi_filterdeps.filtersets import FilterSet
            from fastapi_filterdeps.filters.json.path import JsonPathCriteria, JsonPathOperation
            from fastapi_filterdeps.filters.json.strategy import JsonOperatorStrategy
            from myapp.models import Item

            class ItemFilterSet(FilterSet):
                theme = JsonPathCriteria(
                    field="data",
                    alias="theme",
                    json_path=["settings", "theme"],
                    operation=JsonPathOperation.EQUALS,
                    strategy=JsonOperatorStrategy(),
                    description="Filter items by theme in settings."
                )
                class Meta:
                    orm_model = Item

            # GET /items?theme=dark
            # will filter for items where data->settings->theme == 'dark'.
    """

    def __init__(
        self,
        field: str,
        alias: str,
        json_path: list[str],
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
        super().__init__(field, alias, description, Any, **query_params)
        self.path = json_path
        self.operation = operation
        self.strategy = strategy
        self.array_type = array_type

    def _get_default_description(self) -> str:
        """Generates a default description for the filter."""
        path_str = ".".join(self.path)
        return f"Filter on JSON path '{path_str}' using the '{self.operation.value}' operation."

    def _validation_logic(self, orm_model):
        self._validate_column_type(orm_model, self.field, sqlalchemy.JSON)

    def _filter_logic(self, orm_model, value):
        if value is None:
            return None
        model_field = getattr(orm_model, self.field)
        return self.strategy.build_path_expression(
            field=model_field,
            path=self.path,
            operation=self.operation.value,
            value=value,
            array_type=self.array_type,
        )
