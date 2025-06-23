from typing import Any, Optional, List, Dict, Union

import sqlalchemy

from fastapi_filterdeps.base import SimpleFilterCriteriaBase
from fastapi_filterdeps.strategy.json_strategy import JsonStrategy


class JsonDictTagsCriteria(SimpleFilterCriteriaBase):
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
        strategy: JsonStrategy,
        alias: Optional[str] = None,
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
        super().__init__(field, alias, description, list[str], **query_params)
        self.strategy = strategy

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

    def _validation_logic(self, orm_model):
        self._validate_column_type(orm_model, self.field, sqlalchemy.JSON)

    def _filter_logic(self, orm_model, value):
        filters = []
        tags_dict = self.parse_tags_from_query(value)
        model_field = getattr(orm_model, self.field)

        for key, value in tags_dict.items():
            expression = self.strategy.build_tag_expression(
                field=model_field, key=key, value=value
            )
            filters.append(expression)

        return filters
