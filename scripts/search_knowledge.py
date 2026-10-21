"""Run actual vector similarity retrieval for a natural-language SQL question."""
import argparse
import json
import os

from sql_quiz.retrieval import retrieve_knowledge, RetrievalUnavailable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--cloud', action='store_true', help='Use Chroma Cloud for this command')
    args = parser.parse_args()
    if args.cloud:
        os.environ['CHROMA_MODE'] = 'cloud'
    try:
        print(json.dumps(retrieve_knowledge(args.question, args.top_k), indent=2, ensure_ascii=False))
    except (RetrievalUnavailable, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
