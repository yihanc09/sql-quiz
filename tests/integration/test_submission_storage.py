"""The actual query reader cannot access or edit student submissions."""
import pytest
from sql_quiz.database import run_query


@pytest.mark.parametrize('privilege', ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'TRUNCATE'])
def test_reader_has_no_submission_privileges(privilege):
    result = run_query('SELECT has_table_privilege(current_user, %s, %s) AS allowed',
                       ('public.quiz_submissions', privilege))
    assert not bool(result.iloc[0]['allowed'])
