import abc
from typing import Any, List
from sqlalchemy import ColumnElement, func

from fastapi_filterdeps.exceptions import ConfigurationError, UnsupportedOperationError


class JsonStrategy(abc.ABC):
    """Abstract base class for defining JSON filtering strategies.

    This class provides a common interface for different database-specific
    implementations of JSON filtering logic. By abstracting the mechanism
    (e.g., native JSON operators vs. `json_extract` function), it allows
    filter criteria like `JsonPathCriteria` and `JsonDictTagsCriteria` to
    remain database-agnostic.

    Subclasses must implement methods to build SQL expressions for both
    path-based and tag-based JSON queries.
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
        """Builds a filter expression for a JSON path-based operation.

        This abstract method must be implemented by concrete strategy classes.

        Args:
            field (ColumnElement): The SQLAlchemy column object representing the JSON field.
            path (List[str]): An ordered list of keys defining the JSON path.
            operation (str): The comparison operation to perform (e.g., 'eq', 'contains').
            value (Any): The value to be used in the comparison.
            array_type (bool): A flag indicating if the target at the JSON path is an array.

        Returns:
            ColumnElement: The resulting SQLAlchemy filter expression.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def build_tag_expression(
        self,
        field: ColumnElement,
        key: str,
        value: Any,
    ) -> ColumnElement:
        """Builds a filter expression for querying a key-value tag.

        This abstract method is specialized for querying dictionary-like
        structures within a JSON field, typically under a 'tags' key.

        Args:
            field (ColumnElement): The SQLAlchemy column object representing the JSON field.
            key (str): The tag key to query.
            value (Any): The value to check for. If `True`, it's an existence check.

        Returns:
            ColumnElement: The resulting SQLAlchemy filter expression.
        """
        raise NotImplementedError


class JsonOperatorStrategy(JsonStrategy):
    """A JSON strategy for databases with native JSON operator support.

    This strategy is suitable for backends like PostgreSQL or modern versions
    of MySQL that provide native operators for traversing and querying JSON
    objects (e.g., `->`, `->>`, `@>`). It translates filter operations into
    these more efficient and idiomatic SQL constructs.
    """

    def build_path_expression(
        self, field, path, operation, value, array_type
    ) -> ColumnElement:
        """Builds a filter expression using native JSON operators."""
        target = field
        for part in path:
            target = target[part]

        if operation == "eq":
            return target.as_string() == str(value)
        if operation == "exists":
            return target.isnot(None)
        if operation == "contains":
            # The `contains` operator (`@>`) can check for a value in a JSON array
            # or a key-value pair in a JSON object. Here we assume containment in an array
            # or a simple value based on `array_type`.
            return target.contains([value] if array_type else value)
        if operation == "any":
            if not array_type:
                raise ConfigurationError(
                    "ARRAY_ANY operation is only supported for fields marked as array_type=True."
                )
            return target.any_(value)  # type: ignore # Uses `?` operator
        if operation == "all":
            if not array_type:
                raise ConfigurationError(
                    "ARRAY_ALL operation is only supported for fields marked as array_type=True."
                )
            return target.all_(value)  # type: ignore # Uses `&` operator
        raise UnsupportedOperationError(
            f"Operation '{operation}' is not supported by {self.__class__.__name__}"
        )

    def build_tag_expression(self, field, key, value) -> ColumnElement:
        if isinstance(value, bool):
            return field["tags"][key].isnot(None)
        else:
            return field["tags"][key].as_string() == str(value)


class JsonExtractStrategy(JsonStrategy):
    """A JSON strategy for databases that rely on the `json_extract` function.

    This strategy is designed for backends like SQLite or older versions of
    MySQL where direct JSON operators are unavailable or less comprehensive.
    It constructs JSON paths as strings and uses the `JSON_EXTRACT` SQL
    function to retrieve values for comparison.

    Note:
        This strategy has limitations, especially for array operations, and
        may be less performant than `JsonOperatorStrategy`.
    """

    def build_path_expression(
        self, field, path, operation, value, array_type
    ) -> ColumnElement:
        """Builds a filter expression using the `json_extract` function."""
        json_path_str = "$.{}".format(".".join(path))
        extracted = func.json_extract(field, json_path_str)

        if operation == "eq":
            return extracted == str(value)
        if operation == "exists":
            return extracted.isnot(None)
        if operation == "contains":
            if array_type:
                raise UnsupportedOperationError(
                    "Array 'contains' operation is not supported by JsonExtractStrategy."
                )
            # This is a simple string-based LIKE, which might not be fully
            # accurate for all JSON containment scenarios.
            return extracted.like(f"%{value}%")
        if operation in ("any", "all"):
            raise UnsupportedOperationError(
                f"Operation '{operation}' is not supported by {self.__class__.__name__}"
            )
        raise UnsupportedOperationError(
            f"Operation '{operation}' is not supported by {self.__class__.__name__}"
        )

    def build_tag_expression(self, field, key, value) -> ColumnElement:
        """Builds a tag filter expression using the `json_extract` function."""
        json_path_str = f"$.tags.{key}"
        extracted = func.json_extract(field, json_path_str)
        if isinstance(value, bool):
            return extracted.isnot(None)
        else:
            return extracted == str(value)
