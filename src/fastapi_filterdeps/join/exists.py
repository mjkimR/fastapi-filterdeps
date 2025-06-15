from typing import Optional, Callable

from fastapi import Query
from sqlalchemy import select, not_, and_, or_, exists as sql_exists
from fastapi_filterdeps.base import SqlFilterCriteriaBase
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql.expression import ColumnElement


class JoinExistsCriteria(SqlFilterCriteriaBase):
    """A filter that checks for the existence of related records meeting static conditions.

    This criteria builds a filter that uses a correlated SQL EXISTS subquery.
    It checks if any related records exist in `join_model` that satisfy a
    pre-defined, static `filter_condition`. The activation of this filter
    in an API endpoint is controlled by a single boolean query parameter.

    The behavior regarding records that have no related entities at all can be
    controlled with the `include_unrelated` flag.

    Attributes:
        alias (str): The alias for the boolean query parameter that activates
            this filter in the API endpoint.
        filter_condition (list[ColumnElement]): A list of static SQLAlchemy
            expressions to apply as filters on the `join_model` inside the
            subquery.
        join_condition (ColumnElement): The SQLAlchemy expression that defines the
            relationship between the main model and `join_model`, used to
            correlate the subquery (e.g., `Post.id == Comment.post_id`).
        join_model (type[DeclarativeBase]): The SQLAlchemy model class for the
            related records to check for.
        include_unrelated (bool): Controls how to treat records with no
            relations. Defaults to False. If True, the filter logic is adjusted
            to also include parent records that have no children in the
            `join_model`.
        description (Optional[str]): A custom description for the OpenAPI
            documentation. A default is generated if not provided.

    Examples:
        # In a FastAPI application, define a filter to find Posts that have
        # at least one approved comment.
        # This will expose a query parameter `?has_approved_comments=true`.

        from fastapi_filterdeps.base import create_combined_filter_dependency
        from your_models import Post, Comment

        post_filters = create_combined_filter_dependency(
            JoinExistsCriteria(
                alias="has_approved_comments",
                filter_condition=[Comment.is_approved == True],
                join_condition=Post.id == Comment.post_id,
                join_model=Comment,
                include_unrelated=False # Set to True to also get posts with no comments
            ),
            orm_model=Post,
        )

        # In your endpoint:
        @app.get("/posts")
        def list_posts(filters=Depends(post_filters)):
            query = select(Post).where(*filters)
            # ... execute query ...
    """

    def __init__(
        self,
        alias: str,
        filter_condition: list[ColumnElement],
        join_condition: ColumnElement,
        join_model: type[DeclarativeBase],
        include_unrelated: bool = False,
        description: Optional[str] = None,
    ):
        """Initializes the JoinExistsCriteria.

        Args:
            alias (str): The alias for the query parameter (e.g., "has_approved_comments").
            filter_condition (list[ColumnElement]): A list of static SQLAlchemy filter
                conditions to apply to the `join_model`.
            join_condition (ColumnElement): The SQLAlchemy expression defining the
                relationship between the main model and `join_model`.
            join_model (type[DeclarativeBase]): The SQLAlchemy model class to check
                for related records in.
            include_unrelated (bool): If True, the filter logic also includes
                records that do not have any relations. Defaults to False.
            description (Optional[str]): A custom description for the API
                documentation. If None, a default is generated.
        """
        self.alias = alias
        self.filter_condition = filter_condition
        self.join_condition = join_condition
        self.join_model = join_model
        self.include_unrelated = include_unrelated
        self.description = description or self._get_default_description()

    def _get_default_description(self) -> str:
        """Generates a default description for the OpenAPI documentation."""
        return "Filter by the existence of related records. Set to `false` to invert."

    def build_filter(
        self, orm_model: type[DeclarativeBase]
    ) -> Callable[..., Optional[ColumnElement]]:
        """Builds a FastAPI dependency for filtering based on joined table conditions.

        Args:
            orm_model (type[DeclarativeBase]): The main SQLAlchemy model class that
                the filter will be applied to.

        Returns:
            Callable: A FastAPI dependency that, when resolved, produces an
                SQLAlchemy filter expression (`ColumnElement`) or `None`.
        """

        def filter_dependency(
            exists: Optional[bool] = Query(
                default=None,
                alias=self.alias,
                description=self.description,
            )
        ) -> Optional[ColumnElement]:
            if exists is None:
                return None

            stmt_related_satisfies_fc = (
                select(self.join_model)
                .where(self.join_condition)
                .where(*self.filter_condition)
            )
            cond_related_satisfies_fc = sql_exists(stmt_related_satisfies_fc)

            if not self.include_unrelated:
                if exists:
                    return cond_related_satisfies_fc
                else:
                    return not_(cond_related_satisfies_fc)
            else:
                stmt_any_related = select(self.join_model).where(self.join_condition)
                cond_any_related = sql_exists(stmt_any_related)

                if exists:
                    return or_(cond_related_satisfies_fc, not_(cond_any_related))
                else:
                    return and_(cond_any_related, not_(cond_related_satisfies_fc))

        return filter_dependency
