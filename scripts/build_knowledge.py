"""Stable corpus provenance entry point; implementation lives in scripts.data.

Retained so existing Chroma source metadata remains valid without reindexing.
"""
from scripts.data.build_knowledge import OUTPUT, build_documents, main

__all__ = ['OUTPUT', 'build_documents', 'main']

if __name__ == '__main__':
    main()
