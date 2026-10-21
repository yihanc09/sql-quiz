"""Embed curated knowledge into a local or cloud Chroma collection."""
import argparse
import json

from sql_quiz.retrieval import load_corpus, configured_store, RetrievalUnavailable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cloud', action='store_true', help='Index Chroma Cloud without changing the default local mode')
    args = parser.parse_args()
    try:
        documents, fingerprint = load_corpus()
        if args.cloud:
            from sql_quiz.cloud_retrieval import cloud_store
            store = cloud_store()
        else:
            store = configured_store(create=True)
        summary = store.index(documents, fingerprint)
        print(json.dumps(summary, indent=2))
    except (RetrievalUnavailable, ValueError) as exc:
        raise SystemExit(str(exc)) from None
    except Exception:
        raise SystemExit('Indexing failed. Check the selected Chroma backend and embedding configuration; no configuration values were printed.') from None


if __name__ == '__main__':
    main()
