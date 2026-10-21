"""Generate SQL through real Chroma retrieval and the OpenAI Responses API."""
import argparse
import json
import os

from sql_quiz.generation import generate_sql, load_ai_config, GenerationUnavailable
from sql_quiz.retrieval import RetrievalUnavailable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('question', nargs='?')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--check-config', action='store_true', help='Validate backend settings without an API call')
    parser.add_argument('--cloud', action='store_true', help='Use Chroma Cloud for this command')
    args = parser.parse_args()
    if args.cloud:
        os.environ['CHROMA_MODE'] = 'cloud'
    try:
        if args.check_config:
            config = load_ai_config()
            print(f'OpenAI configured: model={config.model}; API key value hidden.')
        elif args.question:
            print(json.dumps(generate_sql(args.question, args.top_k), indent=2, ensure_ascii=False))
        else:
            parser.error('Supply a natural-language question or --check-config.')
    except (GenerationUnavailable, RetrievalUnavailable, ValueError) as exc:
        raise SystemExit(str(exc)) from None


if __name__ == '__main__':
    main()
