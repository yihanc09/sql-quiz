"""Retrieval corpus consistency and exclusion of grading/private records."""

import json

from scripts.build_knowledge import OUTPUT, build_documents
from sql_quiz.dataset import TABLES

def test_knowledge_is_current_and_excludes_quiz_answers_and_user_records():
    documents = build_documents()
    committed = [json.loads(line) for line in OUTPUT.read_text(encoding='utf-8').splitlines()]
    assert committed == documents
    assert len({doc['id'] for doc in documents}) == len(documents)
    assert {doc['metadata']['table'] for doc in documents if doc['metadata']['kind'] == 'schema'} == {
        f'public.{name}' for name in TABLES}
    corpus = '\n'.join(doc['text'] for doc in documents)
    assert 'quiz_answers' not in corpus
    assert 'quiz_submissions' not in corpus
    assert 'quiz_private' not in corpus
    from sql_quiz.quiz import get_questions
    assert all(question['expected_sql'].strip() not in corpus for question in get_questions())
