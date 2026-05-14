from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Iterable, Mapping


class ValidationError(Exception):
    """Raised when a database request cannot be safely executed."""


class SQLiteAdapter:
    """Small SQLite data access layer with identifier validation."""

    ALLOWED_OPERATORS = {
        "eq": "=",
        "ne": "!=",
        "gt": ">",
        "gte": ">=",
        "lt": "<",
        "lte": "<=",
        "like": "LIKE",
        "in": "IN",
    }
    ALLOWED_AGGREGATES = {"count", "avg", "sum", "min", "max"}
    MAX_LIMIT = 100

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def list_tables(self) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            ).fetchall()
        return [row["name"] for row in rows]

    def get_table_schema(self, table: str) -> list[dict[str, Any]]:
        table = self._validate_table(table)
        with self.connect() as connection:
            rows = connection.execute(
                f"PRAGMA table_info({self._quote_identifier(table)})"
            ).fetchall()
        return [
            {
                "name": row["name"],
                "type": row["type"],
                "not_null": bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            }
            for row in rows
        ]

    def database_schema(self) -> dict[str, Any]:
        tables = {
            table: {"columns": self.get_table_schema(table)}
            for table in self.list_tables()
        }
        return {"database": str(self.db_path), "tables": tables}

    def search(
        self,
        table: str,
        columns: list[str] | None = None,
        filters: Any = None,
        limit: int = 20,
        offset: int = 0,
        order_by: str | None = None,
        descending: bool = False,
    ) -> dict[str, Any]:
        table = self._validate_table(table)
        selected_columns = self._validate_selected_columns(table, columns)
        where_sql, params = self._build_where_clause(table, filters)
        limit, offset = self._validate_limit_offset(limit, offset)

        select_sql = ", ".join(
            self._quote_identifier(column) for column in selected_columns
        )
        sql_parts = [
            f"SELECT {select_sql}",
            f"FROM {self._quote_identifier(table)}",
        ]
        if where_sql:
            sql_parts.append(where_sql)
        if order_by:
            column = self._validate_column(table, order_by)
            direction = "DESC" if descending else "ASC"
            sql_parts.append(f"ORDER BY {self._quote_identifier(column)} {direction}")
        sql_parts.append("LIMIT ? OFFSET ?")
        params.extend([limit, offset])

        rows = self._fetch_all(" ".join(sql_parts), params)
        return {
            "table": table,
            "columns": selected_columns,
            "rows": rows,
            "count": len(rows),
            "limit": limit,
            "offset": offset,
        }

    def insert(self, table: str, values: Mapping[str, Any]) -> dict[str, Any]:
        table = self._validate_table(table)
        if not isinstance(values, Mapping) or not values:
            raise ValidationError("insert requires a non-empty values object")

        columns = [self._validate_column(table, column) for column in values.keys()]
        placeholders = ", ".join("?" for _ in columns)
        column_sql = ", ".join(self._quote_identifier(column) for column in columns)
        sql = (
            f"INSERT INTO {self._quote_identifier(table)} ({column_sql}) "
            f"VALUES ({placeholders})"
        )

        with self.connect() as connection:
            cursor = connection.execute(sql, [values[column] for column in columns])
            inserted_id = cursor.lastrowid
            connection.commit()
            row = connection.execute(
                f"SELECT * FROM {self._quote_identifier(table)} WHERE rowid = ?",
                [inserted_id],
            ).fetchone()

        return {
            "table": table,
            "inserted_id": inserted_id,
            "record": dict(row) if row else dict(values),
        }

    def aggregate(
        self,
        table: str,
        metric: str,
        column: str | None = None,
        filters: Any = None,
        group_by: str | list[str] | None = None,
    ) -> dict[str, Any]:
        table = self._validate_table(table)
        metric = self._validate_metric(metric)
        group_columns = self._validate_group_by(table, group_by)
        target_sql = self._aggregate_target_sql(table, metric, column)
        where_sql, params = self._build_where_clause(table, filters)

        select_parts = [self._quote_identifier(column) for column in group_columns]
        select_parts.append(f"{metric.upper()}({target_sql}) AS value")

        sql_parts = [
            f"SELECT {', '.join(select_parts)}",
            f"FROM {self._quote_identifier(table)}",
        ]
        if where_sql:
            sql_parts.append(where_sql)
        if group_columns:
            group_sql = ", ".join(self._quote_identifier(column) for column in group_columns)
            sql_parts.append(f"GROUP BY {group_sql}")
            sql_parts.append(f"ORDER BY {group_sql}")

        rows = self._fetch_all(" ".join(sql_parts), params)
        return {
            "table": table,
            "metric": metric,
            "column": column,
            "group_by": group_columns,
            "rows": rows,
        }

    def _fetch_all(self, sql: str, params: Iterable[Any]) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(sql, list(params)).fetchall()
        return [dict(row) for row in rows]

    def _validate_table(self, table: str) -> str:
        if not isinstance(table, str) or not table.strip():
            raise ValidationError("table must be a non-empty string")
        table = table.strip()
        tables = self.list_tables()
        if table not in tables:
            raise ValidationError(
                f"unknown table '{table}'. Available tables: {', '.join(tables)}"
            )
        return table

    def _columns_for_table(self, table: str) -> list[str]:
        schema = self.get_table_schema(table)
        return [column["name"] for column in schema]

    def _validate_column(self, table: str, column: str) -> str:
        if not isinstance(column, str) or not column.strip():
            raise ValidationError("column must be a non-empty string")
        column = column.strip()
        columns = self._columns_for_table(table)
        if column not in columns:
            raise ValidationError(
                f"unknown column '{column}' for table '{table}'. "
                f"Available columns: {', '.join(columns)}"
            )
        return column

    def _validate_selected_columns(
        self, table: str, columns: list[str] | None
    ) -> list[str]:
        if columns is None:
            return self._columns_for_table(table)
        if not isinstance(columns, list) or not columns:
            raise ValidationError("columns must be a non-empty list when provided")
        return [self._validate_column(table, column) for column in columns]

    def _validate_metric(self, metric: str) -> str:
        if not isinstance(metric, str) or not metric.strip():
            raise ValidationError("metric must be a non-empty string")
        metric = metric.strip().lower()
        if metric not in self.ALLOWED_AGGREGATES:
            raise ValidationError(
                f"unsupported aggregate metric '{metric}'. "
                f"Allowed metrics: {', '.join(sorted(self.ALLOWED_AGGREGATES))}"
            )
        return metric

    def _validate_group_by(
        self, table: str, group_by: str | list[str] | None
    ) -> list[str]:
        if group_by is None:
            return []
        if isinstance(group_by, str):
            return [self._validate_column(table, group_by)]
        if isinstance(group_by, list) and group_by:
            return [self._validate_column(table, column) for column in group_by]
        raise ValidationError("group_by must be a column name or a non-empty list")

    def _aggregate_target_sql(
        self, table: str, metric: str, column: str | None
    ) -> str:
        if metric == "count" and column is None:
            return "*"
        if column is None:
            raise ValidationError(f"aggregate metric '{metric}' requires a column")
        return self._quote_identifier(self._validate_column(table, column))

    def _validate_limit_offset(self, limit: int, offset: int) -> tuple[int, int]:
        if not isinstance(limit, int) or isinstance(limit, bool):
            raise ValidationError("limit must be an integer")
        if not isinstance(offset, int) or isinstance(offset, bool):
            raise ValidationError("offset must be an integer")
        if limit < 1 or limit > self.MAX_LIMIT:
            raise ValidationError(f"limit must be between 1 and {self.MAX_LIMIT}")
        if offset < 0:
            raise ValidationError("offset must be greater than or equal to 0")
        return limit, offset

    def _build_where_clause(
        self, table: str, filters: Any
    ) -> tuple[str, list[Any]]:
        normalized = self._normalize_filters(filters)
        if not normalized:
            return "", []

        clauses: list[str] = []
        params: list[Any] = []
        for item in normalized:
            column = self._validate_column(table, item["column"])
            operator = item["operator"]
            value = item["value"]
            quoted_column = self._quote_identifier(column)

            if operator not in self.ALLOWED_OPERATORS:
                raise ValidationError(
                    f"unsupported filter operator '{operator}'. "
                    f"Allowed operators: {', '.join(sorted(self.ALLOWED_OPERATORS))}"
                )

            if operator == "in":
                if not isinstance(value, list) or not value:
                    raise ValidationError("operator 'in' requires a non-empty list value")
                placeholders = ", ".join("?" for _ in value)
                clauses.append(f"{quoted_column} IN ({placeholders})")
                params.extend(value)
            elif operator == "eq" and value is None:
                clauses.append(f"{quoted_column} IS NULL")
            elif operator == "ne" and value is None:
                clauses.append(f"{quoted_column} IS NOT NULL")
            else:
                clauses.append(
                    f"{quoted_column} {self.ALLOWED_OPERATORS[operator]} ?"
                )
                params.append(value)

        return f"WHERE {' AND '.join(clauses)}", params

    def _normalize_filters(self, filters: Any) -> list[dict[str, Any]]:
        if filters is None or filters == {} or filters == []:
            return []

        if isinstance(filters, Mapping):
            normalized = []
            for column, value in filters.items():
                if isinstance(value, Mapping):
                    operator = value.get("operator", value.get("op", "eq"))
                    filter_value = value.get("value")
                else:
                    operator = "eq"
                    filter_value = value
                normalized.append(
                    {"column": column, "operator": operator, "value": filter_value}
                )
            return normalized

        if isinstance(filters, list):
            normalized = []
            for item in filters:
                if not isinstance(item, Mapping):
                    raise ValidationError("each filter must be an object")
                column = item.get("column")
                operator = item.get("operator", item.get("op", "eq"))
                if "value" not in item:
                    raise ValidationError("each filter object requires a value")
                normalized.append(
                    {"column": column, "operator": operator, "value": item["value"]}
                )
            return normalized

        raise ValidationError("filters must be an object, list, or null")

    @staticmethod
    def _quote_identifier(identifier: str) -> str:
        return '"' + identifier.replace('"', '""') + '"'
