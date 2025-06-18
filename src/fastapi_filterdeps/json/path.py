from enum import Enum
from typing import Any, Optional, List, Callable

from fastapi import Query
from sqlalchemy import func, ColumnElement
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.exceptions import ConfigurationError


class JsonPathOperation(str, Enum):
    """Specifies the available operations for JSON field filtering.

    Attributes:
        EQUALS: Direct value comparison at the specified path.
        CONTAINS: Checks if a value is contained within a JSON object or array.
        EXISTS: Checks if the specified path exists and is not null.
        ARRAY_ANY: Checks if any element in a JSON array matches the value.
        ARRAY_ALL: Checks if all elements in a JSON array match the value.
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
    """A filter for querying specific paths within a JSON database column.

    This criteria allows for filtering records based on the value at a nested
    path within a JSON or JSONB column. It supports multiple operations like
    equality, containment, and existence checks.

    It can operate in two modes depending on the database backend:
    - Standard Mode (for PostgreSQL/MySQL): Uses native JSON operators.
    - `json_extract` Mode (for SQLite): Uses the `JSON_EXTRACT` function.

    Attributes:
        field (str): The name of the SQLAlchemy model's JSON column to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
        json_path (List[str]): An ordered list of keys representing the path to
            the target value within the JSON object (e.g., `['settings', 'theme']`).
        operation (JsonPathOperation): The comparison operation to perform.
        use_json_extract (bool): If True, uses `func.json_extract` for filtering,
            which is required for SQLite. Defaults to False.
        array_type (bool): If True, indicates that the target value at the
            `json_path` is an array, affecting `CONTAINS`, `ARRAY_ANY`, and
            `ARRAY_ALL` operations. Defaults to False.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Examples:
        # In your FastAPI app, filter a model `BasicModel` with a JSON `detail` field.
        # The JSON could look like: `{"settings": {"theme": "dark"}}`

        from fastapi_filterdeps.base import create_combined_filter_dependency
        from your_models import BasicModel

        item_filters = create_combined_filter_dependency(
            # Create a filter that exposes a `?theme=` query parameter.
            # This is for PostgreSQL or MySQL. For SQLite, set use_json_extract=True.
            JsonPathCriteria(
                field="detail",
                alias="theme",
                json_path=["settings", "theme"],
                operation=JsonPathOperation.EQUALS,
                use_json_extract=False
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
        use_json_extract: bool = False,
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
            use_json_extract (bool): If True, use the `JSON_EXTRACT` function,
                which is necessary for SQLite compatibility. Defaults to False.
            array_type (bool): Set to True if the target field is an array to
                ensure correct operation for array-specific functions.
            description (Optional[str]): A custom description for the OpenAPI
                documentation. If None, a default is generated.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        self.field = field
        self.alias = alias
        self.path = json_path
        self.operation = operation
        self.use_json_extract = use_json_extract
        self.array_type = array_type
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter."""
        return (
            f"Filter on '{'.'.join(self.path)}' using {self.operation.value} operation."
        )

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for filtering by a JSON path.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class that
                the filter will be applied to.

        Returns:
            Callable: A FastAPI dependency that, when resolved, produces an
                SQLAlchemy filter expression (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the `orm_model`.
            InvalidColumnTypeError: If the specified `field` is not a JSON type column.
            NotImplementedError: If an unsupported operation is used with
                `use_json_extract=True`.
            ConfigurationError: If an array-specific operation is used on a field that
                is not marked as `array_type=True`.
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
            if value is None and self.operation != JsonPathOperation.EXISTS:
                return None

            orm_field = getattr(orm_model, self.field)

            if self.use_json_extract:
                # SQLite-compatible path using json_extract
                json_path_str = "$." + ".".join(self.path)
                extracted = func.json_extract(orm_field, json_path_str)

                if self.operation == JsonPathOperation.EQUALS:
                    return extracted == str(value)
                elif self.operation == JsonPathOperation.EXISTS:
                    return extracted.isnot(None)
                elif self.operation == JsonPathOperation.CONTAINS:
                    if self.array_type:
                        raise NotImplementedError(
                            "CONTAINS on arrays is not supported when use_json_extract=True."
                        )
                    return extracted.like(f"%{value}%")
                elif self.operation in (
                    JsonPathOperation.ARRAY_ANY,
                    JsonPathOperation.ARRAY_ALL,
                ):
                    raise NotImplementedError(
                        f"{self.operation.value} is not supported when use_json_extract=True."
                    )
            else:
                # Standard path traversal for PostgreSQL, MySQL
                target = orm_field
                for path_part in self.path:
                    target = target[path_part]

                if self.operation == JsonPathOperation.EQUALS:
                    return target.as_string() == str(value)
                elif self.operation == JsonPathOperation.EXISTS:
                    return target.isnot(None)
                elif self.operation == JsonPathOperation.CONTAINS:
                    # For arrays, `contains` expects a list of items to find.
                    return target.contains([value] if self.array_type else value)
                elif self.operation == JsonPathOperation.ARRAY_ANY:
                    if not self.array_type:
                        raise ConfigurationError(
                            "ARRAY_ANY is only valid for array types."
                        )
                    return target.any_(value)
                elif self.operation == JsonPathOperation.ARRAY_ALL:
                    if not self.array_type:
                        raise ConfigurationError(
                            "ARRAY_ALL is only valid for array types."
                        )
                    return target.all_(value)

            return None

        return filter_dependency
