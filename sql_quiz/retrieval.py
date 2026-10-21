"""Local or cloud semantic retrieval over the curated Chinook knowledge corpus.

Chroma stores explicit dense embeddings. Querying never executes SQL or looks
up a quiz answer. Native/model dependencies are loaded only for this feature.
"""
import hashlib
import json
import math
import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from sql_quiz.paths import PROJECT_ROOT, KNOWLEDGE_PATH

MODEL_NAME = 'all-MiniLM-L6-v2'
DIMENSIONS = 384
COLLECTION_NAME = 'chinook_knowledge_minilm_v1'
INDEX_COMMAND = '.venv/bin/python -m scripts.index_knowledge'


class RetrievalUnavailable(RuntimeError):
    """An actionable retrieval error safe to display without internal details."""


def validate_question(question, top_k=5):
    if not isinstance(question, str) or not question.strip() or len(question) > 2000:
        raise ValueError('Enter a natural-language question between 1 and 2000 characters.')
    if type(top_k) is not int or not 1 <= top_k <= 8:
        raise ValueError('top_k must be an integer between 1 and 8.')
    return question.strip()


def load_corpus(path=KNOWLEDGE_PATH):
    documents = [json.loads(line) for line in Path(path).read_text(encoding='utf-8').splitlines() if line.strip()]
    ids = set()
    if not documents:
        raise ValueError('The knowledge corpus is empty; rebuild it first.')
    for doc in documents:
        if not isinstance(doc.get('id'), str) or not doc['id'] or doc['id'] in ids:
            raise ValueError('Knowledge document IDs must be nonempty and unique.')
        if not isinstance(doc.get('text'), str) or not doc['text'].strip():
            raise ValueError('Each knowledge document must contain text.')
        metadata = doc.get('metadata')
        if not isinstance(metadata, dict) or not metadata.get('source') or not metadata.get('kind'):
            raise ValueError('Each knowledge document must have source and kind metadata.')
        if any(not isinstance(value, (str, int, float, bool)) for value in metadata.values()):
            raise ValueError('Knowledge metadata must contain flat scalar values.')
        ids.add(doc['id'])
    canonical = json.dumps(sorted(documents, key=lambda d: d['id']), sort_keys=True, ensure_ascii=False)
    return documents, hashlib.sha256(canonical.encode()).hexdigest()


