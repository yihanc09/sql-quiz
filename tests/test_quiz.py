import json
from pathlib import Path

from quiz import get_questions, get_total_points

RESULTS_PATH = Path(__file__).resolve().parents[1] / "data" / "expected_results.json"


def load_expected_results():
    with RESULTS_PATH.open(encoding="utf-8") as file:
        return json.load(file)


def test_question_count():
    """The quiz must contain exactly five questions."""
    assert len(get_questions()) == 5


def test_total_points():
    """The quiz must be worth 20 points."""
    assert get_total_points() == 20


def test_unique_question_ids():
    """Each question must have a unique ID."""
    ids = [question["id"] for question in get_questions()]
    assert len(ids) == len(set(ids))


def test_questions_have_required_fields():
    """Every question must have the required information."""
    for question in get_questions():
        assert question["title"]
        assert question["description"]
        assert question["expected_sql"].strip()
        assert question["points"] == 4


def test_expected_results_complete():
    """Every question must have saved reference results."""
    results = load_expected_results()

    for question in get_questions():
        answer = results[str(question["id"])]

        assert answer["expected_sql"]
        assert answer["columns"]
        assert answer["rows"]
        assert answer["points"] == question["points"]


def test_artist_count():
    """The verified Chinook dataset contains 275 artists."""
    results = load_expected_results()

    assert results["1"]["columns"] == ["total_artists"]
    assert results["1"]["rows"] == [[275]]


def test_expected_result_shapes():
    """Reference results must have the expected row counts."""
    results = load_expected_results()

    expected_counts = {
        "1": 1,
        "2": 5,
        "3": 25,
        "4": 5,
        "5": 5,
    }

    for question_id, count in expected_counts.items():
        assert len(results[question_id]["rows"]) == count

        column_count = len(results[question_id]["columns"])

        for row in results[question_id]["rows"]:
            assert len(row) == column_count
