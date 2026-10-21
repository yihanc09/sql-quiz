"""Grade SQL results against reference tables, accounting for DB/JSON numeric types."""

import json
import math
from decimal import Decimal, InvalidOperation
from numbers import Number
from pathlib import Path

import pandas as pd

RESULTS_PATH = Path(__file__).resolve().parent / "data" / "expected_results.json"


def load_expected_results():
    with RESULTS_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


def _normalize(value):
    """Use the same representation for Decimal, numpy numbers and JSON numbers.

    Numeric-looking strings are normalized too, since json.dumps(..., default=str)
    stores PostgreSQL Decimal values as strings. Non-numeric text is preserved.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            number = Decimal(value)
            if number.is_finite():
                return ("number", number)
        except InvalidOperation:
            pass
        return ("text", value)
    if isinstance(value, bool):
        return ("bool", value)
    try:
        if bool(pd.isna(value)):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, Number):
        try:
            number = Decimal(str(value))
            if number.is_finite():
                return ("number", number)
        except InvalidOperation:
            pass
    return ("text", str(value))


def grade_result(question_id, actual, reference=None):
    """Return (is_correct, feedback) after comparing columns and row values.

    Q1 and Q3 do not require row ordering. Q2, Q4 and Q5 do.
    """
    if reference is None:
        reference = load_expected_results()
    expected = reference[str(question_id)]
    expected_columns = expected["columns"]
    if list(actual.columns) != expected_columns:
        return False, f"Expected columns: {', '.join(expected_columns)}."

    actual_rows = [
        tuple(_normalize(v) for v in row)
        for row in actual.itertuples(index=False, name=None)
    ]
    expected_rows = [tuple(_normalize(v) for v in row) for row in expected["rows"]]
    if len(actual_rows) != len(expected_rows):
        return False, f"Expected {len(expected_rows)} rows, got {len(actual_rows)}."

    if question_id in (1, 3):
        correct = sorted(actual_rows, key=repr) == sorted(expected_rows, key=repr)
    else:
        correct = actual_rows == expected_rows

    if correct:
        return True, "Your result matches the reference result."

    for index, (actual_row, expected_row) in enumerate(zip(actual_rows, expected_rows), start=1):
        if actual_row != expected_row:
            return False, (
                f"Result differs at row {index}. Check the returned values "
                "and the required row order."
            )
    return False, "The result does not match the reference result."
