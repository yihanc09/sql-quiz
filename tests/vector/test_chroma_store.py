"""Native Chroma storage/query tests; small explicit vectors need no download."""
import pytest

chromadb = pytest.importorskip('chromadb')
from sql_quiz.retrieval import KnowledgeStore, RetrievalUnavailable


def documents(names=('catalog','sales','other')):
    return [{'id':name,'text':name,'metadata':{'kind':'schema','source':'test'}} for name in names]


def vectors(texts):
    mapping={'catalog':[1.0,0.0],'sales':[0.0,1.0],'other':[-1.0,0.0]}
    # Deliberately no shared query/document words: ranking must use vectors.
    return [mapping.get(text,[0.0,1.0]) for text in texts]


@pytest.fixture
def store(tmp_path):
    return KnowledgeStore(chromadb.PersistentClient(path=str(tmp_path)),vectors,
                          model_name='test-vectors',dimensions=2)


def test_native_embedding_storage_and_nearest_neighbor_order(store):
    store.index(documents(),'version1')
    collection=store.client.get_collection(store.collection_name)
    assert len(collection.get(include=['embeddings'])['embeddings'][0]) == 2
    result=store.retrieve('which documents explain revenue?','version1',3)
    assert result['results'][0]['id']=='sales'
    assert result['results'][0]['distance']==pytest.approx(0,abs=1e-6)
    distances=[hit['distance'] for hit in result['results']]
    assert distances==sorted(distances)


def test_reindex_is_idempotent_and_removes_stale_documents(store):
    store.index(documents(),'version1')
    assert store.index(documents(),'version1')['indexed_documents']==3
    assert store.index(documents(('catalog','sales')),'version2')['indexed_documents']==2
    assert set(store.client.get_collection(store.collection_name).get()['ids'])=={'catalog','sales'}
    with pytest.raises(RetrievalUnavailable,match='stale'):
        store.retrieve('a question','version1')
    assert len(store.retrieve('a question','version2',8)['results'])==2


def test_embedding_model_mismatch_is_rejected(store):
    store.index(documents(),'version1')
    incompatible=KnowledgeStore(store.client,vectors,model_name='different-model',dimensions=2)
    with pytest.raises(RetrievalUnavailable,match='model changed'):
        incompatible.retrieve('question','version1')


def test_collection_persists_across_store_instances(store):
    store.index(documents(),'version1')
    reopened=KnowledgeStore(store.client,vectors,model_name='test-vectors',dimensions=2)
    assert reopened.retrieve('unseen natural language','version1')['results'][0]['id']=='sales'
