from fastapi import Query
from typing import Sequence, Optional

from sqlalchemy.orm import DeclarativeBase
from fastapi_filterdeps.exceptions import InvalidFieldError, InvalidValueError


def order_by_params(
    orm_model: type[DeclarativeBase],
    whitelist: Sequence[str] = ("created_at", "updated_at", "id"),
    default: str = "-created_at",
):
    """Creates a FastAPI dependency for order_by parameter handling.

    This function generates a dependency that parses and validates order_by query parameters,
    converting them into SQLAlchemy order_by conditions.

    Args:
        orm_model (type[DeclarativeBase]): The SQLAlchemy model class to create order_by conditions for.
        whitelist (Sequence[str], optional): List of allowed field names for ordering.
            Defaults to ("created_at", "updated_at", "id").
        default (str, optional): Default ordering to use when none is specified.
            Defaults to "-created_at".

    Returns:
        callable: A FastAPI dependency function that returns a list of SQLAlchemy order_by conditions.

    Raises:
        InvalidFieldError: If a field in whitelist doesn't exist in the model.
        InvalidValueError: If an invalid order_by field is provided.
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
                "The 'id' field is automatically appended at the end if not present (acts as a tie-breaker).\n"
                "Example: order_by=-created_at,id\n"
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
        if order_by_conditions and hasattr(orm_model, "id"):
            # Automatically append id field at the end if not present (as tie-breaker)
            if "id" not in [opt["field"] for opt in options]:
                order_by_conditions.append(getattr(orm_model, "id").asc())

        return order_by_conditions

    return order_by_dependency
