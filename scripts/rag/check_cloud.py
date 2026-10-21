"""Verify the cloud collection without embedding or SQL-generation API calls."""
import json

from sql_quiz.cloud_retrieval import cloud_store
from sql_quiz.retrieval import load_corpus, RetrievalUnavailable


def main():
    try:
        store = cloud_store()
        collection = store.client.get_collection(store.collection_name, embedding_function=None)
        metadata = collection.metadata or {}
        store._check_model(metadata)
        _, fingerprint = load_corpus()
        if metadata.get('ready') is not True or metadata.get('corpus_sha256') != fingerprint:
            raise RetrievalUnavailable('Cloud index is stale or incomplete; rerun scripts.rag.index_knowledge --cloud.')
        count = collection.count()
        if not count:
            raise RetrievalUnavailable('Cloud index is empty; run scripts.rag.index_knowledge --cloud.')
        print(json.dumps({'backend': 'cloud', 'collection': store.collection_name,
                          'model': store.model_name, 'dimensions': store.dimensions,
                          'indexed_documents': count, 'ready': True}, indent=2))
    except RetrievalUnavailable as exc:
        raise SystemExit(str(exc)) from None
    except Exception:
        raise SystemExit('Cloud verification failed. Check the connection and collection settings; no credential values were printed.') from None


if __name__ == '__main__':
    main()
