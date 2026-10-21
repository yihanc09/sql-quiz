"""Student work uses its own table; instructor reference queries stay separate."""
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sql_quiz import auth


@pytest.mark.parametrize('operation', ['load', 'draft', 'grade'])
def test_persistence_uses_student_submission_table(operation):
    client = Mock()
    table = client.table.return_value
    table.select.return_value.eq.return_value.execute.return_value = SimpleNamespace(data=[])
    if operation == 'load':
        assert auth.load_answer_records(client, 'user') == {}
    elif operation == 'draft':
        auth.save_answer(client, 'user', 1, 'SELECT 1')
    else:
        auth.save_graded_answer(client, 'user', 1, 'SELECT 1', 4, True)
    client.table.assert_called_once_with('quiz_submissions')
