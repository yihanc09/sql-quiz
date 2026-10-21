"""Check the actual CSV dataset and knowledge boundaries without network/secrets."""

import csv
import shutil
from datetime import datetime
from decimal import Decimal

import pytest

from sql_quiz.dataset import CSV_DIR, TABLES, load_dataset


def test_full_dataset_integrity_and_types():
    data = load_dataset()
    assert len(data) == 11
    assert sum(map(len, data.values())) == 15607
    assert isinstance(data['invoice'][0][2], datetime)
    assert isinstance(data['invoice'][0][-1], Decimal)
    assert data['employee'][0][4] is None
    assert len(data['playlist_track']) == 8715


@pytest.mark.parametrize('mutation', ['orphan', 'duplicate', 'header', 'required', 'money'])
def test_corrupt_csv_rejected_before_any_database_write(tmp_path, mutation):
    shutil.copytree(CSV_DIR, tmp_path / 'csv')
    path = tmp_path / 'csv' / ('invoice.csv' if mutation == 'money' else 'album.csv')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        rows = list(csv.reader(handle))
    if mutation == 'orphan':
        rows[1][2] = '999999'
    elif mutation == 'duplicate':
        rows[2][0] = rows[1][0]
    elif mutation == 'header':
        rows[0][0] = 'wrong_id'
    elif mutation == 'required':
        rows[1][1] = ''
    else:
        rows[1][-1] = 'NaN'
    with path.open('w', encoding='utf-8', newline='') as handle:
        csv.writer(handle).writerows(rows)
    with pytest.raises(ValueError):
        load_dataset(tmp_path / 'csv')
