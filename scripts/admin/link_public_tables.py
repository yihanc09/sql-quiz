"""Validate uploaded public CSV tables and configure them for the quiz.

Default: read-only preflight. --apply: one transaction normalizes imported types,
adds missing PK/FK constraints, trims known city whitespace and grants the
restricted quiz reader SELECT on these 11 tables only. No tables are deleted.
"""
import argparse
from collections import Counter

from psycopg import sql
import psycopg

from sql_quiz.dataset import TABLES, convert, load_dataset
from sql_quiz.database import get_connection
from sql_quiz.runtime_config import backend_connection


def preflight(conn):
    expected = load_dataset()
    for name, table in TABLES.items():
        columns = table['columns']
        rows = conn.execute(sql.SQL('SELECT {} FROM public.{}').format(
            sql.SQL(', ').join(sql.Identifier(c['name']) for c in columns),
            sql.Identifier(name))).fetchall()
        normalized = []
        for row in rows:
            values = []
            for value, col in zip(row, columns):
                if value is None:
                    value = ''
                elif col['type'] == 'timestamp' and hasattr(value, 'strftime'):
                    value = value.strftime('%Y/%m/%d')
                else:
                    value = str(value)
                if col['name'] in ('city', 'billing_city'):
                    value = value.strip()
                values.append(convert(value, col))
            normalized.append(tuple(values))
        if Counter(normalized) != Counter(expected[name]):
            raise ValueError(f'public.{name}: uploaded values differ from the validated CSVs; stopped without replacing records.')
        print(f'public.{name}: {len(rows)} rows validated')


def configure(conn, role):
    conn.execute("SET LOCAL lock_timeout = '5s'")
    # Supabase CSV auto-detection inferred text dates and floating-point money.
    for name, column, kind in (
        ('employee', 'reports_to', 'integer'),
        ('employee', 'birth_date', 'timestamp'),
        ('employee', 'hire_date', 'timestamp'),
        ('invoice', 'invoice_date', 'timestamp'),
        ('invoice', 'total', 'numeric(10,2)'),
        ('invoice_line', 'unit_price', 'numeric(10,2)'),
        ('track', 'unit_price', 'numeric(10,2)'),
    ):
        conn.execute(sql.SQL('ALTER TABLE public.{} ALTER COLUMN {} TYPE {} USING NULLIF({}::text, \'\')::{}').format(
            sql.Identifier(name), sql.Identifier(column), sql.SQL(kind),
            sql.Identifier(column), sql.SQL(kind)))
    for name, col in (('customer', 'city'), ('invoice', 'billing_city')):
        conn.execute(sql.SQL('UPDATE public.{} SET {} = btrim({}) WHERE {} <> btrim({})').format(
            sql.Identifier(name), *[sql.Identifier(col)] * 4))
    for name, table in TABLES.items():
        for col in table['columns']:
            if not col['nullable']:
                conn.execute(sql.SQL('ALTER TABLE public.{} ALTER COLUMN {} SET NOT NULL').format(
                    sql.Identifier(name), sql.Identifier(col['name'])))
        primary = conn.execute(
            "SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conrelid = %s::regclass AND contype = 'p'",
            ('public.' + name,)).fetchall()
        desired = 'PRIMARY KEY (' + ', '.join(table['primary_key']) + ')'
        if primary and primary[0][0] != desired:
            raise ValueError(f'public.{name}: unexpected primary key; migration aborted.')
        if not primary:
            conn.execute(sql.SQL('ALTER TABLE public.{} ADD PRIMARY KEY ({})').format(
                sql.Identifier(name), sql.SQL(', ').join(map(sql.Identifier, table['primary_key']))))
        for column, target in table['foreign_keys'].items():
            parent, key = target.split('.')
            constraint = f'quiz_link_{name}_{column}_fk'
            if not conn.execute('SELECT 1 FROM pg_constraint WHERE conrelid = %s::regclass AND conname = %s',
                                ('public.' + name, constraint)).fetchone():
                conn.execute(sql.SQL('ALTER TABLE public.{} ADD CONSTRAINT {} FOREIGN KEY ({}) REFERENCES public.{} ({})').format(
                    sql.Identifier(name), sql.Identifier(constraint), sql.Identifier(column),
                    sql.Identifier(parent), sql.Identifier(key)))
    conn.execute(sql.SQL('GRANT USAGE ON SCHEMA public TO {}').format(sql.Identifier(role)))
    for name in TABLES:
        conn.execute(sql.SQL('GRANT SELECT ON public.{} TO {}').format(sql.Identifier(name), sql.Identifier(role)))
        # Supabase enables RLS on imported public tables. A SQL GRANT alone
        # permits the statement but returns zero visible rows without a policy.
        if not conn.execute(
            'SELECT 1 FROM pg_policy WHERE polrelid = %s::regclass AND polname = %s',
            ('public.' + name, 'quiz_reader_select')).fetchone():
            conn.execute(sql.SQL('CREATE POLICY quiz_reader_select ON public.{} FOR SELECT TO {} USING (true)').format(
                sql.Identifier(name), sql.Identifier(role)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        with get_connection() as reader:
            reader.execute('SET TRANSACTION READ ONLY')
            role = reader.execute('SELECT current_user').fetchone()[0]
        if role != 'quiz_reader':
            raise ValueError('Expected the existing restricted quiz_reader role; stopped before granting access.')
        with backend_connection() as conn:
            if args.apply:
                # Keep the preflight snapshot stable until constraints and grants commit.
                for name in TABLES:
                    conn.execute(sql.SQL('LOCK TABLE public.{} IN ACCESS EXCLUSIVE MODE NOWAIT').format(sql.Identifier(name)))
            else:
                conn.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY')
            preflight(conn)
            if args.apply:
                configure(conn, role)
                preflight(conn)
        print('Public quiz tables configured.' if args.apply else 'Preflight passed; no changes made.')
    except psycopg.Error:
        raise SystemExit('Database operation failed; transaction rolled back. Check connection, table types and permissions; credentials hidden.') from None
    except ValueError as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
