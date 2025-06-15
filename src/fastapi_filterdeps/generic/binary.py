from enum import Enum
from typing import Callable, Optional

from fastapi import Query
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement

from fastapi_filterdeps.base import SqlFilterCriteriaBase


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


class BinaryCriteria(SqlFilterCriteriaBase):
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

    Examples:
        # In a FastAPI application, define filters for a 'Post' model.
        # Assume 'Post' has a boolean 'is_published' field and a nullable
        # 'archived_at' field.

        from fastapi_filterdeps import create_combined_filter_dependency
        from .models import Post

        post_filters = create_combined_filter_dependency(
            # Creates a 'published' query parameter.
            # ?published=true -> filters for posts where is_published is True.
            # ?published=false -> filters for posts where is_published is False.
            BinaryCriteria(
                field="is_published",
                alias="published",
                filter_type=BinaryFilterType.IS_TRUE
            ),
            # Creates a 'is_archived' query parameter.
            # ?is_archived=true -> filters for posts where archived_at is not NULL.
            # ?is_archived=false -> filters for posts where archived_at is NULL.
            BinaryCriteria(
                field="archived_at",
                alias="is_archived",
                filter_type=BinaryFilterType.IS_NOT_NONE
            ),
            orm_model=Post,
        )

        # In your endpoint:
        # @app.get("/posts")
        # def list_posts(filters=Depends(post_filters)):
        #     query = select(Post).where(*filters)
        #     ...
    """

    def __init__(
        self,
        field: str,
        alias: Optional[str] = None,
        filter_type: BinaryFilterType = BinaryFilterType.IS_TRUE,
        description: Optional[str] = None,
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
        """
        self.field = field
        self.alias = alias or f"{field}_{filter_type.value}"
        self.filter_type = filter_type
        self.description = description or self._get_default_description()

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

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for binary condition filtering.

        This method validates the provided field and creates a callable FastAPI
        dependency. The dependency, when executed by FastAPI, will produce the
        appropriate SQLAlchemy filter expression based on the query parameter.

        Args:
            orm_model (type[DeclarativeBase]): The SQLAlchemy model class to which
                the filter will be applied.

        Returns:
            Callable: A FastAPI dependency that, when called with a request,
                returns a SQLAlchemy filter condition (`ColumnElement`) or `None`.

        Raises:
            InvalidFieldError: If the specified `field` does not exist on the
                `orm_model`.
            InvalidValueError: If the `filter_type` is not a valid
                `BinaryFilterType`.
        """
        self._validate_field_exists(orm_model, self.field)
        self._validate_enum_value(
            self.filter_type, BinaryFilterType.get_all_operators(), "filter type"
        )

        model_field = getattr(orm_model, self.field)

        def filter_dependency(
            is_value: Optional[bool] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            ),
        ) -> Optional[ColumnElement]:
            """Generates a binary filter condition based on the query parameter.

            Args:
                is_value (Optional[bool]): The boolean value from the query
                    parameter. If None, no filter is applied. If False, the
                    filter logic is inverted.

            Returns:
                Optional[ColumnElement]: A SQLAlchemy filter expression, or None
                    if no filter should be applied.
            """
            if is_value is None:
                return None

            if self.filter_type == BinaryFilterType.IS_TRUE:
                return model_field.is_(True) if is_value else model_field.is_(False)
            elif self.filter_type == BinaryFilterType.IS_FALSE:
                return model_field.is_(False) if is_value else model_field.is_(True)
            elif self.filter_type == BinaryFilterType.IS_NONE:
                return model_field.is_(None) if is_value else model_field.isnot(None)
            else:  # IS_NOT_NONE
                return model_field.isnot(None) if is_value else model_field.is_(None)

        return filter_dependency
