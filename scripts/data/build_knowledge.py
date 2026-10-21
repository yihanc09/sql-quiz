"""Build deterministic retrieval documents; this does not perform vector retrieval."""

import json
from sql_quiz.dataset import SCHEMA
from sql_quiz.paths import PROJECT_ROOT as ROOT, KNOWLEDGE_PATH

OUTPUT = KNOWLEDGE_PATH


def build_documents():
    documents = []
    for table in SCHEMA['tables']:
        name = table['name']
        lines = [f"PostgreSQL table public.{name}: {table['description']}", 'Columns:']
        for col in table['columns']:
            lines.append(f"- {col['name']}: {col['type']}, {'nullable' if col['nullable'] else 'required'}")
        lines.append('Primary key: ' + ', '.join(table['primary_key']))
        for col, target in table['foreign_keys'].items():
            lines.append(f'Join public.{name}.{col} = public.{target}')
        documents.append({'id': f'schema.{name}', 'text': '\n'.join(lines),
                          'metadata': {'kind': 'schema', 'source': 'data/schema.json', 'table': f'public.{name}'}})
    semantics = [
        ('duration', 'Track duration is track.milliseconds. Divide by 60000.0 to get minutes. '
         'Use ROUND(AVG(milliseconds) / 60000.0, 2) for a two-decimal average. '
         'Some genres contain video or TV content and can have long durations.'),
        ('sales', 'invoice.total is an invoice header total; SUM(invoice.total) by customer measures spending. '
         'invoice_line.quantity measures units sold. SUM(quantity) measures track sales, not COUNT(track_id) '
         'or playlist membership. Line revenue is invoice_line.unit_price * invoice_line.quantity. '
         'Joining invoice headers to multiple lines duplicates header totals; aggregate at the correct grain.'),
        ('joins', 'Artist -> album -> track joins use artist_id then album_id. Track -> genre uses genre_id. '
         'Customer -> invoice -> invoice_line -> track joins use customer_id, invoice_id, track_id. '
         'playlist_track joins playlist and track; membership is many-to-many. Use LEFT JOIN if zero-match '
         'entities must be included; an INNER JOIN excludes them.'),
        ('postgres', 'Use PostgreSQL syntax and qualified public.table names. Generate one read-only SELECT '
         'or WITH ... SELECT statement. Give requested output aliases and ORDER BY. Use deterministic '
         'secondary sorting for ties and LIMIT for top-N requests. Text literals require single quotes. '
         'Dates are timestamps; use actual data values rather than assuming a particular Chinook edition.'),
    ]
    for key, text in semantics:
        documents.append({'id': f'semantics.{key}', 'text': text,
                          'metadata': {'kind': 'semantics', 'source': 'scripts/build_knowledge.py'}})
    examples = [
        ('formats', 'List all available media formats alphabetically.',
         'SELECT name AS media_format FROM public.media_type ORDER BY name;'),
        ('countries', 'Count customers in each country, including a stable sort.',
         'SELECT country, COUNT(*) AS customer_count FROM public.customer GROUP BY country ORDER BY customer_count DESC, country ASC;'),
    ]
    for key, question, query in examples:
        documents.append({'id': f'example.{key}', 'text': f'Question: {question}\nSQL: {query}',
                          'metadata': {'kind': 'example', 'source': 'scripts/build_knowledge.py'}})
    return documents


def main():
    documents = build_documents()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(''.join(json.dumps(doc, ensure_ascii=False) + '\n' for doc in documents), encoding='utf-8')
    print(f'Wrote {len(documents)} retrieval documents to {OUTPUT.relative_to(ROOT)}')


if __name__ == '__main__':
    main()
