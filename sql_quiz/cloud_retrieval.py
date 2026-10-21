"""Chroma Cloud storage with explicit OpenAI embeddings; no local model files."""
import math
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache

import httpx
from dotenv import load_dotenv

from sql_quiz.paths import PROJECT_ROOT
from sql_quiz.retrieval import KnowledgeStore, RetrievalUnavailable

CLOUD_MODEL = 'text-embedding-3-small'
CLOUD_DIMENSIONS = 1536
CLOUD_COLLECTION = 'chinook_knowledge_openai3small_v1'


@dataclass(frozen=True)
class CloudConfig:
    tenant: str
    database: str
    host: str
    api_key: str = field(repr=False)
    openai_key: str = field(repr=False)


def load_cloud_config():
    load_dotenv(PROJECT_ROOT / '.env')
    values = {key: os.getenv(key, '').strip() for key in
              ('CHROMA_API_KEY', 'CHROMA_TENANT', 'CHROMA_DATABASE', 'OPENAI_API_KEY')}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise RetrievalUnavailable('Cloud retrieval needs backend settings: ' + ', '.join(missing) + '.')
    host = os.getenv('CHROMA_HOST', 'api.trychroma.com').strip()
    # Never send Chroma credentials to an arbitrary URL supplied by a request.
    if not re.fullmatch(r'(?:[a-z0-9-]+\.)+trychroma\.com', host):
        raise RetrievalUnavailable('CHROMA_HOST must be the Chroma Cloud hostname from its Connect panel (without https:// or a path).')
    return CloudConfig(values['CHROMA_TENANT'], values['CHROMA_DATABASE'], host,
                       values['CHROMA_API_KEY'], values['OPENAI_API_KEY'])


def openai_embeddings(texts, api_key):
    try:
        response = httpx.post(
            'https://api.openai.com/v1/embeddings',
            headers={'Authorization': 'Bearer ' + api_key},
            json={'model': CLOUD_MODEL, 'input': texts, 'dimensions': CLOUD_DIMENSIONS,
                  'encoding_format': 'float'},
            timeout=httpx.Timeout(20.0, connect=10.0), follow_redirects=False)
    except httpx.RequestError:
        raise RetrievalUnavailable('Could not reach the OpenAI embedding API. Check your network and retry.') from None
    if response.status_code in (401, 403):
        raise RetrievalUnavailable('OpenAI embedding access was rejected. Check OPENAI_API_KEY and model permissions.')
    if response.status_code == 429:
        raise RetrievalUnavailable('The OpenAI embedding rate or quota limit was reached. Please retry later.')
    if not 200 <= response.status_code < 300:
        raise RetrievalUnavailable('The OpenAI embedding service is unavailable. Please retry later.')
    try:
        data = response.json()['data']
        if len(data) != len(texts) or sorted(item['index'] for item in data) != list(range(len(texts))):
            raise ValueError()
        vectors = [item['embedding'] for item in sorted(data, key=lambda item: item['index'])]
        if any(len(v) != CLOUD_DIMENSIONS or any(not math.isfinite(float(n)) for n in v) for v in vectors):
            raise ValueError()
        return vectors
    except (KeyError, TypeError, ValueError):
        raise RetrievalUnavailable('The embedding service returned invalid vectors. No index update was applied.') from None


@lru_cache(maxsize=2)
def _cloud_client(tenant, database, host, api_key):
    import chromadb
    from chromadb.config import Settings
    return chromadb.CloudClient(tenant=tenant, database=database, api_key=api_key,
                                cloud_host=host, cloud_port=443, enable_ssl=True,
                                settings=Settings(anonymized_telemetry=False))


def cloud_store():
    config = load_cloud_config()
    try:
        client = _cloud_client(config.tenant, config.database, config.host, config.api_key)
    except ImportError:
        raise RetrievalUnavailable('Install cloud dependencies with python -m pip install -r requirements.txt.') from None
    except Exception:
        raise RetrievalUnavailable('Could not connect to Chroma Cloud. Check the API key, tenant, database and region hostname.') from None
    return KnowledgeStore(client, lambda texts: openai_embeddings(texts, config.openai_key),
                          collection_name=os.getenv('CHROMA_CLOUD_COLLECTION', CLOUD_COLLECTION),
                          model_name=CLOUD_MODEL, dimensions=CLOUD_DIMENSIONS,
                          configuration={'spann': {'space': 'cosine'}}, backend='cloud',
                          index_command='.venv/bin/python -m scripts.index_knowledge --cloud')
