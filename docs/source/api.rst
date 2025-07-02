#############
API Reference
#############

This section provides a detailed overview of the ``fastapi-filterdeps`` library's public API.

.. contents::
   :local:
   :depth: 2

Core Components
===============

Core components form the foundation of the library, providing the base classes and functions for creating and combining filters.

.. automodule:: fastapi_filterdeps.filtersets
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.core.base
   :members: SqlFilterCriteriaBase, SimpleFilterCriteriaBase
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.order_by
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.core.decorators
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: fastapi_filterdeps.core.exceptions
   :members:
   :undoc-members:
   :show-inheritance:

----------------

Available Filters
=================

These are the pre-built filter criteria classes that you can use to build your `FilterSet`. They are organized by the type of database column or relationship they operate on.

Column Filters
--------------
Filters that operate on standard SQLAlchemy column types.

.. automodule:: fastapi_filterdeps.filters.column.string
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.column.numeric
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.column.binary
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.column.enum
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.column.time
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.column.relative_time
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.column.regex
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.column.order
   :members:
   :undoc-members:
   :show-inheritance:

JSON Filters
------------
Filters specifically designed for querying `JSON` or `JSONB` columns.

.. automodule:: fastapi_filterdeps.filters.json.path
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.json.tags
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.json.strategy
   :members:
   :undoc-members:
   :show-inheritance:

Relation Filters
----------------
Filters that operate on SQLAlchemy relationships, often resulting in subqueries.

.. automodule:: fastapi_filterdeps.filters.relation.exists
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.relation.nested
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.filters.relation.having
   :members:
   :undoc-members:
   :show-inheritance:

----------------

Filter Operations
=================

These modules provide the logic for combining (`&`, `|`) and inverting (`~`) filter criteria.

.. automodule:: fastapi_filterdeps.operations.combine
   :members:
   :undoc-members:
   :show-inheritance:

.. automodule:: fastapi_filterdeps.operations.invert
   :members:
   :undoc-members:
   :show-inheritance: