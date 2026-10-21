"""Hosted integration checks: all five questions use the uploaded public tables."""

import pytest

from sql_quiz.database import run_query
from sql_quiz.grading import grade_result
from sql_quiz.quiz import get_questions
from sql_quiz.quiz_reference import get_live_reference
from sql_quiz.dataset import TABLES


@pytest.mark.parametrize('question', get_questions(), ids=lambda q: str(q['id']))
def test_reference_executes_and_grades_live(question):
    assert 'public.' in question['expected_sql']
    assert 'chinook.' not in question['expected_sql']
    live = get_live_reference(question['id'])
    actual = run_query(question['expected_sql'])
    assert grade_result(question['id'], actual, {str(question['id']): live})[0]
    assert live['source'] == 'live_database'
    assert live['rows']
    assert live['columns'] == list(actual.columns)


@pytest.mark.parametrize('table', TABLES)
def test_reader_can_query_each_uploaded_table(table):
    from psycopg import sql
    statement = sql.SQL('SELECT COUNT(*) AS n FROM public.{}').format(sql.Identifier(table)).as_string()
    assert int(run_query(statement).iloc[0]['n']) == TABLES[table]['row_count']
