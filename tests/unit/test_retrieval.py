"""Retrieval input/configuration contracts without native model dependencies."""
import json
from unittest.mock import Mock

import pytest
from sql_quiz import retrieval


@pytest.mark.parametrize('question,top_k', [('',5),('   ',5),(None,5),('x'*2001,5),('artists',True),('artists',0),('artists',9)])
def test_invalid_search_rejected_before_opening_index(question, top_k, monkeypatch):
    store = Mock()
    monkeypatch.setattr(retrieval, 'local_store', store)
    with pytest.raises(ValueError):
        retrieval.retrieve_knowledge(question,top_k)
    store.assert_not_called()


def test_fingerprint_tracks_content_and_not_document_order(tmp_path):
    path = tmp_path / 'documents.jsonl'
    docs = [{'id': name,'text': name,'metadata': {'kind':'schema','source':'schema.json'}} for name in ('a','b')]
    def write(records):
        path.write_text('\n'.join(json.dumps(r) for r in records))
    write(docs)
    _, original = retrieval.load_corpus(path)
    write(list(reversed(docs)))
    assert retrieval.load_corpus(path)[1] == original
    docs[0]['text'] = 'changed schema'
    write(docs)
    assert retrieval.load_corpus(path)[1] != original
    write([docs[0],docs[0]])
    with pytest.raises(ValueError,match='unique'):
        retrieval.load_corpus(path)


def test_local_mode_refused_on_vercel_before_any_native_import(monkeypatch):
    monkeypatch.setenv('VERCEL','1')
    client = Mock()
    monkeypatch.setattr(retrieval,'_local_client',client)
    with pytest.raises(retrieval.RetrievalUnavailable,match='Cloud Chroma'):
        retrieval.local_store(create=True)
    client.assert_not_called()
