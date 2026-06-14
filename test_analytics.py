"""
test_analytics.py — tests for SQL Analytics Toolkit
Run:  pytest test_analytics.py -v
"""
import csv
import os
import sqlite3
import pytest
import analytics as mod


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    mod._conn = None
    db = str(tmp_path / "test.db")
    yield db
    mod._conn = None


def _make_csv(tmp_path, name, rows, header=None):
    path = tmp_path / name
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        if header:
            w.writerow(header)
        w.writerows(rows)
    return str(path)


# ── type inference ─────────────────────────────────────────────────────────────

def test_infer_integer():
    assert mod._infer_type(["1", "2", "3"]) == "INTEGER"

def test_infer_real():
    assert mod._infer_type(["1.1", "2.2"]) == "REAL"

def test_infer_text():
    assert mod._infer_type(["hello", "world"]) == "TEXT"

def test_infer_empty():
    assert mod._infer_type(["", "  "]) == "TEXT"

def test_infer_mixed():
    assert mod._infer_type(["1", "two", "3"]) == "TEXT"


# ── import ─────────────────────────────────────────────────────────────────────

class TestImport:
    def test_basic_import(self, tmp_path, fresh_db, capsys):
        path = _make_csv(tmp_path, "data.csv",
                         [["Alice", "30", "75000.50"], ["Bob", "25", "62000.00"]],
                         header=["name", "age", "salary"])
        args = mod.build_parser().parse_args(["--db", fresh_db, "import", path])
        mod.cmd_import(args)
        out = capsys.readouterr().out
        assert "2" in out
        conn = sqlite3.connect(fresh_db)
        rows = conn.execute("SELECT * FROM data").fetchall()
        assert len(rows) == 2
        conn.close()

    def test_custom_table_name(self, tmp_path, fresh_db, capsys):
        path = _make_csv(tmp_path, "sales.csv", [["1", "100"]], header=["id", "amount"])
        args = mod.build_parser().parse_args(["--db", fresh_db, "import", path, "--table", "revenue"])
        mod.cmd_import(args)
        conn = sqlite3.connect(fresh_db)
        row = conn.execute("SELECT COUNT(*) FROM revenue").fetchone()
        assert row[0] == 1
        conn.close()

    def test_missing_file_exits(self, fresh_db):
        args = mod.build_parser().parse_args(["--db", fresh_db, "import", "/nonexistent.csv"])
        with pytest.raises(SystemExit):
            mod.cmd_import(args)

    def test_column_type_inference(self, tmp_path, fresh_db, capsys):
        path = _make_csv(tmp_path, "types.csv",
                         [["42", "3.14", "hello"]],
                         header=["an_int", "a_float", "a_str"])
        args = mod.build_parser().parse_args(["--db", fresh_db, "import", path])
        mod.cmd_import(args)
        conn = sqlite3.connect(fresh_db)
        info = conn.execute("PRAGMA table_info(types)").fetchall()
        types = {row[1]: row[2] for row in info}
        assert types["an_int"] == "INTEGER"
        assert types["a_float"] == "REAL"
        assert types["a_str"] == "TEXT"
        conn.close()


# ── query ──────────────────────────────────────────────────────────────────────

class TestQuery:
    def _setup(self, tmp_path, db):
        path = _make_csv(tmp_path, "emp.csv",
                         [["Alice", "Engineering", "90000"],
                          ["Bob", "Marketing", "65000"],
                          ["Carol", "Engineering", "95000"]],
                         header=["name", "dept", "salary"])
        args = mod.build_parser().parse_args(["--db", db, "import", path])
        mod.cmd_import(args)

    def test_select_all(self, tmp_path, fresh_db, capsys):
        self._setup(tmp_path, fresh_db)
        args = mod.build_parser().parse_args(["--db", fresh_db, "query", "SELECT * FROM emp"])
        mod.cmd_query(args)
        out = capsys.readouterr().out
        assert "Alice" in out

    def test_aggregate(self, tmp_path, fresh_db, capsys):
        self._setup(tmp_path, fresh_db)
        args = mod.build_parser().parse_args(
            ["--db", fresh_db, "query",
             "SELECT dept, COUNT(*) c FROM emp GROUP BY dept ORDER BY dept"])
        mod.cmd_query(args)
        out = capsys.readouterr().out
        assert "Engineering" in out
        assert "2" in out

    def test_no_rows(self, tmp_path, fresh_db, capsys):
        self._setup(tmp_path, fresh_db)
        args = mod.build_parser().parse_args(
            ["--db", fresh_db, "query", "SELECT * FROM emp WHERE name='Nobody'"])
        mod.cmd_query(args)
        out = capsys.readouterr().out
        assert "no rows" in out

    def test_export_csv(self, tmp_path, fresh_db, capsys):
        self._setup(tmp_path, fresh_db)
        export_path = str(tmp_path / "out.csv")
        args = mod.build_parser().parse_args(
            ["--db", fresh_db, "query", "SELECT * FROM emp", "--export", export_path])
        mod.cmd_query(args)
        assert os.path.isfile(export_path)
        with open(export_path) as f:
            assert "Alice" in f.read()

    def test_bad_sql_exits(self, tmp_path, fresh_db):
        args = mod.build_parser().parse_args(
            ["--db", fresh_db, "query", "SELECT * FROM nonexistent_table"])
        with pytest.raises(SystemExit):
            mod.cmd_query(args)


# ── tables / schema ────────────────────────────────────────────────────────────

class TestMeta:
    def test_tables_empty(self, fresh_db, capsys):
        args = mod.build_parser().parse_args(["--db", fresh_db, "tables"])
        mod.cmd_tables(args)
        assert "no tables" in capsys.readouterr().out

    def test_tables_after_import(self, tmp_path, fresh_db, capsys):
        path = _make_csv(tmp_path, "items.csv", [["a", "1"]], header=["name", "qty"])
        mod.cmd_import(mod.build_parser().parse_args(["--db", fresh_db, "import", path]))
        mod.cmd_tables(mod.build_parser().parse_args(["--db", fresh_db, "tables"]))
        assert "items" in capsys.readouterr().out

    def test_schema(self, tmp_path, fresh_db, capsys):
        path = _make_csv(tmp_path, "products.csv", [["widget", "9.99"]], header=["name", "price"])
        mod.cmd_import(mod.build_parser().parse_args(["--db", fresh_db, "import", path]))
        args = mod.build_parser().parse_args(["--db", fresh_db, "schema", "products"])
        mod.cmd_schema(args)
        out = capsys.readouterr().out
        assert "name" in out and "price" in out

    def test_schema_missing_table_exits(self, fresh_db):
        args = mod.build_parser().parse_args(["--db", fresh_db, "schema", "ghost"])
        with pytest.raises(SystemExit):
            mod.cmd_schema(args)
