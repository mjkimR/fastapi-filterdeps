from fastapi import Query
from typing import Sequence, Optional

from sqlalchemy.orm import DeclarativeBase
from fastapi_filterdeps.exceptions import InvalidFieldError, InvalidValueError
from fastapi_filterdeps.base import SqlFilterCriteriaBase


def order_by_params(
    orm_model: type[DeclarativeBase],
    whitelist: Sequence[str] = ("created_at", "updated_at"),
    default: str = "-created_at",
):
    """Creates a FastAPI dependency for order_by parameter handling.

    This function generates a dependency that parses and validates order_by query parameters,
    converting them into SQLAlchemy order_by conditions. It automatically appends primary keys
    as tie-breakers if they are not already included in the ordering.

    Args:
        orm_model (type[DeclarativeBase]): The SQLAlchemy model class to create order_by conditions for.
            Must be a declarative model class with defined columns.
        whitelist (Sequence[str], optional): List of allowed field names for ordering.
            These fields must exist in the orm_model.
            Defaults to ("created_at", "updated_at").
        default (str, optional): Default ordering to use when none is specified.
            Should follow the same format as order_by parameter (e.g., "-created_at" for descending).
            Defaults to "-created_at".

    Returns:
        callable: A FastAPI dependency function that returns a list of SQLAlchemy order_by
            conditions (List[sqlalchemy.sql.elements.UnaryExpression]).

    Raises:
        InvalidFieldError: If a field in whitelist doesn't exist in the model.
        InvalidValueError: If an order_by field is provided that's not in the whitelist.

    Examples:
        >>> from fastapi import FastAPI
        >>> from sqlalchemy.orm import DeclarativeBase
        >>>
        >>> app = FastAPI()
        >>> class User(DeclarativeBase):
        ...     id: int
        ...     created_at: datetime
        ...     name: str
        >>>
        >>> @app.get("/users")
        >>> def get_users(
        ...     order: list = Depends(order_by_params(
        ...         User,
        ...         whitelist=["created_at", "name"],
        ...         default="-created_at"
        ...     ))
        ... ):
        ...     # order will contain SQLAlchemy order_by expressions
        ...     return {"users": db.query(User).order_by(*order).all()}

        # Query examples:
        # GET /users?order_by=name,-created_at  # Order by name (asc) then created_at (desc)
        # GET /users?order_by=-name  # Order by name (desc), id will be appended as tie-breaker
    """

    # Validation: Ensure all fields in whitelist exist in the orm_model
    for field_name in whitelist:
        if not hasattr(orm_model, field_name):
            raise InvalidFieldError(
                f"Field '{field_name}' listed in whitelist does not exist in model '{orm_model.__name__}'."
            )

    def _parse_options_from_query(_query: str) -> list[dict]:
        tokens = []
        values = [t.strip() for t in _query.split(",") if t.strip()]

        for value in values:
            if value.startswith("-"):
                tokens.append({"field": value[1:], "direction": "desc"})
            else:
                tokens.append({"field": value, "direction": "asc"})
        return tokens

    def order_by_dependency(
        order_by: Optional[str] = Query(
            default=None,
            description=(
                "Order by option. Comma-separated field names, prefix with '-' for descending order.\n"
                "Primary keys will be automatically appended at the end if not present (acts as a tie-breaker).\n"
                "Example: order_by=-created_at\n"
                f"Default: '{default}'"
            ),
        )
    ):
        if order_by is None:
            order_by = default
        options = _parse_options_from_query(order_by)

        # Validation: Check if order_by fields are in the whitelist
        for option in options:
            if option["field"] not in whitelist:
                raise InvalidValueError(
                    f"Invalid order by field: '{option['field']}'. Allowed fields: {', '.join(whitelist)}"
                )

        # Return SQLAlchemy order_by conditions
        order_by_conditions = []
        for option in options:
            field = option["field"]
            direction = option["direction"]
            if direction == "desc":
                order_by_conditions.append(getattr(orm_model, field).desc())
            else:
                order_by_conditions.append(getattr(orm_model, field).asc())

        # Try to append primary keys at the end if not present (as tie-breaker)
        try:
            pk_columns = SqlFilterCriteriaBase.get_primary_keys(orm_model)
            if pk_columns:
                # Get the fields that are already in the ordering
                ordered_fields = [opt["field"] for opt in options]
                # Add each PK that isn't already in the ordering
                for pk in pk_columns:
                    if pk.name not in ordered_fields:
                        order_by_conditions.append(pk.asc())
        except Exception:
            # If model has no primary keys, just continue without them
            pass

        return order_by_conditions

    return order_by_dependency
