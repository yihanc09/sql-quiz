"""RAG boundaries: retrieval precedes the API; secrets/answers stay out of prompts."""
import json
from unittest.mock import Mock

import httpx
import pytest

import sql_quiz.generation as generation


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(generation, 'load_dotenv', lambda *a, **kw: None)
    monkeypatch.setenv('OPENAI_API_KEY', 'private-test-credential')
    monkeypatch.setenv('OPENAI_MODEL', 'gpt-4.1-mini')
    return generation.load_ai_config()


@pytest.fixture
def retrieved():
    return {'question': 'Count artists', 'results': [
        {'id': 'schema.artist', 'text': 'public.artist (artist_id bigint, name text)',
         'metadata': {'source': 'data/schema.json', 'kind': 'schema'}, 'distance': .2}],
        'indexed_documents': 17}


def response(text='SELECT COUNT(*) FROM public.artist;', **changes):
    return {'status': 'completed', 'output': [
        {'type': 'reasoning', 'summary': []},
        {'type': 'message', 'content': [{'type': 'output_text', 'text': text}]}], **changes}


def test_missing_key_is_actionable_and_does_not_retrieve(monkeypatch):
    monkeypatch.setattr(generation, 'load_dotenv', lambda *a, **kw: None)
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    retrieve = Mock()
    monkeypatch.setattr(generation, 'retrieve_knowledge', retrieve)
    with pytest.raises(generation.GenerationUnavailable, match='OPENAI_API_KEY'):
        generation.generate_sql('Count artists')
    retrieve.assert_not_called()


def test_key_is_excluded_from_config_representation(configured):
    assert 'private-test-credential' not in repr(configured)


def test_question_validation_precedes_any_api_request(monkeypatch):
    completion = Mock()
    monkeypatch.setattr(generation, 'request_completion', completion)
    with pytest.raises(ValueError):
        generation.generate_sql(' ')
    completion.assert_not_called()


def test_generation_uses_actual_retrieval_before_model(configured, retrieved, monkeypatch):
    calls = []
    def retrieve(question, k):
        calls.append('retrieve')
        assert question == 'Count artists' and k == 3
        return retrieved
    def complete(config, messages):
        calls.append('model')
        context = json.loads(messages[1]['content'])
        assert context['retrieved_knowledge'][0]['text'] == retrieved['results'][0]['text']
        assert 'private-test-credential' not in json.dumps(messages)
        return 'SELECT COUNT(*) FROM public.artist;'
    monkeypatch.setattr(generation, 'retrieve_knowledge', retrieve)
    monkeypatch.setattr(generation, 'request_completion', complete)
    result = generation.generate_sql(' Count artists ', 3)
    assert calls == ['retrieve', 'model']
    assert result['retrieval'] is retrieved and result['executed'] is False
    assert result['model'] == configured.model


def test_no_silent_prompt_only_fallback(configured, monkeypatch):
    monkeypatch.setattr(generation, 'retrieve_knowledge', Mock(return_value={'results': []}))
    completion = Mock()
    monkeypatch.setattr(generation, 'request_completion', completion)
    with pytest.raises(generation.GenerationUnavailable, match='No knowledge'):
        generation.generate_sql('Count artists')
    completion.assert_not_called()


def test_official_responses_request_keeps_key_in_header(configured, retrieved, monkeypatch):
    post = Mock(return_value=httpx.Response(200, json=response()))
    monkeypatch.setattr(generation.httpx, 'post', post)
    assert generation.request_completion(configured, generation.build_messages('Count artists', retrieved)).startswith('SELECT')
    args, kwargs = post.call_args
    assert args == ('https://api.openai.com/v1/responses',)
    assert kwargs['json']['store'] is False
    assert kwargs['json']['max_output_tokens'] == 1200
    assert kwargs['follow_redirects'] is False
    assert kwargs['headers']['Authorization'] == 'Bearer private-test-credential'
    assert 'private-test-credential' not in json.dumps(kwargs['json'])
    assert post.call_count == 1


@pytest.mark.parametrize('status', [301, 400, 401, 403, 404, 429, 500])
def test_provider_errors_do_not_leak_response_secrets(configured, monkeypatch, status):
    monkeypatch.setattr(generation.httpx, 'post', Mock(return_value=httpx.Response(status, text='private-test-credential secret-provider-error')))
    with pytest.raises(generation.GenerationUnavailable) as error:
        generation.request_completion(configured, [{'content': 'rules'}, {'content': 'question'}])
    assert 'private-test-credential' not in str(error.value)
    assert 'secret-provider-error' not in str(error.value)


@pytest.mark.parametrize('error', [httpx.ReadTimeout('private-token'), httpx.ConnectError('private-token')])
def test_network_failures_are_sanitized(configured, monkeypatch, error):
    monkeypatch.setattr(generation.httpx, 'post', Mock(side_effect=error))
    with pytest.raises(generation.GenerationUnavailable) as failure:
        generation.request_completion(configured, [{'content': 'rules'}, {'content': 'question'}])
    assert 'private-token' not in str(failure.value)


@pytest.mark.parametrize('body', [response(status='incomplete'), response(''), response('DROP TABLE public.artist;'),
                                response('INSUFFICIENT_CONTEXT'), {'output': []},
                                response('SELECT 1', output=[{'type': 'message', 'content': [{'type': 'refusal'}]}])])
def test_incomplete_refusal_and_non_sql_output_are_rejected(body):
    with pytest.raises(generation.GenerationUnavailable):
        generation.extract_sql(body)


def test_sql_fences_and_leading_reasoning_item_are_supported():
    assert generation.extract_sql(response('```sql\nSELECT COUNT(*) FROM public.artist;\n```')) == 'SELECT COUNT(*) FROM public.artist;'
