from typing import Optional

from fastapi import Query
from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class JsonDictTagsCriteria(SqlFilterCriteriaBase):
    """Filter for JSON/JSONB tag fields.

    Provides filtering by tags stored in a JSON field. Supports both tag existence
    checks and tag value matching. Works with both PostgreSQL JSONB and SQLite JSON1.

    The tag system supports two formats:
    1. Key-only tags (e.g., "urgent", "featured") - stored as {key: true}
    2. Key-value pairs (e.g., "priority:high", "language:en") - stored as {key: "value"}

    This dual format allows for both simple boolean flags and more detailed
    categorization within the same tag field.

    Attributes:
        field (str): The model field name to filter on.
        alias (str): The query parameter name.
        use_json_extract (bool): Whether to use JSON_EXTRACT (True for SQLite, False for PostgreSQL)
    """

    def __init__(self, field: str, alias: str, use_json_extract=False):
        """Initialize the tags filter.

        Args:
            field (str): The name of the field to filter on.
            alias (str): The query parameter name.
            use_json_extract (bool): Use JSON_EXTRACT function (True for SQLite). Defaults to False.
        """
        self.field = field
        self.alias = alias
        self.use_json_extract = use_json_extract

    @classmethod
    def parse_tags_from_query(cls, tags_query: list[str]) -> dict[str, str | bool]:
        """Parse tag query parameters into a structured dictionary.

        Converts raw query parameters into a structured dictionary of tag criteria.

        Args:
            tags_query (list[str]): A list of tag strings in either 'key' or 'key:value' format.

        Returns:
            dict[str, str | bool]: A dictionary mapping tag keys to their values
                (or True for existence checks).

        Example:
            ["priority", "language:en"] becomes {"priority": True, "language": "en"}
        """
        parsed_tags = {}
        for item in tags_query:
            if ":" in item:
                key, value = item.split(":", 1)
                parsed_tags[key.strip()] = value.strip()
            else:
                parsed_tags[item.strip()] = True
        return parsed_tags

    def build_filter(self, orm_model: type[DeclarativeBase]):
        """Build a FastAPI dependency for filtering by tags.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to create filter conditions for.

        Returns:
            callable: A FastAPI dependency function that returns a list of SQLAlchemy filter conditions
                for filtering by tags.
        """
        self._validate_field_exists(orm_model, self.field)

        def filter_dependency(
            tags: Optional[list[str]] = Query(
                None,
                alias=self.alias,
                description="List of tags in 'key' or 'key:value' format. Example: tags=summary&tags=language:en",
            )
        ):
            """Generate tag filter conditions.

            Args:
                tags (Optional[list[str]]): List of tag strings to filter by.

            Returns:
                Optional[list]: List of SQLAlchemy filter conditions or None if no tags provided.
            """
            if tags is None:
                return None

            filters = []
            tags_dict = self.parse_tags_from_query(tags)
            field = getattr(orm_model, self.field)

            for key, value in tags_dict.items():
                if self.use_json_extract:
                    # SQLite JSON1 방식
                    json_path = f"$.tags.{key}"  # Add 'tags' to the path
                    extracted = func.json_extract(field, json_path)

                    if isinstance(value, bool):
                        # 존재 여부 체크
                        filters.append(extracted.isnot(None))
                    else:
                        # 값 비교
                        filters.append(extracted == value)
                else:
                    # PostgreSQL JSONB 방식
                    if isinstance(value, bool):
                        filters.append(field["tags"][key].isnot(None))
                    else:
                        filters.append(field["tags"][key].as_string() == value)

            return filters

        return filter_dependency
