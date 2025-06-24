class FilterDependencyError(Exception):
    """Base exception for all filter dependency related errors."""

    pass


class ConfigurationError(FilterDependencyError):
    """
    Raised for errors in filter configuration during development.

    This category of exceptions indicates a problem with how the filter
    dependencies are defined in the code, rather than an issue with runtime
    user input.
    """

    pass


class InvalidFieldError(ConfigurationError):
    """
    Raised when a specified field does not exist on the ORM model.

    Example:
        .. code-block:: python

            class User(Base):
                __tablename__ = "users"
                id: Mapped[int] = mapped_column(primary_key=True)
                username: Mapped[str]

            # This will raise InvalidFieldError because the 'name' field does not exist.
            # The available fields are 'id' and 'username'.
            invalid_filter = StringCriteria(field="name", value="test")
    """

    pass


class InvalidRelationError(ConfigurationError):
    """
    Raised when a specified relationship does not exist on the ORM model.

    This is common in join-based filters like `ExistsCriteria` or `NestedCriteria`.

    Example:
        .. code-block:: python

            class User(Base):
                __tablename__ = "users"
                id: Mapped[int] = mapped_column(primary_key=True)
                posts: Mapped[List["Post"]] = relationship(back_populates="author")

            # This will raise InvalidRelationError because the 'comments' relation
            # is not defined on the User model.
            invalid_filter = ExistsCriteria(relation="comments", field="content", value="test")
    """

    pass


class InvalidColumnTypeError(ConfigurationError):
    """
    Raised when a filter is applied to an unsupported column type.

    Some filters are designed to work only with specific data types (e.g., JSON).
    This exception prevents runtime database errors by validating the column type
    during filter construction.

    Example:
        .. code-block:: python

            class User(Base):
                __tablename__ = "users"
                id: Mapped[int] = mapped_column(primary_key=True)
                username: Mapped[str]  # This is a string, not JSON.

            # This will raise InvalidColumnTypeError because JsonPathCriteria
            # requires a JSON or JSONB column.
            invalid_filter = JsonPathCriteria(field="username", path="$.key", value="test")
    """

    pass


class MissingPrimaryKeyError(ConfigurationError):
    """
    Raised when a filter requires a primary key on a model, but none is found.

    Certain operations, especially those related to ordering and pagination,
    rely on the presence of a primary key.

    Example:
        .. code-block:: python

            class Log(Base):
                __tablename__ = "logs"
                # No primary key is defined.
                message: Mapped[str]

            # This will raise MissingPrimaryKeyError because OrderCriteria needs a PK
            # to apply a deterministic order.
            invalid_order = OrderCriteria(orm_model=Log, order_by=["message"])
    """

    pass


class InvalidValueError(FilterDependencyError):
    """
    Raised when a value provided to a filter is invalid.

    This can occur in two scenarios:
    1.  **Configuration Time**: An invalid value is used when defining a filter,
        such as an incorrect enum value for a `match_type`.
    2.  **Runtime**: An invalid value is provided by an API user, such as a
        field name for ordering that is not in the allowed `whitelist`.

    Example:
        Configuration Time

        .. code-block:: python

            # This will raise InvalidValueError because 'contains_case_sensitive'
            # is not a valid MatchType for StringCriteria.
            invalid_filter = StringCriteria(field="username", match_type="contains_case_sensitive", value="test")

        Runtime, within an endpoint

        .. code-block:: python

            # If a user requests GET /users?order_by=id,desc,password,asc
            # and 'password' is not in the whitelist, order_by_params dependency
            # will raise InvalidValueError.
            order_by = order_by_params(whitelist=["id", "username"])
    """

    pass


class UnsupportedOperationError(FilterDependencyError):
    """Raised when an operation is not supported for the given configuration."""

    pass
