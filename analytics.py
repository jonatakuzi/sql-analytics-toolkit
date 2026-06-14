"""
analytics.py — SQL Analytics Toolkit
Usage:  python analytics.py <command> [options]
Run:    python analytics.py --help
"""
import argparse
import csv
import os
import sqlite3
import sys

DB_FILE = ":memory:"
_conn = None


def get_conn(db=DB_FILE):
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(db)
        _conn.row_factory = sqlite3.Row
    return _conn


def close_conn():
    global _conn
    if _conn:
        _conn.close()
        _conn = None


def _infer_type(values):
    non_null = [v for v in values if v.strip()]
    if not non_null:
        return "TEXT"
    for v in non_null:
        try:
            int(v)
        except ValueError:
            break
    else:
        return "INTEGER"
    for v in non_null:
        try:
            float(v)
        except ValueError:
            break
    else:
        return "REAL"
    return "TEXT"


def cmd_import(args):
    path = args.file
    if not os.path.isfile(path):
        sys.exit(f"Error: file not found: {path}")
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None:
            sys.exit("Error: CSV has no header row.")
        fieldnames = list(reader.fieldnames)
        rows = list(reader)
    if not rows:
        print(f"Warning: {path} has no data rows.")
    sample = rows[:200]
    col_types = {col: _infer_type([r[col] for r in sample]) for col in fieldnames}
    table = args.table or os.path.splitext(os.path.basename(path))[0]
    conn = get_conn(args.db)
    cur = conn.cursor()
    col_defs = ", ".join(f'"{c}" {col_types[c]}' for c in fieldnames)
    cur.execute(f'DROP TABLE IF EXISTS "{table}"')
    cur.execute(f'CREATE TABLE "{table}" ({col_defs})')
    placeholders = ", ".join("?" for _ in fieldnames)
    cur.executemany(
        f'INSERT INTO "{table}" VALUES ({placeholders})',
        [[r[c] for c in fieldnames] for r in rows],
    )
    conn.commit()
    print(f"✓ Imported {len(rows):,} rows into table '{table}'")
    print(f"  Columns: {', '.join(f'{c} ({col_types[c]})' for c in fieldnames)}")


def cmd_query(args):
    conn = get_conn(args.db)
    try:
        cur = conn.execute(args.sql)
    except sqlite3.Error as exc:
        sys.exit(f"SQL error: {exc}")
    rows = cur.fetchall()
    if not rows:
        print("(no rows returned)")
        return
    cols = [d[0] for d in cur.description]
    widths = [max(len(c), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    sep = "  ".join("─" * w for w in widths)
    print(fmt.format(*cols))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(v) for v in row]))
    print(f"\n{len(rows):,} row(s)")
    if args.export:
        with open(args.export, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(cols)
            writer.writerows(rows)
        print(f"✓ Exported to {args.export}")


def cmd_run(args):
    if not os.path.isfile(args.sql_file):
        sys.exit(f"Error: file not found: {args.sql_file}")
    with open(args.sql_file, encoding="utf-8") as fh:
        sql = fh.read()
    conn = get_conn(args.db)
    try:
        conn.executescript(sql)
        conn.commit()
        print(f"✓ Executed {args.sql_file}")
    except sqlite3.Error as exc:
        sys.exit(f"SQL error: {exc}")


def cmd_tables(args):
    conn = get_conn(args.db)
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    rows = cur.fetchall()
    if not rows:
        print("(no tables found)")
        return
    print(f"{'Table':<30}  {'Rows':>8}")
    print("─" * 42)
    for row in rows:
        rc = get_conn(args.db).execute(f'SELECT COUNT(*) FROM "{row["name"]}"').fetchone()[0]
        print(f"{row['name']:<30}  {rc:>8,}")


def cmd_schema(args):
    conn = get_conn(args.db)
    cur = conn.execute(f'PRAGMA table_info("{args.table}")')
    cols = cur.fetchall()
    if not cols:
        sys.exit(f"Table '{args.table}' not found.")
    print(f"Schema: {args.table}")
    print(f"{'#':<4}  {'Column':<25}  {'Type':<10}  {'NotNull':<8}  {'Default'}")
    print("─" * 65)
    for c in cols:
        nn = "YES" if c["notnull"] else ""
        dflt = c["dflt_value"] or ""
        print(f"{c['cid']:<4}  {c['name']:<25}  {c['type']:<10}  {nn:<8}  {dflt}")


def cmd_repl(args):
    conn = get_conn(args.db)
    print("SQL Analytics Toolkit — interactive mode")
    print("  .tables   list tables    .schema <table>   show schema    .quit   exit\n")
    while True:
        try:
            sql = input("SQL> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not sql:
            continue
        if sql in {".quit", ".exit", "quit", "exit"}:
            break
        if sql == ".tables":
            cmd_tables(args)
            continue
        if sql.startswith(".schema "):
            args.table = sql.split(None, 1)[1]
            cmd_schema(args)
            continue
        try:
            cur = conn.execute(sql)
            rows = cur.fetchall()
            if rows:
                cols = [d[0] for d in cur.description]
                widths = [max(len(c), max((len(str(r[i])) for r in rows), default=0)) for i, c in enumerate(cols)]
                fmt = "  ".join(f"{{:<{w}}}" for w in widths)
                print(fmt.format(*cols))
                print("  ".join("─" * w for w in widths))
                for row in rows:
                    print(fmt.format(*[str(v) for v in row]))
                print(f"\n{len(rows):,} row(s)")
            else:
                conn.commit()
                print("OK")
        except sqlite3.Error as exc:
            print(f"Error: {exc}")


def build_parser():
    p = argparse.ArgumentParser(
        prog="analytics.py",
        description="SQL Analytics Toolkit — run SQL against CSV datasets",
    )
    p.add_argument("--db", default="analytics.db", metavar="FILE",
                   help="SQLite database file (default: analytics.db)")
    sub = p.add_subparsers(dest="command", required=True)

    pi = sub.add_parser("import", help="Import a CSV file into a table")
    pi.add_argument("file", help="Path to CSV file")
    pi.add_argument("--table", help="Table name (default: CSV filename)")

    pq = sub.add_parser("query", help="Run a SQL query")
    pq.add_argument("sql", help="SQL statement")
    pq.add_argument("--export", metavar="FILE", help="Export results to CSV")

    pr = sub.add_parser("run", help="Execute a .sql file")
    pr.add_argument("sql_file", help="Path to .sql file")

    sub.add_parser("tables", help="List all tables")

    ps = sub.add_parser("schema", help="Show table schema")
    ps.add_argument("table", help="Table name")

    sub.add_parser("repl", help="Interactive SQL shell")
    return p


def main():
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "import": cmd_import,
        "query":  cmd_query,
        "run":    cmd_run,
        "tables": cmd_tables,
        "schema": cmd_schema,
        "repl":   cmd_repl,
    }
    try:
        dispatch[args.command](args)
    finally:
        close_conn()


if __name__ == "__main__":
    main()
