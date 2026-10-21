"""Regression tests for numeric normalization and SQL quiz result grading."""
import json
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from grading import grade_result


@pytest.fixture
def reference():
    path = Path(__file__).resolve().parents[1] / "data" / "expected_results.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("qid", [1, 2, 3, 4, 5])
def test_all_five_reference_results_are_accepted(qid, reference):
    expected = reference[str(qid)]
    rows = [
        [Decimal(v) if isinstance(v, str) and v.replace(".", "", 1).isdigit() else v
         for v in row]
        for row in expected["rows"]
    ]
    actual = pd.DataFrame(rows, columns=expected["columns"])
    assert grade_result(qid, actual, reference)[0]


def test_wrong_numeric_result_is_rejected(reference):
    actual = pd.DataFrame([[276]], columns=["total_artists"])
    assert not grade_result(1, actual, reference)[0]


def test_wrong_ranked_order_is_rejected(reference):
    expected = reference["5"]
    actual = pd.DataFrame(list(reversed(expected["rows"])), columns=expected["columns"])
    assert not grade_result(5, actual, reference)[0]


def test_wrong_columns_are_rejected(reference):
    actual = pd.DataFrame([[275]], columns=["count"])
    assert not grade_result(1, actual, reference)[0]
