"""Generate reference SQL results for the five quiz questions."""

import json
from pathlib import Path

from database import run_query
from quiz import get_questions


def main():
    expected_results = {}

    for question in get_questions():
        result = run_query(question["expected_sql"])

        # Convert database values to JSON-compatible values.
        expected_results[str(question["id"])] = {
            "title": question["title"],
            "points": question["points"],
            "expected_sql": question["expected_sql"].strip(),
            "columns": list(result.columns),
            "rows": json.loads(result.to_json(orient="values", date_format="iso")),
        }

        print(
            f"Q{question['id']}: " f"{len(result)} rows, {len(result.columns)} columns"
        )

    output_path = Path("data/expected_results.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(expected_results, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"\nSaved reference results to {output_path}")


if __name__ == "__main__":
    main()
