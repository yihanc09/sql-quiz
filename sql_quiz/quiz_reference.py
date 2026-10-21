"""Execute instructor reference SQL against the live, restricted quiz database."""

from sql_quiz.database import run_query
from sql_quiz.quiz import get_questions


def get_live_reference(question_id, execute=None):
    """Never load a saved result table or a student's saved submission.

    The reference SQL defines the question. Its result is fetched anew on each
    hint refresh and grading attempt, using the same reader as student queries.
    Exceptions deliberately propagate; no stale-file fallback awards a grade.
    """
    question = next((q for q in get_questions() if q['id'] == question_id), None)
    if type(question_id) is not int or question is None:
        raise ValueError('Unknown question ID.')
    result = (execute or run_query)(question['expected_sql'])
    return {
        'question_id': question_id,
        'expected_sql': question['expected_sql'].strip(),
        'columns': list(result.columns),
        'rows': [list(row) for row in result.itertuples(index=False, name=None)],
        'source': 'live_database',
        'schema': 'public',
    }
