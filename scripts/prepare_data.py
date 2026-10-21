"""Validate CSVs; optionally compare or bootstrap the hosted Chinook schema.

Default mode never connects to the database. --check-db is read-only.
--apply creates absent tables and fills only empty tables in one transaction;
existing nonempty tables must exactly match the CSVs or the operation rolls back.
"""

import argparse
import json

import psycopg
from psycopg import sql

from sql_quiz.dataset import TABLES, compare_database, load_dataset, select_table
from sql_quiz.runtime_config import backend_connection


def bootstrap(conn, dataset):
    conn.execute('SET LOCAL lock_timeout = \'5s\'')
    conn.execute('CREATE SCHEMA IF NOT EXISTS public')
    for name, table in TABLES.items():
        definitions = []
        for col in table['columns']:
            definitions.append(sql.SQL('{} {} {}').format(
                sql.Identifier(col['name']), sql.SQL(col['type']),
                sql.SQL('' if col['nullable'] else 'NOT NULL')))
        definitions.append(sql.SQL('PRIMARY KEY ({})').format(
            sql.SQL(', ').join(map(sql.Identifier, table['primary_key']))))
        for col, target in table['foreign_keys'].items():
            parent, key = target.split('.')
            definitions.append(sql.SQL('FOREIGN KEY ({}) REFERENCES public.{} ({})').format(
                sql.Identifier(col), sql.Identifier(parent), sql.Identifier(key)))
        conn.execute(sql.SQL('CREATE TABLE IF NOT EXISTS public.{} ({})').format(
            sql.Identifier(name), sql.SQL(', ').join(definitions)))
        conn.execute(sql.SQL('LOCK TABLE public.{} IN SHARE ROW EXCLUSIVE MODE').format(sql.Identifier(name)))
        existing = conn.execute(select_table(name)).fetchall()
        if existing:
            from collections import Counter
            if Counter(existing) != Counter(dataset[name]):
                raise ValueError(f'{name}: existing data differs; no data was overwritten. Investigate with --check-db.')
            continue
        columns = table['columns']
        insert = sql.SQL('INSERT INTO public.{} ({}) VALUES ({})').format(
            sql.Identifier(name),
            sql.SQL(', ').join(sql.Identifier(c['name']) for c in columns),
            sql.SQL(', ').join(sql.Placeholder() for _ in columns))
        with conn.cursor() as cursor:
            cursor.executemany(insert, dataset[name])
    # A new project still needs a separately configured restricted role and Auth.
    # Never grant new data to PUBLIC or to the privileged backend user as a reader.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument('--check-db', action='store_true')
    mode.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    dataset = load_dataset()
    print(f'Validated {len(dataset)} CSV tables, {sum(map(len, dataset.values()))} rows, types, PKs and FKs.')
    if not (args.check_db or args.apply):
        return
    try:
        with backend_connection() as conn:
            if args.apply:
                bootstrap(conn, dataset)
            else:
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            report = compare_database(conn, dataset)
            print(json.dumps(report, indent=2))
            if not all(row['matches'] for row in report):
                raise ValueError('Database and CSV differ. No existing rows have been replaced.')
    except ValueError as exc:
        raise SystemExit(str(exc)) from None
    except psycopg.Error:
        raise SystemExit('Database operation failed; transaction rolled back. Check connection, schema and permissions (credentials hidden).') from None


if __name__ == '__main__':
    main()
