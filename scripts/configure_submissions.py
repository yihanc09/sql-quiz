"""Create/check empty student submission storage after removal of legacy answers.

This does not restore deleted records, seed solutions, or change Auth accounts.
"""
import argparse
import psycopg

from sql_quiz.paths import SQL_DIR
from sql_quiz.runtime_config import backend_connection


def check_storage(conn):
    exists = conn.execute("SELECT to_regclass('public.quiz_submissions') IS NOT NULL").fetchone()[0]
    if not exists:
        raise ValueError('Run python -m scripts.configure_submissions --apply first.')
    checks = []
    for role in ('quiz_reader', 'anon'):
        for privilege in ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'):
            allowed = conn.execute('SELECT has_table_privilege(%s, %s, %s)',
                                   (role, 'public.quiz_submissions', privilege)).fetchone()[0]
            checks.append((f'{role}: no submission {privilege}', not allowed))
    for privilege in ('SELECT', 'INSERT', 'UPDATE'):
        allowed = conn.execute('SELECT has_table_privilege(%s, %s, %s)',
                               ('authenticated', 'public.quiz_submissions', privilege)).fetchone()[0]
        checks.append((f'authenticated: submission {privilege}', allowed))
    rls = conn.execute("SELECT relrowsecurity FROM pg_class WHERE oid='public.quiz_submissions'::regclass").fetchone()[0]
    checks.append(('submission RLS enabled', rls))
    count = conn.execute("SELECT count(*) FROM pg_policy WHERE polrelid='public.quiz_submissions'::regclass AND polname IN ('submission_select_own','submission_insert_own','submission_update_own')").fetchone()[0]
    checks.append(('three ownership policies present', count == 3))
    trigger = conn.execute("SELECT EXISTS (SELECT 1 FROM pg_trigger WHERE tgrelid='public.quiz_submissions'::regclass AND tgname='trg_quiz_answer_audit' AND tgenabled IN ('O','A'))").fetchone()[0]
    checks.append(('submission audit trigger enabled', trigger))
    for name, passed in checks:
        print(('PASS ' if passed else 'FAIL ') + name)
    if not all(passed for _, passed in checks):
        raise ValueError('Submission storage permission checks failed.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--apply', action='store_true')
    group.add_argument('--check', action='store_true')
    args = parser.parse_args()
    try:
        with backend_connection() as conn:
            if args.apply:
                conn.autocommit = True
                conn.execute((SQL_DIR / '003_submission_storage.sql').read_text(), prepare=False)
                print('Student submission storage configured; deleted records were not restored.')
            else:
                conn.execute('SET TRANSACTION READ ONLY')
            check_storage(conn)
    except (psycopg.Error, ValueError) as exc:
        print('Storage setup failed (' + type(exc).__name__ + '); credentials hidden.')
        raise SystemExit(1) from None


if __name__ == '__main__':
    main()
