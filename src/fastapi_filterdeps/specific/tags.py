from typing import Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase

from fastapi_filterdeps.base import SqlFilterCriteriaBase


class TagsFieldCriteria(SqlFilterCriteriaBase):
    """Filter for JSONB tag fields.

    Provides filtering by tags stored in a JSONB field. Supports both tag existence
    checks and tag value matching.

    Attributes:
        tags_field (str): The model field name to filter on. Defaults to "tags".
    """

    def __init__(self, tags_field="tags"):
        """Initialize the tags filter.

        Args:
            tags_field (str): The name of the field to filter on. Defaults to "tags".
        """
        self.tags_field = tags_field

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

        def filter_dependency(
                tags: Optional[list[str]] = Query(
                    None,
                    description="List of tags in 'key' or 'key:value' format. Example: tags=summary&tags=language:en"
                )
        ):
            """Generate tag filter conditions.

            Args:
                tags (Optional[list[str]]): List of tag strings to filter by.

            Returns:
                Optional[list]: List of SQLAlchemy filter conditions or None if no tags provided.
            """
            filters = []
            if tags is None:
                return None
            tags = self.parse_tags_from_query(tags)

            for key, value in tags.items():
                if isinstance(value, bool):
                    filters.append(getattr(orm_model, self.tags_field)[key].isnot(None))
                else:
                    filters.append(getattr(orm_model, self.tags_field)[key].as_string() == value)
            return filters

        return filter_dependency