class KnowledgeStore:
    """A testable Chroma index with explicit embedding-model/corpus contracts."""

    def __init__(self, client, embed, collection_name=COLLECTION_NAME,
                 model_name=MODEL_NAME, dimensions=DIMENSIONS, configuration=None,
                 backend='local', index_command=INDEX_COMMAND):
        self.client, self.embed = client, embed
        self.collection_name, self.model_name = collection_name, model_name
        self.dimensions = dimensions
        self.configuration = configuration or {'hnsw': {'space': 'cosine'}}
        self.backend, self.index_command = backend, index_command

    def _vectors(self, texts):
        vectors = self.embed(texts)
        if len(vectors) != len(texts) or any(
            len(vector) != self.dimensions or any(not math.isfinite(float(v)) for v in vector)
            for vector in vectors
        ):
            raise RetrievalUnavailable('Embedding output does not match the configured model dimensions.')
        return vectors

    def _check_model(self, metadata):
        if metadata.get('embedding_model') != self.model_name or metadata.get('dimensions') != self.dimensions:
            raise RetrievalUnavailable('Index embedding model changed. Use a new collection and rebuild it.')

    def index(self, documents, fingerprint):
        # Embed first: a model/download failure leaves an existing ready index intact.
        vectors = self._vectors([doc['text'] for doc in documents])
        collection = self.client.get_or_create_collection(
            name=self.collection_name, embedding_function=None,
            configuration=self.configuration,
        )
        if collection.count():
            self._check_model(collection.metadata or {})
        metadata = {'embedding_model': self.model_name, 'dimensions': self.dimensions,
                    'metric': 'cosine', 'corpus_sha256': fingerprint, 'ready': False}
        collection.modify(metadata=metadata)
        collection.upsert(ids=[d['id'] for d in documents], embeddings=vectors,
                          documents=[d['text'] for d in documents], metadatas=[d['metadata'] for d in documents])
        expected_ids = {d['id'] for d in documents}
        stale = set(collection.get(include=[])['ids']) - expected_ids
        if stale:
            collection.delete(ids=sorted(stale))
        if collection.count() != len(documents):
            raise RetrievalUnavailable('Index verification failed; rerun the indexing command.')
        collection.modify(metadata={**metadata, 'ready': True})
        return {'collection': self.collection_name, 'backend': self.backend, 'model': self.model_name,
                'embedding_dimensions': self.dimensions, 'indexed_documents': collection.count(),
                'metric': 'cosine', 'corpus_sha256': fingerprint}

    def retrieve(self, question, fingerprint, top_k=5):
        question = validate_question(question, top_k)
        try:
            collection = self.client.get_collection(self.collection_name, embedding_function=None)
        except Exception:
            raise RetrievalUnavailable(f'Knowledge index not found. Run {self.index_command} first.') from None
        metadata = collection.metadata or {}
        self._check_model(metadata)
        if metadata.get('ready') is not True or metadata.get('corpus_sha256') != fingerprint:
            raise RetrievalUnavailable(f'Knowledge index is stale or incomplete. Run {self.index_command} again.')
        count = collection.count()
        if not count:
            raise RetrievalUnavailable(f'Knowledge index is empty. Run {self.index_command} first.')
        response = collection.query(query_embeddings=self._vectors([question]),
                                    n_results=min(top_k, count),
                                    include=['documents', 'metadatas', 'distances'])
        results = [
            {'id': identifier, 'text': text, 'metadata': details, 'distance': float(distance)}
            for identifier, text, details, distance in zip(
                response['ids'][0], response['documents'][0], response['metadatas'][0], response['distances'][0])
        ]
        return {'question': question, 'collection': self.collection_name, 'backend': self.backend,
                'model': self.model_name, 'embedding_dimensions': self.dimensions,
                'metric': 'cosine', 'indexed_documents': count,
                'corpus_sha256': fingerprint, 'results': results}


@lru_cache(maxsize=4)
def _local_client(path):
    import chromadb
    from chromadb.config import Settings
    return chromadb.PersistentClient(path=path, settings=Settings(anonymized_telemetry=False))


@lru_cache(maxsize=1)
def _local_embedder():
    from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
    return DefaultEmbeddingFunction()


def local_store(create=False):
    load_dotenv(PROJECT_ROOT / '.env')
    if os.getenv('VERCEL'):
        raise RetrievalUnavailable('Local vector retrieval is not available on Vercel yet. Cloud Chroma integration is the next step.')
    path = Path(os.getenv('CHROMA_LOCAL_PATH', '.chroma')).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    if not create and not (path / 'chroma.sqlite3').is_file():
        raise RetrievalUnavailable(f'Knowledge index not found. Run {INDEX_COMMAND} first.')
    try:
        return KnowledgeStore(_local_client(str(path.resolve())), _local_embedder(),
                              collection_name=os.getenv('CHROMA_COLLECTION', COLLECTION_NAME))
    except ImportError:
        raise RetrievalUnavailable('Install local retrieval dependencies with .venv/bin/python -m pip install -r requirements-rag.txt.') from None


def configured_store(create=False):
    load_dotenv(PROJECT_ROOT / '.env')
    mode = os.getenv('CHROMA_MODE', 'cloud' if os.getenv('VERCEL') else 'local').strip().lower()
    if mode == 'cloud':
        from sql_quiz.cloud_retrieval import cloud_store
        return cloud_store()
    if mode == 'local':
        return local_store(create=create)
    raise RetrievalUnavailable('CHROMA_MODE must be local or cloud.')


def retrieve_knowledge(question, top_k=5):
    question = validate_question(question, top_k)
    try:
        _, fingerprint = load_corpus()
        return configured_store().retrieve(question, fingerprint, top_k)
    except (RetrievalUnavailable, ValueError):
        raise
    except Exception:
        raise RetrievalUnavailable('Vector retrieval failed. Check the selected Chroma backend, credentials and embedding model.') from None
