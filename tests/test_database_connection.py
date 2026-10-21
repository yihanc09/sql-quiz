from database import run_query


def test_database_connection():
    result = run_query("SELECT COUNT(*) AS total_artists FROM chinook.artist;")

    assert result.iloc[0]["total_artists"] == 275
