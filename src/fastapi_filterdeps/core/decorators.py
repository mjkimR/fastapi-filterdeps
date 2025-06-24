from fastapi_filterdeps.core.base import SimpleFilterCriteriaBase


def for_filter(field, alias=None, description=None, bound_type=None, **query_params):
    """
    Decorator to create a SimpleFilterCriteriaBase subclass from a filter logic function.

    Args:
        field (str): The ORM model field to filter on.
        alias (Optional[str]): The query parameter name.
        description (Optional[str]): Description for OpenAPI docs.
        bound_type (Optional[type]): The type to bind the query parameter to.
        **query_params: Additional keyword arguments for FastAPI's Query.
    """

    def decorator(func):
        class _CustomSimpleFilter(SimpleFilterCriteriaBase):
            def __init__(self):
                super().__init__(
                    field=field,
                    alias=alias,
                    description=description,
                    bound_type=bound_type,
                    **query_params,
                )

            def _filter_logic(self, orm_model, value):
                return func(orm_model, value)

        _CustomSimpleFilter.__name__ = func.__name__
        return _CustomSimpleFilter()

    return decorator
