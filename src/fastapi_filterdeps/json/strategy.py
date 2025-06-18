import abc
from typing import Any, List
from sqlalchemy import ColumnElement, func

from fastapi_filterdeps.exceptions import ConfigurationError, UnsupportedOperationError


class JsonStrategy(abc.ABC):
    """
    Abstract base class for JSON strategies.
    Defines the interface for creating JSON-based filter expressions
    based on a specific operational logic (e.g., using a function vs. an operator).
    """

    @abc.abstractmethod
    def build_path_expression(
        self,
        field: ColumnElement,
        path: List[str],
        operation: str,
        value: Any,
        array_type: bool,
    ) -> ColumnElement:
        """Builds a filter expression for a JSON path operation."""
        raise NotImplementedError

    @abc.abstractmethod
    def build_tag_expression(
        self,
        field: ColumnElement,
        key: str,
        value: Any,
    ) -> ColumnElement:
        """Builds a filter expression for a JSON tag operation."""
        raise NotImplementedError


class JsonOperatorStrategy(JsonStrategy):
    """
    Strategy for databases that support native JSON path operators (e.g., `->`, `->>`).
    Suitable for PostgreSQL, recent MySQL versions, etc.
    """

    def build_path_expression(
        self, field, path, operation, value, array_type
    ) -> ColumnElement:
        target = field
        for part in path:
            target = target[part]

        if operation == "eq":
            return target.as_string() == str(value)
        if operation == "exists":
            return target.isnot(None)
        if operation == "contains":
            return target.contains([value] if array_type else value)
        if operation == "any":
            if not array_type:
                raise ConfigurationError("ARRAY_ANY is only for array fields")
            return target.any_(value)
        if operation == "all":
            if not array_type:
                raise ConfigurationError("ARRAY_ALL is only for array fields")
            return target.all_(value)
        raise UnsupportedOperationError(
            f"Operation '{operation}' not supported by {self.__class__.__name__}"
        )

    def build_tag_expression(self, field, key, value) -> ColumnElement:
        if isinstance(value, bool):
            return field["tags"][key].isnot(None)
        else:
            return field["tags"][key].as_string() == str(value)


class JsonExtractStrategy(JsonStrategy):
    """
    Strategy for databases that rely on a `json_extract` function.
    Suitable for SQLite, older MySQL versions, etc.
    """

    def build_path_expression(
        self, field, path, operation, value, array_type
    ) -> ColumnElement:
        json_path_str = "$.{}".format(".".join(path))
        extracted = func.json_extract(field, json_path_str)

        if operation == "eq":
            return extracted == str(value)
        if operation == "exists":
            return extracted.isnot(None)
        if operation == "contains":
            if array_type:
                raise UnsupportedOperationError(
                    "CONTAINS on arrays is not well-supported with json_extract in this context."
                )
            return extracted.like(f"%{value}%")
        if operation in ("any", "all"):
            raise UnsupportedOperationError(
                f"Operation '{operation}' not supported by {self.__class__.__name__}"
            )
        raise UnsupportedOperationError(
            f"Operation '{operation}' not supported by {self.__class__.__name__}"
        )

    def build_tag_expression(self, field, key, value) -> ColumnElement:
        json_path_str = f"$.tags.{key}"
        extracted = func.json_extract(field, json_path_str)
        if isinstance(value, bool):
            return extracted.isnot(None)
        else:
            return extracted == str(value)
