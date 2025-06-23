from enum import Enum
from typing import Any, Optional


from fastapi_filterdeps.base import SimpleFilterCriteriaBase


class BinaryFilterType(str, Enum):
    """Defines the types of binary (boolean or null) checks available.

    This enum specifies the filtering strategy for the `BinaryCriteria` class.

    Attributes:
        IS_TRUE: Checks if a field is `True`.
        IS_FALSE: Checks if a field is `False`.
        IS_NONE: Checks if a field is `NULL`.
        IS_NOT_NONE: Checks if a field is `NOT NULL`.
    """

    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    IS_NONE = "is_none"
    IS_NOT_NONE = "is_not_none"

    @classmethod
    def get_all_operators(cls) -> set[str]:
        """Returns a set of all available operator values."""
        return {op.value for op in cls}


class BinaryCriteria(SimpleFilterCriteriaBase):
    """A filter for boolean fields and nullability checks.

    This class creates a filter based on a boolean query parameter. It can check
    for truthiness (`IS TRUE`, `IS FALSE`) or for nullability (`IS NULL`,
    `IS NOT NULL`). The behavior is controlled by the `filter_type` attribute.

    The generated API query parameter accepts a boolean (`true` or `false`).
    Passing `true` applies the specified `filter_type`, while passing `false`
    applies its logical opposite. For example, if `filter_type` is `IS_TRUE`,
    `?{alias}=true` filters for `field IS TRUE`, and `?{alias}=false` filters
    for `field IS FALSE`.

    Attributes:
        field (str): The name of the SQLAlchemy model field to filter on.
        alias (str): The alias for the query parameter in the API endpoint.
            If not provided, it is automatically generated (e.g., "is_active_is_true").
        filter_type (BinaryFilterType): The type of binary check to perform.
            Defaults to `BinaryFilterType.IS_TRUE`.
        description (Optional[str]): A custom description for the OpenAPI documentation.
            A default description is generated if not provided.
        **query_params: Additional keyword arguments to be passed to FastAPI's Query.

    Example:
        In a FastAPI application, define filters for a 'Post' model. Assume 'Post' has a boolean 'is_published' field and a nullable 'archived_at' field::

            from .models import Post
            from fastapi_filterdeps import create_combined_filter_dependency
            from fastapi_filterdeps.generic.binary import BinaryCriteria, BinaryFilterType

            post_filters = create_combined_filter_dependency(
                BinaryCriteria(
                    field="is_published",
                    alias="is_published",
                    filter_type=BinaryFilterType.IS_TRUE,
                    description="Filter for published posts"
                ),
                BinaryCriteria(
                    field="archived_at",
                    alias="is_archived",
                    filter_type=BinaryFilterType.IS_NOT_NONE,
                    description="Filter for archived posts"
                ),
                orm_model=Post,
            )

            # In your endpoint, a request like GET /posts?is_published=true&is_archived=false
            # will filter for published and not archived posts.
    """

    def __init__(
        self,
        field: str,
        filter_type: BinaryFilterType = BinaryFilterType.IS_TRUE,
        alias: Optional[str] = None,
        description: Optional[str] = None,
        **query_params: Any,
    ):
        """Initializes the binary filter criteria.

        Args:
            field (str): The name of the SQLAlchemy model field to filter on.
            alias (Optional[str]): The alias for the query parameter. If None,
                a default is generated from the field name and filter type.
            filter_type (BinaryFilterType): The type of binary check to perform.
                Defaults to `BinaryFilterType.IS_TRUE`.
            description (Optional[str]): A custom description for the OpenAPI
                documentation. A default is generated if not provided.
            **query_params: Additional keyword arguments to be passed to FastAPI's Query.
                (e.g., min_length=3, max_length=50)
        """
        super().__init__(field, alias, description, bool, **query_params)
        self.filter_type = filter_type

    def _get_default_description(self) -> str:
        """Generates a default description based on the filter type.

        Returns:
            str: The default description for the filter.
        """
        descriptions = {
            BinaryFilterType.IS_TRUE: f"Filter where {self.field} is true.",
            BinaryFilterType.IS_FALSE: f"Filter where {self.field} is false.",
            BinaryFilterType.IS_NONE: f"Filter where {self.field} is null.",
            BinaryFilterType.IS_NOT_NONE: f"Filter where {self.field} is not null.",
        }
        base_desc = descriptions.get(self.filter_type, f"Filter by {self.field}.")
        return f"{base_desc} Set to false to invert the filter."

    def _validation_logic(self, orm_model):
        self._validate_enum_value(
            self.filter_type, BinaryFilterType.get_all_operators(), "filter type"
        )

    def _filter_logic(self, orm_model, value):
        model_field = getattr(orm_model, self.field)
        if self.filter_type == BinaryFilterType.IS_TRUE:
            return model_field.is_(True) if value else model_field.is_(False)
        elif self.filter_type == BinaryFilterType.IS_FALSE:
            return model_field.is_(False) if value else model_field.is_(True)
        elif self.filter_type == BinaryFilterType.IS_NONE:
            return model_field.is_(None) if value else model_field.isnot(None)
        elif self.filter_type == BinaryFilterType.IS_NOT_NONE:
            return model_field.isnot(None) if value else model_field.is_(None)
        return None
