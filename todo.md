### **Project TODO List & Development Roadmap**

---

#### **[High Priority]**

* **Enhance Test Coverage for Core Functionality**
    We need to bolster the test suite to cover more edge cases and complex interactions between filters. This effort will focus on increasing coverage for the core `FilterSet` logic, combination operators (`&`, `|`, `~`), and widely used criteria like `NumericCriteria` and `StringCriteria`. Achieving higher test coverage is crucial for ensuring long-term stability and preventing regressions as new features are introduced.

* **Refine and Expand Official Documentation (Sphinx)**
    To improve user adoption and proficiency, the official documentation requires significant enhancement. This includes creating a comprehensive API reference and writing detailed guides for common use cases. A new "Advanced Usage" section will be added to showcase complex patterns, such as combining `JoinNestedFilterCriteria` with `GroupByHavingCriteria` to solve real-world problems.

#### **[Medium Priority]**

* **Provide More Granular and Context-Aware Error Messages**
    The current exception handling is robust, but we can make it more informative. When a configuration error occurs, such as a duplicate alias, the error message should pinpoint the exact source. For instance, instead of a generic "Duplicate alias," the new message will be `ConfigurationError in 'UserFilterSet': Duplicate alias 'username' found. It is used by 'username_contains' and 'username_exact' attributes.` This requires passing context from the `FilterSetMeta` down to the criteria instances.

* **Introduce Advanced Full-Text Search Capabilities**
    We will extend our string filtering capabilities by adding a powerful `SearchCriteria`. This new filter will abstract the full-text search (FTS) engines of different database backends, such as `to_tsvector` in PostgreSQL. Users will be able to perform sophisticated, language-aware searches across multiple columns, unlocking a critical feature for many applications. This should follow the `JsonStrategy` pattern for dialect-specific implementations.

* **Develop a Generalized Window Function Filter**
    Building on the success of the `rank` function in `OrderCriteria`, we will create a more generic `WindowFunctionCriteria`. This will serve as a powerful building block, allowing users to filter based on functions like `ROW_NUMBER()`, `LAG`, and `LEAD` over a `PARTITION BY` clause. This enables complex analytical queries, such as selecting the first or last record within a group, directly through the filter layer.

#### **[Low Priority / Backlog]**

* **Implement Native Array Type Support for PostgreSQL**
    To better support databases with native array types, a new `ArrayCriteria` will be implemented. This filter will handle native list/array columns and support common array operators, such as contains (`@>`), is-contained-by (`<@`), and overlaps (`&&`). This feature will provide a more efficient and direct way to query array data compared to using JSON-based workarounds.

* **Introduce an Opt-In SQL Commenting Feature for Tracing**
    For easier debugging of complex queries, we will add an optional feature to inject tracer comments into the generated SQL. By setting `include_sql_comments = True` in the `FilterSet.Meta`, each generated SQL condition will be preceded by a comment like `/* Filter: PostFilter.title_contains */`. This provides immense value for performance tuning and understanding how filters translate to the final query, without adding any overhead to production environments.