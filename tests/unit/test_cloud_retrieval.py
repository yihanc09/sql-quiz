"""Cloud transport/model contracts, without real credentials or billed calls."""
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest

from sql_quiz import cloud_retrieval as cloud
from sql_quiz import retrieval


@pytest.fixture
def settings(monkeypatch):
    monkeypatch.setattr(cloud, 'load_dotenv', lambda *a, **kw: None)
    monkeypatch.setattr(retrieval, 'load_dotenv', lambda *a, **kw: None)
    for key, value in {'CHROMA_API_KEY': 'private-chroma', 'CHROMA_TENANT': 'tenant',
                       'CHROMA_DATABASE': 'quiz', 'CHROMA_HOST': 'api.trychroma.com',
                       'OPENAI_API_KEY': 'private-openai'}.items():
        monkeypatch.setenv(key, value)
    return monkeypatch


def test_incomplete_config_stops_before_network(settings):
    settings.delenv('CHROMA_API_KEY')
    client = Mock()
    settings.setattr(cloud, '_cloud_client', client)
    with pytest.raises(retrieval.RetrievalUnavailable, match='CHROMA_API_KEY'):
        cloud.cloud_store()
    client.assert_not_called()


@pytest.mark.parametrize('host', ['https://api.trychroma.com', 'evil.example.com',
                                 'api.trychroma.com/steal', 'api.trychroma.com.evil.com'])
def test_key_cannot_be_sent_to_non_cloud_host(settings, host):
    settings.setenv('CHROMA_HOST', host)
    with pytest.raises(retrieval.RetrievalUnavailable, match='hostname'):
        cloud.load_cloud_config()


def test_cloud_secrets_not_in_config_repr(settings):
    config = cloud.load_cloud_config()
    assert 'private-chroma' not in repr(config) and 'private-openai' not in repr(config)


def test_cloud_uses_separate_model_collection_and_spann(settings):
    client = Mock()
    settings.setattr(cloud, '_cloud_client', Mock(return_value=client))
    store = cloud.cloud_store()
    assert store.client is client
    assert store.model_name == 'text-embedding-3-small' and store.dimensions == 1536
    assert store.collection_name != retrieval.COLLECTION_NAME
    assert store.backend == 'cloud' and store.configuration == {'spann': {'space': 'cosine'}}


def test_embedding_response_reordered_by_index_and_dimension_checked(settings):
    vectors = [{'index': i, 'embedding': [float(i)] * 1536} for i in (1, 0)]
    post = Mock(return_value=httpx.Response(200, json={'data': vectors}))
    settings.setattr(cloud.httpx, 'post', post)
    assert cloud.openai_embeddings(['a', 'b'], 'private-openai')[0][0] == 0
    args, kw = post.call_args
    assert args[0] == 'https://api.openai.com/v1/embeddings'
    assert kw['json']['dimensions'] == 1536 and kw['json']['model'] == cloud.CLOUD_MODEL
    assert kw['follow_redirects'] is False
    assert 'private-openai' not in str(kw['json'])


@pytest.mark.parametrize('data', [[], [{'index': 0, 'embedding': [1, 2]}],
                                 [{'index': 1, 'embedding': [1] * 1536}],
                                 [{'index': 0, 'embedding': [float('inf')] * 1536}]])
def test_malformed_embedding_output_is_rejected(settings, data):
    reply = Mock(status_code=200)
    reply.json.return_value = {'data': data}
    settings.setattr(cloud.httpx, 'post', Mock(return_value=reply))
    with pytest.raises(retrieval.RetrievalUnavailable, match='invalid vectors'):
        cloud.openai_embeddings(['a'], 'key')


@pytest.mark.parametrize('status', [301, 401, 403, 429, 500])
def test_embedding_api_errors_hide_provider_body(settings, status):
    settings.setattr(cloud.httpx, 'post', Mock(return_value=httpx.Response(status, text='private-body')))
    with pytest.raises(retrieval.RetrievalUnavailable) as exc:
        cloud.openai_embeddings(['a'], 'private-openai')
    assert 'private-body' not in str(exc.value) and 'private-openai' not in str(exc.value)


def test_cloud_connection_failure_hides_credentials(settings):
    settings.setattr(cloud, '_cloud_client', Mock(side_effect=RuntimeError('private-chroma')))
    with pytest.raises(retrieval.RetrievalUnavailable) as exc:
        cloud.cloud_store()
    assert 'private-chroma' not in str(exc.value)


def test_vercel_defaults_to_cloud_and_never_falls_back_to_local(settings):
    settings.setenv('VERCEL', '1')
    settings.delenv('CHROMA_MODE', raising=False)
    local = Mock()
    settings.setattr(retrieval, 'local_store', local)
    remote = Mock(return_value=SimpleNamespace(backend='cloud'))
    settings.setattr(cloud, 'cloud_store', remote)
    assert retrieval.configured_store().backend == 'cloud'
    local.assert_not_called()
    settings.setattr(cloud, 'cloud_store', Mock(side_effect=retrieval.RetrievalUnavailable('offline')))
    with pytest.raises(retrieval.RetrievalUnavailable, match='offline'):
        retrieval.configured_store()
    local.assert_not_called()


def test_explicit_local_mode_stays_local(settings):
    settings.setenv('CHROMA_MODE', 'local')
    local = Mock(return_value='local')
    settings.setattr(retrieval, 'local_store', local)
    assert retrieval.configured_store() == 'local'
