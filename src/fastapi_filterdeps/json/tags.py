from typing import Any, Optional, List, Dict, Union, Callable

from fastapi import Query
from sqlalchemy import func, ColumnElement
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class JsonDictTagsCriteria(SqlFilterCriteriaBase):
    """A specialized filter for querying key-value tags within a JSON column.

    This filter is designed for a common use case where a JSON field contains a
    dictionary of tags. It allows filtering by tag existence or by a specific
    tag-value pair. The query parameter accepts multiple tags, which are
    combined with an AND operator.

    It supports two tag formats in query parameters:
    1.  `key`: Checks for the existence of the tag key (e.g., `?tags=urgent`).
    2.  `key:value`: Checks if the tag key matches the specified value (e.g.,
        `?tags=priority:high`).

    The filter is compatible with both PostgreSQL/MySQL (using JSON operators)
    and SQLite (using the `JSON_EXTRACT` function).

    Attributes:
        field (str): The name of the SQLAlchemy model's JSON column that
            contains the tags dictionary.
        alias (str): The alias for the query parameter in the API endpoint.
        use_json_extract (bool): If True, uses `func.json_extract` for filtering,
            which is required for SQLite. Defaults to False.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.
    Examples:
        # Given a model `BasicModel` with a JSON `detail` field structured as:
        # `{"tags": {"urgent": True, "language": "en", "priority": "high"}}`

        from fastapi_filterdeps.base import create_combined_filter_dependency
        from your_models import BasicModel

        item_filters = create_combined_filter_dependency(
            # This will expose a `?tags=` query parameter.
            # For SQLite, set use_json_extract=True.
            JsonDictTagsCriteria(
                field="detail",
                alias="tags",
                use_json_extract=False
            ),
            orm_model=BasicModel,
        )

        # In your endpoint:
        # A request to `/items?tags=urgent&tags=language:en` will find items
        # that have both the "urgent" tag AND the "language:en" tag.
        @app.get("/items")
        def list_items(filters=Depends(item_filters)):
            query = select(BasicModel).where(*filters)
            # ... execute query ...
    """

    def __init__(
        self,
        field: str,
        alias: str,
        use_json_extract: bool = False,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the JsonDictTagsCriteria.

        Args:
            field (str): The name of the JSON field in the SQLAlchemy model.
            alias (str): The alias for the query parameter in the API.
            use_json_extract (bool): If True, use the `JSON_EXTRACT` function,
                which is necessary for SQLite compatibility. Defaults to False.
            description (Optional[str]): A custom description for the OpenAPI
                documentation. If None, a default is generated.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        self.field = field
        self.alias = alias
        self.use_json_extract = use_json_extract
        self.description = description or self._get_default_description()
        self.query_params = query_params

    def _get_default_description(self) -> str:
        """Generates a default description for the filter."""
        return (
            "Filter by tags. Use 'key' for existence or 'key:value' for a specific value. "
            "Multiple tags are combined with AND. Example: ?tags=urgent&tags=lang:en"
        )

    @classmethod
    def parse_tags_from_query(
        cls, tags_query: List[str]
    ) -> Dict[str, Union[str, bool]]:
        """Parses a list of tag query strings into a structured dictionary.

        This method converts raw query parameter strings into a dictionary of
        tag criteria, distinguishing between existence checks and value checks.

        Args:
            tags_query (List[str]): A list of tag strings from the query, where
                each string is in either 'key' or 'key:value' format.

        Returns:
            Dict[str, Union[str, bool]]: A dictionary mapping each tag key to
                its value, or to `True` if it's an existence check.

        Examples:
            >>> query = ["priority:high", "urgent"]
            >>> JsonDictTagsCriteria.parse_tags_from_query(query)
            {'priority': 'high', 'urgent': True}
        """
        parsed_tags = {}
        for item in tags_query:
            if ":" in item:
                key, value = item.split(":", 1)
                parsed_tags[key.strip()] = value.strip()
            else:
                parsed_tags[item.strip()] = True
        return parsed_tags

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[List[ColumnElement]]]:
        """Builds a FastAPI dependency for filtering by a list of tags.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class that
                the filter will be applied to.

        Returns:
            Callable: A FastAPI dependency that, when resolved, produces a list
                of SQLAlchemy filter expressions or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the `orm_model`.
            InvalidColumnTypeError: If the specified `field` is not a JSON type column.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_column_type(orm_model, self.field, sqlalchemy.JSON)

        def filter_dependency(
            tags: Optional[List[str]] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
                **self.query_params,
            )
        ) -> Optional[List[ColumnElement]]:
            """Generates a list of tag-based filter conditions."""
            if not tags:
                return None

            filters = []
            tags_dict = self.parse_tags_from_query(tags)
            orm_field = getattr(orm_model, self.field)

            for key, value in tags_dict.items():
                if self.use_json_extract:
                    # SQLite JSON1 style
                    json_path = f"$.tags.{key}"
                    extracted = func.json_extract(orm_field, json_path)
                    if isinstance(value, bool):
                        # Existence check
                        filters.append(extracted.isnot(None))
                    else:
                        # Value match
                        filters.append(extracted == value)
                else:
                    # PostgreSQL/MySQL JSONB style
                    target_tag = orm_field["tags"][key]
                    if isinstance(value, bool):
                        # Existence check
                        filters.append(target_tag.isnot(None))
                    else:
                        # Value match, casting the JSONB value to text for comparison
                        filters.append(target_tag.as_string() == value)

            return filters if filters else None

        return filter_dependency
