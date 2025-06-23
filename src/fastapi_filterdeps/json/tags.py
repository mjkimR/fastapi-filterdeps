from typing import Any, Optional, List, Dict, Union, Callable

from fastapi import Query
from sqlalchemy import ColumnElement
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase
from fastapi_filterdeps.json.strategy import JsonStrategy


class JsonDictTagsCriteria(SqlFilterCriteriaBase):
    """A specialized filter for querying key-value tags within a JSON column.

    This filter is designed for a common use case where a JSON field contains a
    dictionary, often under a specific key like "tags". It allows filtering by
    tag existence or by a specific tag-value pair. The query parameter accepts
    multiple tags, which are combined with a logical AND.

    The SQL generation is delegated to a `JsonStrategy`, making this filter
    compatible with various database backends.

    Query parameters are parsed in two formats:
    1.  `key`: Checks for the existence of the tag key (e.g., `?tags=urgent`).
    2.  `key:value`: Checks if the tag key's value matches the specified value
        (e.g., `?tags=priority:high`).

    Attributes:
        field (str): The name of the SQLAlchemy model's JSON column that
            contains the tags dictionary.
        alias (str): The alias for the query parameter in the API endpoint.
        strategy (JsonStrategy): The database-specific strategy for building the
            SQL filter expression.
        description (Optional[str]): A custom description for the OpenAPI documentation.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        Given a model `BasicModel` with a JSON `detail` field structured as::
            {"tags": {"urgent": True, "language": "en", "priority": "high"}}

        Use in a FastAPI endpoint::

            from fastapi_filterdeps.base import create_combined_filter_dependency
            from fastapi_filterdeps.json.strategy import JsonOperatorStrategy
            from your_models import BasicModel

            item_filters = create_combined_filter_dependency(
                # This exposes a `?tags=` query parameter.
                JsonDictTagsCriteria(
                    field="detail",
                    alias="tags",
                    strategy=JsonOperatorStrategy(), # Choose the appropriate strategy
                ),
                orm_model=BasicModel,
            )

            # In your endpoint:
            # A request to `/items?tags=urgent&tags=language:en` will find items
            # that have BOTH the "urgent" tag AND the "language:en" tag.
            @app.get("/items")
            def list_items(filters=Depends(item_filters)):
                query = select(BasicModel).where(*filters)
                # ... execute query ...
    """

    def __init__(
        self,
        field: str,
        alias: str,
        strategy: JsonStrategy,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the JsonDictTagsCriteria.

        Args:
            field (str): The name of the JSON field in the SQLAlchemy model.
            alias (str): The alias for the query parameter in the API.
            strategy (JsonStrategy): The database-specific strategy instance for
                building the filter expression.
            description (Optional[str]): A custom description for the OpenAPI
                documentation. If None, a default is generated.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
        """
        self.field = field
        self.alias = alias
        self.strategy = strategy
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
                its value, or to `True` if it's an existence-only check.

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
                of SQLAlchemy filter expressions (one for each tag) or `None`.

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
            model_field = getattr(orm_model, self.field)

            for key, value in tags_dict.items():
                expression = self.strategy.build_tag_expression(
                    field=model_field, key=key, value=value
                )
                filters.append(expression)

            return filters

        return filter_dependency
