#!/usr/bin/env python3
"""Translate a constrained question grammar into guarded read-only SQLite queries."""
import argparse
import json
from pathlib import Path
import re
import sqlite3
import tempfile


ALLOWED_COLUMNS = {"id", "product", "status", "amount_cents"}


def compile_question(question):
    if not isinstance(question, str): raise ValueError("question must be text")
    question = " ".join(question.casefold().strip().rstrip("?").split())
    if question == "count orders":
        return "SELECT COUNT(*) AS order_count FROM orders", ()
    if question == "total revenue":
        return "SELECT COALESCE(SUM(amount_cents), 0) AS revenue_cents FROM orders WHERE status = ?", ("paid",)
    match = re.fullmatch(r"orders with status (paid|pending|cancelled)", question)
    if match:
        return "SELECT id, product, status, amount_cents FROM orders WHERE status = ? ORDER BY id", (match.group(1),)
    match = re.fullmatch(r"top ([1-9][0-9]?) products", question)
    if match:
        count = int(match.group(1))
        if count > 20: raise ValueError("top products limit is 20")
        return ("SELECT product, SUM(amount_cents) AS revenue_cents FROM orders WHERE status = ? "
                "GROUP BY product ORDER BY revenue_cents DESC, product LIMIT ?"), ("paid", count)
    raise ValueError("supported: count orders; total revenue; orders with status paid|pending|cancelled; top N products")


def execute_sql(database, sql, parameters=(), row_limit=20, max_steps=20000):
    if type(row_limit) is not int or not 1 <= row_limit <= 1000: raise ValueError("row_limit must be 1..1000")
    if type(max_steps) is not int or max_steps < 1: raise ValueError("max_steps must be positive")
    path = Path(database).resolve()
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=0.25)
    denied = []
    ticks = [0]

    def authorize(action, arg1, arg2, db, trigger):
        allowed = action == sqlite3.SQLITE_SELECT
        if action == sqlite3.SQLITE_READ:
            # SQLite reports COUNT(*) as an empty-column read with db=None.
            allowed = arg1 == "orders" and ((db == "main" and arg2 in ALLOWED_COLUMNS)
                                          or (db in {"main", None} and arg2 == ""))
        if action == sqlite3.SQLITE_FUNCTION:
            allowed = (arg2 or arg1 or "").lower() in {"count", "sum", "coalesce"}
        if not allowed: denied.append({"action": action, "object": arg1})
        return sqlite3.SQLITE_OK if allowed else sqlite3.SQLITE_DENY

    def progress():
        ticks[0] += 1
        return int(ticks[0] > max_steps)

    connection.set_authorizer(authorize)
    connection.set_progress_handler(progress, 1)
    try:
        cursor = connection.execute(sql, parameters)
        columns = [item[0] for item in cursor.description or []]
        rows = cursor.fetchmany(row_limit + 1)
        return {"columns": columns, "rows": [list(row) for row in rows[:row_limit]],
                "truncated": len(rows) > row_limit, "vm_steps": ticks[0]}
    except (sqlite3.Error, sqlite3.Warning) as exc:
        reason = "query rejected by allowlist" if denied else "query interrupted or invalid: " + str(exc)
        raise ValueError(reason) from exc
    finally:
        connection.close()


def ask(database, question, **limits):
    sql, params = compile_question(question)
    return dict(execute_sql(database, sql, params, **limits), question=question, sql=sql, parameters=list(params))


def create_fixture(path):
    connection = sqlite3.connect(path)
    try:
        connection.executescript(Path(__file__).with_name("fixture.sql").read_text())
        connection.commit()
    finally: connection.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", nargs="?", default="top 3 products")
    parser.add_argument("--database", type=Path, help="Trusted existing SQLite database with the documented orders schema")
    parser.add_argument("--row-limit", type=int, default=20)
    parser.add_argument("--max-steps", type=int, default=20000)
    args = parser.parse_args()
    try:
        if args.database:
            result = ask(args.database, args.question, row_limit=args.row_limit, max_steps=args.max_steps)
        else:
            with tempfile.TemporaryDirectory(prefix="datatalk-") as directory:
                database = Path(directory) / "synthetic.sqlite"
                create_fixture(database)
                result = ask(database, args.question, row_limit=args.row_limit, max_steps=args.max_steps)
        print(json.dumps(result, indent=2))
    except (ValueError, OSError, sqlite3.Error) as exc: parser.error(str(exc))


if __name__ == "__main__": main()
