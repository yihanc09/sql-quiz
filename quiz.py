"""SQL Quiz questions for the Chinook database."""

QUESTIONS = [
    {
        "id": 1,
        "title": "Count Artists",
        "points": 4,
        "description": (
            "How many artists are in the Chinook database? "
            "Return one column named total_artists."
        ),
        "expected_sql": """
            SELECT COUNT(*) AS total_artists
            FROM chinook.artist;
        """,
    },
    {
        "id": 2,
        "title": "Albums by Artist",
        "points": 4,
        "description": (
            "Find the 5 artists with the most albums. "
            "Return artist and album_count, ordered by "
            "album_count descending and artist ascending."
        ),
        "expected_sql": """
            SELECT
                ar.name AS artist,
                COUNT(al.album_id) AS album_count
            FROM chinook.artist AS ar
            JOIN chinook.album AS al
                ON ar.artist_id = al.artist_id
            GROUP BY ar.artist_id, ar.name
            ORDER BY album_count DESC, artist ASC
            LIMIT 5;
        """,
    },
    {
        "id": 3,
        "title": "Average Track Duration",
        "points": 4,
        "description": (
            "Calculate the average track duration in minutes "
            "for each genre. Round to two decimal places "
            "and sort alphabetically by genre."
        ),
        "expected_sql": """
            SELECT
                g.name AS genre,
                ROUND(AVG(t.milliseconds) / 60000.0, 2)
                    AS avg_minutes
            FROM chinook.genre AS g
            JOIN chinook.track AS t
                ON g.genre_id = t.genre_id
            GROUP BY g.genre_id, g.name
            ORDER BY genre;
        """,
    },
    {
        "id": 4,
        "title": "Top Spending Customers",
        "points": 4,
        "description": (
            "Find the 5 customers who have spent the most. "
            "Return first_name, last_name, and total_spent, "
            "ordered by total_spent descending."
        ),
        "expected_sql": """
            SELECT
                c.first_name,
                c.last_name,
                ROUND(SUM(i.total)::numeric, 2) AS total_spent
            FROM chinook.customer AS c
            JOIN chinook.invoice AS i
                ON c.customer_id = i.customer_id
            GROUP BY c.customer_id, c.first_name, c.last_name
            ORDER BY total_spent DESC, c.customer_id ASC
            LIMIT 5;
        """,
    },
    {
        "id": 5,
        "title": "Most Popular Genres",
        "points": 4,
        "description": (
            "Find the 5 music genres with the highest number "
            "of tracks sold. Return genre and tracks_sold, "
            "ordered from highest to lowest."
        ),
        "expected_sql": """
            SELECT
                g.name AS genre,
                SUM(il.quantity) AS tracks_sold
            FROM chinook.genre AS g
            JOIN chinook.track AS t
                ON g.genre_id = t.genre_id
            JOIN chinook.invoice_line AS il
                ON t.track_id = il.track_id
            GROUP BY g.genre_id, g.name
            ORDER BY tracks_sold DESC, genre ASC
            LIMIT 5;
        """,
    },
]


def get_questions():
    """Return all quiz questions."""
    return QUESTIONS


def get_total_points():
    """Return the total possible quiz score."""
    return sum(question["points"] for question in QUESTIONS)
