# SQL Analytics Toolkit

A Python command-line tool for running SQL analytics against CSV datasets. Import any CSV into SQLite, write queries, aggregate results, and export reports — no database server required.

![Python](https://img.shields.io/badge/Python-3.7%2B-blue?logo=python&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-lightblue?logo=sqlite)
![Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Import CSV** files directly into SQLite tables — auto-detects column types
- **Run SQL queries** interactively or from `.sql` files
- **Aggregate and group** with full SQL support: SUM, AVG, COUNT, GROUP BY, JOIN, WHERE
- **Schema inspection** — list tables, view column names and types, check row counts
- **Export results** to CSV for sharing or further processing
- **REPL mode** — interactive SQL shell against your imported data
- Zero external dependencies — uses only Python's `sqlite3`, `csv`, and `argparse`

## Requirements

- Python 3.7+
- No `pip install` needed

## Installation

```bash
git clone https://github.com/jonatakuzi/sql-analytics-toolkit.git
cd sql-analytics-toolkit
```

## Usage

### Import a CSV file into SQLite
```bash
python analytics.py import sales.csv --table sales
python analytics.py import employees.csv --table employees
```

### Run a SQL query
```bash
python analytics.py query "SELECT department, COUNT(*), ROUND(AVG(salary),2) FROM employees GROUP BY department ORDER BY 3 DESC"
```
```
department       count    avg_salary
───────────────────────────────────────
Engineering      47       98412.00
Marketing        23       72100.00
Sales            31       65800.00
Support          19       58340.00
```

### Run a query from a .sql file
```bash
python analytics.py run queries/monthly_report.sql
```

### Inspect tables and schema
```bash
python analytics.py tables
python analytics.py schema employees
```

### Export query results to CSV
```bash
python analytics.py query "SELECT * FROM sales WHERE year=2024" --export results.csv
```

### Interactive SQL REPL
```bash
python analytics.py repl
```
```
SQL> SELECT name, salary FROM employees WHERE department='Engineering' LIMIT 5;
SQL> .tables
SQL> .quit
```

## Tech Stack

- Python 3.7+
- SQLite3 (built into Python stdlib)
- Standard library: `sqlite3`, `csv`, `argparse`, `os`
