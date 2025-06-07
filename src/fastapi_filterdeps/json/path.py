from enum import Enum
from typing import Any, Optional, List

from fastapi import Query
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class JsonPathOperation(str, Enum):
    """Available operations for JSON field filtering.

    EQUALS: Direct value comparison
    CONTAINS: Check if the value is contained (for objects/arrays)
    EXISTS: Check if the path exists and is not null
    ARRAY_ANY: Check if any array element matches (for array fields)
    ARRAY_ALL: Check if all array elements match (for array fields)
    """

    EQUALS = "eq"
    CONTAINS = "contains"
    EXISTS = "exists"
    ARRAY_ANY = "any"
    ARRAY_ALL = "all"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        return {op.value for op in cls}


class JsonPathCriteria(SqlFilterCriteriaBase):
    """Filter criteria for JSON field paths.

    Provides filtering capabilities for specific paths within JSON fields.
    The path is specified as a list of strings representing the traversal path
    in the JSON structure.

    Examples:
        # PostgreSQL/MySQL style filter
        theme_filter = JsonPathCriteria(
            "preferences",
            ["settings", "theme"],
            JsonPathOperation.EQUALS,
        )

        # SQLite style filter
        tags_filter = JsonPathCriteria(
            "metadata",
            ["tags"],
            JsonPathOperation.EQUALS,
            use_json_extract=True,
        )
    """

    def __init__(
        self,
        field: str,
        alias: str,
        json_path: List[str],
        operation: JsonPathOperation,
        use_json_extract: bool = False,
        array_type: bool = False,
    ):
        """Initialize JSON path filter criteria.

        Args:
            json_field: Name of the JSON field in the database model
            json_path: List of strings representing the JSON path (e.g. ["settings", "theme"])
            operation: Type of operation to perform on the field
            use_json_extract: Whether to use JSON_EXTRACT function (True for SQLite)
            array_type: Flag indicating if the target field is an array
        """
        self.field = field
        self.alias = alias
        self.path = json_path
        self.operation = operation
        self.use_json_extract = use_json_extract
        self.array_type = array_type

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for filtering by JSON path.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to create filter conditions for.

        Returns:
            callable: A FastAPI dependency function that returns a list of SQLAlchemy filter conditions
                for filtering by JSON path.
        """
        self._validate_field_exists(orm_model, self.field)

        def filter_dependency(
            value: Optional[Any] = Query(
                None,
                alias=self.alias,
                description=f"Filter value for {'.'.join(self.path)} using {self.operation.value} operation",
            )
        ):
            """Generate JSON path filter condition.

            Note:
                When use_json_extract=True (typically for SQLite), the following operations
                are not supported and will raise NotImplementedError:
                - CONTAINS operation for array fields
                - ARRAY_ANY operation
                - ARRAY_ALL operation

            Args:
                value: Value to filter by (optional for EXISTS operation)

            Returns:
                Optional SQLAlchemy filter condition

            Raises:
                ValueError: If array operations are used on non-array fields
                NotImplementedError: If an unsupported operation is used with use_json_extract=True
            """
            if value is None:
                return None

            field = getattr(orm_model, self.field)

            if self.use_json_extract:
                json_path = "$." + ".".join(self.path)
                extracted = func.json_extract(field, json_path)

                if self.operation == JsonPathOperation.EQUALS:
                    return extracted == str(value)
                elif self.operation == JsonPathOperation.EXISTS:
                    return extracted.isnot(None)
                elif self.operation == JsonPathOperation.CONTAINS:
                    if self.array_type:
                        raise NotImplementedError("CONTAINS operation is not supported for JSON path filtering with use_json_extract=True")
                    return extracted.like(f"%{value}%")
                elif self.operation == JsonPathOperation.ARRAY_ANY:
                    raise NotImplementedError("ARRAY_ANY operation is not supported for JSON path filtering with use_json_extract=True")
                elif self.operation == JsonPathOperation.ARRAY_ALL:
                    raise NotImplementedError("ARRAY_ALL operation is not supported for JSON path filtering with use_json_extract=True")
            else:
                target = field
                for path_part in self.path:
                    target = target[path_part]

                if self.operation == JsonPathOperation.EQUALS:
                    return target.as_string() == str(value)
                elif self.operation == JsonPathOperation.EXISTS:
                    return target.isnot(None)
                elif self.operation == JsonPathOperation.CONTAINS:
                    if self.array_type:
                        return target.contains([value])
                    return target.contains(value)
                elif self.operation == JsonPathOperation.ARRAY_ANY:
                    if not self.array_type:
                        raise ValueError(
                            "ARRAY_ANY operation is only valid for array fields"
                        )
                    return target.any_(value)
                elif self.operation == JsonPathOperation.ARRAY_ALL:
                    if not self.array_type:
                        raise ValueError(
                            "ARRAY_ALL operation is only valid for array fields"
                        )
                    return target.all_(value)

            return None

        return filter_dependency
