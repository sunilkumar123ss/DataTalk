# DataTalk

**A constrained question-to-SQL reference with an inspectable execution policy.**

DataTalk maps four explicit question patterns onto parameterized SQL and executes them against a read-only SQLite connection. It prints the generated SQL, bound parameters, result columns, row truncation flag and executed VM-step count. The default database is created temporarily from synthetic orders and removed afterwards.

## Run

Python 3.9+ · standard library only.

```sh
python3 main.py
python3 main.py "count orders"
python3 main.py "total revenue"
python3 main.py "orders with status pending" --row-limit 5
python3 main.py "top 2 products"
python3 main.py --help
python3 -m unittest discover -s . -p 'test_main.py' -v
```

Default demo and help work from any working directory. The fixture path is anchored beside the script. To query a **trusted** existing database with the documented `orders(id, product, status, amount_cents)` schema, pass `--database /path/to/orders.sqlite`.

## Query contract

| Question | Meaning |
| --- | --- |
| `count orders` | Count all orders |
| `total revenue` | Sum integer cents for paid orders; integer zero when none exist |
| `orders with status paid/pending/cancelled` | List matching orders by ID |
| `top N products` | Paid revenue by product, descending; N is 1–20 |

The slash-separated status examples in the table indicate alternatives; supply one literal status. Unsupported wording is rejected rather than guessed. Status and limit values use bound parameters. The synthetic fixture returns 5 orders and 2,700 cents in paid revenue.

## Execution controls

The database opens with URI `mode=ro`. A SQLite authorizer allows only SELECT, reads of the four allowed `orders` columns, and `count`/`sum`/`coalesce`; empty-column reads needed by `COUNT(*)` are handled explicitly. `COALESCE` makes total revenue integer zero when no paid orders exist. Other tables, writes, PRAGMAs, attachments and unapproved functions are denied. SQLite's single-statement API rejects multiple statements.

A progress handler checks every virtual-machine instruction and interrupts after the configured step budget. A result cap returns at most `--row-limit` rows and reports whether additional rows existed. Connections are closed in a `finally` block on both success and error. The database lock timeout is 0.25 seconds.

Nine tests cover aggregates, integer-zero revenue when no paid orders exist, parameterized queries, unsupported/injected questions, writes, private tables, PRAGMAs, attachments, multiple statements, unapproved functions, row truncation and actual VM-budget interruption.

## Boundaries

The tests validate the documented grammar and execution controls; they do not establish general text-to-SQL accuracy.

This is a finite grammar, not general LLM text-to-SQL. It has no OpenAI, FAISS, PostgreSQL, schema-retrieval or EXPLAIN-plan adapter. The SQLite database and schema must be trusted: this is not process isolation for hostile database files. VM steps are not a wall-clock, byte or memory limit, and a permitted row or aggregate can still be large. The row cap does not reduce all work needed to sort or aggregate. Production use needs an isolated worker, cancellation, explicit resource limits and reviewed data-access policies.

## Repository checks

```sh
python3 verify.py
```

This runs the isolated test suite, synthetic example, and CLI help. The `verify.yml.template` file contains an optional GitHub Actions workflow. Place it at `.github/workflows/verify.yml` to enable hosted checks; the current repository is verified locally.
