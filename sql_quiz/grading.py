"""Grade SQL results against live references; explicit fixtures support offline tests."""

from decimal import Decimal, InvalidOperation
from numbers import Number

import pandas as pd
from sql_quiz.quiz_reference import get_live_reference

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

    Q1 is a single aggregate row. Q2–Q5 require the requested row ordering.
    """
    if reference is None:
        reference = {str(question_id): get_live_reference(question_id)}
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

    if question_id == 1:
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
