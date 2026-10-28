"""Run the controlled PostgreSQL ingress gate against a disposable local database.

Requires psycopg and libpq environment settings for a role that can create
schemas and roles. Run explicitly; it is not part of the offline test suite.
"""

from __future__ import annotations

import os
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import psycopg
from psycopg import sql

from parison.core import ParisonError
from parison.postgres_ingress import _metadata, export_postgres
from parison.source_receipt import verify_postgres_export


def main() -> None:
    suffix = uuid.uuid4().hex[:12]
    schema, reader = f"parison_ingress_{suffix}", f"parison_reader_{suffix}"
    original_user = os.environ.get("PGUSER")
    with psycopg.connect("", autocommit=True) as admin:
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(reader)))
        try:
            admin.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
            admin.execute(
                sql.SQL(
                    "CREATE TABLE {}.orders (id integer PRIMARY KEY, note text, amount numeric, stamped timestamptz)"
                ).format(sql.Identifier(schema))
            )
            admin.execute(
                sql.SQL(
                    "INSERT INTO {}.orders VALUES (1, 'hello', 1.20, '2026-10-28 00:00:00+00'), "
                    "(2, NULL, -4.50, '2026-10-28 01:00:00+00')"
                ).format(sql.Identifier(schema))
            )
            admin.execute(
                sql.SQL("GRANT USAGE ON SCHEMA {} TO {}").format(sql.Identifier(schema), sql.Identifier(reader))
            )
            admin.execute(
                sql.SQL("GRANT SELECT ON {}.orders TO {}").format(sql.Identifier(schema), sql.Identifier(reader))
            )
            with tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                import json

                plan = {
                    "plan_version": 1,
                    "source_id": "controlled-source",
                    "schema": schema,
                    "table": "orders",
                    "columns": ["id", "note", "amount", "stamped"],
                    "primary_key": ["id"],
                    "limits": {
                        "max_rows": 10,
                        "max_output_bytes": 10000,
                        "statement_timeout_ms": 5000,
                        "wall_timeout_ms": 10000,
                    },
                }
                plan_path = root / "plan.json"
                plan_path.write_text(json.dumps(plan))
                bundle = root / "bundle"

                def after_snapshot(cursor, declared):
                    source, snapshot = _metadata(cursor, declared)
                    admin.execute("SET lock_timeout TO '250ms'")
                    try:
                        admin.execute(
                            sql.SQL("ALTER TABLE {}.orders RENAME TO swapped_orders").format(sql.Identifier(schema))
                        )
                    except psycopg.errors.LockNotAvailable:
                        pass
                    else:
                        raise AssertionError("qualified relation was not locked")
                    admin.execute(
                        sql.SQL("INSERT INTO {}.orders VALUES (3, 'late', 9, now())").format(sql.Identifier(schema))
                    )
                    return source, snapshot

                os.environ["PGUSER"] = reader
                try:
                    with patch("parison.postgres_ingress._metadata", after_snapshot):
                        summary = export_postgres(plan_path, bundle)
                    assert summary["rows"] == 2, summary
                    assert verify_postgres_export(bundle) == summary
                    assert not (bundle / "data.csv").read_text().count("late")
                    try:
                        export_postgres(plan_path, bundle)
                    except ParisonError:
                        pass
                    else:
                        raise AssertionError("no-overwrite gate failed")
                    admin.execute(
                        sql.SQL("ALTER TABLE {}.orders ENABLE ROW LEVEL SECURITY").format(sql.Identifier(schema))
                    )
                    admin.execute(
                        sql.SQL("CREATE POLICY only_first ON {}.orders FOR SELECT USING (id = 1)").format(
                            sql.Identifier(schema)
                        )
                    )
                    try:
                        export_postgres(plan_path, root / "rls")
                    except ParisonError:
                        assert not (root / "rls").exists()
                    else:
                        raise AssertionError("RLS gate failed")
                    admin.execute(
                        sql.SQL("ALTER TABLE {}.orders DISABLE ROW LEVEL SECURITY").format(sql.Identifier(schema))
                    )
                    admin.execute(
                        sql.SQL("INSERT INTO {}.orders VALUES (4, %s, 0, now())").format(sql.Identifier(schema)),
                        (r"\N",),
                    )
                    try:
                        export_postgres(plan_path, root / "null_marker")
                    except ParisonError:
                        assert not (root / "null_marker").exists()
                    else:
                        raise AssertionError("NULL marker collision gate failed")
                finally:
                    if original_user is None:
                        os.environ.pop("PGUSER", None)
                    else:
                        os.environ["PGUSER"] = original_user
                admin.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))
                assert verify_postgres_export(bundle) == summary
                print("PostgreSQL ingress live gate passed: snapshot, RLS, NULL collision, no-overwrite, offline")
        finally:
            admin.execute(sql.SQL("DROP SCHEMA IF EXISTS {} CASCADE").format(sql.Identifier(schema)))
            admin.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(reader)))


if __name__ == "__main__":
    main()
