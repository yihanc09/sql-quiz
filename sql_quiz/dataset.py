"""Typed Chinook CSV contract, local integrity checks, and safe SQL identifiers."""

import csv
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from psycopg import sql

from sql_quiz.paths import CSV_DIR, SCHEMA_PATH

SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding='utf-8'))
TABLES = {table['name']: table for table in SCHEMA['tables']}


def convert(value, column):
    if value == '':
        if not column['nullable']:
            raise ValueError(f"Required column {column['name']} is empty")
        return None
    kind = column['type']
    if kind in ('integer', 'bigint'):
        return int(value)
    if kind.startswith('numeric'):
        number = Decimal(value)
        if not number.is_finite() or number != number.quantize(Decimal('.01')):
            raise ValueError('Money values must be finite with at most two decimals')
        return number
    if kind == 'timestamp':
        # The supplied CSV uses YYYY/M/D; PostgreSQL uses typed timestamps.
        return datetime.strptime(value, '%Y/%m/%d')
    return value


def load_dataset(directory=CSV_DIR):
    """Validate headers, types, counts, unique keys, and every FK before writes."""
    directory = Path(directory)
    found = {p.stem for p in directory.glob('*.csv')}
    if found != set(TABLES):
        raise ValueError(f'Expected exactly these CSV tables: {sorted(TABLES)}')
    dataset = {}
    for name, table in TABLES.items():
        with (directory / f'{name}.csv').open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.reader(handle)
            columns = table['columns']
            if next(reader, None) != [col['name'] for col in columns]:
                raise ValueError(f'{name}: CSV headers differ from schema.json')
            rows = []
            for line, values in enumerate(reader, 2):
                try:
                    if len(values) != len(columns):
                        raise ValueError('Wrong column count')
                    rows.append(tuple(convert(v, c) for v, c in zip(values, columns)))
                except (ValueError, ArithmeticError) as exc:
                    raise ValueError(f'{name}: invalid row at CSV line {line}') from exc
        if len(rows) != table['row_count']:
            raise ValueError(f'{name}: expected {table["row_count"]} rows, got {len(rows)}')
        names = [col['name'] for col in columns]
        keys = [tuple(row[names.index(key)] for key in table['primary_key']) for row in rows]
        if len(set(keys)) != len(keys):
            raise ValueError(f'{name}: duplicate primary key')
        dataset[name] = rows
    for name, table in TABLES.items():
        names = [col['name'] for col in table['columns']]
        for col, target in table['foreign_keys'].items():
            parent, key = target.split('.')
            index = [c['name'] for c in TABLES[parent]['columns']].index(key)
            valid = {row[index] for row in dataset[parent]}
            if any(row[names.index(col)] is not None and row[names.index(col)] not in valid
                   for row in dataset[name]):
                raise ValueError(f'{name}.{col}: orphan foreign key')
    return dataset


def select_table(name):
    """Identifiers are composed separately from SQL/data values."""
    table = TABLES[name]
    return sql.SQL('SELECT {} FROM {}.{}').format(
        sql.SQL(', ').join(sql.Identifier(c['name']) for c in table['columns']),
        sql.Identifier(SCHEMA['schema']), sql.Identifier(name))


def compare_database(conn, dataset):
    """Compare all typed rows, not only counts or the five known answers."""
    report = []
    for name, rows in dataset.items():
        actual = conn.execute(select_table(name)).fetchall()
        expected_counts, actual_counts = Counter(rows), Counter(actual)
        report.append({'table': name, 'csv_rows': len(rows), 'database_rows': len(actual),
                       'matches': expected_counts == actual_counts,
                       'missing_rows': sum((expected_counts - actual_counts).values()),
                       'extra_rows': sum((actual_counts - expected_counts).values())})
    return report
