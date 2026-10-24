from pathlib import Path
import sqlite3
import tempfile
import unittest
from main import ask, compile_question, create_fixture, execute_sql


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database = Path(self.directory.name) / "test.sqlite"
        create_fixture(self.database)

    def tearDown(self): self.directory.cleanup()

    def test_count_and_paid_revenue(self):
        self.assertEqual(ask(self.database, "COUNT orders?")["rows"], [[5]])
        self.assertEqual(ask(self.database, "total revenue")["rows"], [[2700]])

    def test_no_paid_orders_returns_integer_zero(self):
        with sqlite3.connect(self.database) as connection:
            connection.execute("UPDATE orders SET status='pending' WHERE status='paid'")
        revenue = ask(self.database, "total revenue")["rows"][0][0]
        self.assertEqual(revenue, 0)
        self.assertIs(type(revenue), int)

    def test_ranking_and_parameterized_status(self):
        out = ask(self.database, "top 1 products")
        self.assertEqual(out["rows"], [["Demo Notebook",2400]])
        self.assertEqual(out["parameters"], ["paid",1])
        self.assertEqual(len(ask(self.database,"orders with status pending")["rows"]), 1)

    def test_injection_and_unsupported_intents_rejected(self):
        for query in ["orders with status paid OR 1=1", "drop orders", "top 99 products"]:
            with self.assertRaises(ValueError): compile_question(query)

    def test_writes_are_denied_and_data_survives(self):
        for sql in ["DELETE FROM orders", "UPDATE orders SET amount_cents = 0", "DROP TABLE orders"]:
            with self.assertRaises(ValueError): execute_sql(self.database, sql)
        self.assertEqual(ask(self.database,"count orders")["rows"], [[5]])

    def test_private_tables_pragmas_and_attachments_denied(self):
        for sql in ["SELECT * FROM private_notes", "PRAGMA table_info(orders)", "ATTACH ':memory:' AS extra"]:
            with self.assertRaises(ValueError): execute_sql(self.database, sql)

    def test_multiple_statements_and_unsafe_functions_denied(self):
        for sql in ["SELECT id FROM orders; DELETE FROM orders", "SELECT randomblob(10000000)"]:
            with self.assertRaises(ValueError): execute_sql(self.database, sql)

    def test_row_cap_is_explicit(self):
        out = ask(self.database,"orders with status paid", row_limit=2)
        self.assertEqual(len(out["rows"]),2)
        self.assertTrue(out["truncated"])

    def test_progress_limit_interrupts_expensive_query(self):
        sql = "SELECT COUNT(*) FROM orders a, orders b, orders c, orders d, orders e"
        with self.assertRaisesRegex(ValueError, "interrupted"):
            execute_sql(self.database, sql, max_steps=10)
        self.assertEqual(ask(self.database, "count orders")["rows"], [[5]])


if __name__ == "__main__": unittest.main()
