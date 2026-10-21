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
            FROM public.artist;
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
            FROM public.artist AS ar
            JOIN public.album AS al
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
            FROM public.genre AS g
            JOIN public.track AS t
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
            "ordered by total_spent descending, then customer_id ascending for ties."
        ),
        "expected_sql": """
            SELECT
                c.first_name,
                c.last_name,
                ROUND(SUM(i.total)::numeric, 2) AS total_spent
            FROM public.customer AS c
            JOIN public.invoice AS i
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
            "ordered by tracks_sold descending, then genre ascending for ties."
        ),
        "expected_sql": """
            SELECT
                g.name AS genre,
                SUM(il.quantity) AS tracks_sold
            FROM public.genre AS g
            JOIN public.track AS t
                ON g.genre_id = t.genre_id
            JOIN public.invoice_line AS il
                ON t.track_id = il.track_id
            GROUP BY g.genre_id, g.name
            ORDER BY tracks_sold DESC, genre ASC
            LIMIT 5;
        """,
    },
]


# Both frontends consume these hints, so SQL/table guidance has one source.
HINTS = {
    1: (['artist'], 'Each row in public.artist represents one artist.',
        'Use COUNT(*) and name the output column total_artists.'),
    2: (['artist', 'album'], 'Join public.artist and public.album on artist_id.',
        'Count albums per artist. Sort album_count descending and artist ascending; return 5 rows.'),
    3: (['genre', 'track'], 'Join public.genre and public.track on genre_id.',
        'Average milliseconds, divide by 60000.0, round to two decimals; return genre and avg_minutes alphabetically by genre.'),
    4: (['customer', 'invoice'], 'Join public.customer and public.invoice on customer_id.',
        'Sum invoice.total per customer. Return first_name, last_name and total_spent; sort total_spent descending, then customer_id ascending; return 5 rows.'),
    5: (['genre', 'track', 'invoice_line'], 'Join public.genre to public.track on genre_id, then public.invoice_line on track_id.',
        'Sum invoice_line.quantity per genre; return genre and tracks_sold. Sort tracks_sold descending, then genre ascending; return 5 rows.'),
}
for question in QUESTIONS:
    tables, connections, approach = HINTS[question['id']]
    question['tables'] = tables
    question['hint'] = {'connections': connections, 'approach': approach}


def get_questions():
    """Return all quiz questions."""
    return QUESTIONS


def get_total_points():
    """Return the total possible quiz score."""
    return sum(question["points"] for question in QUESTIONS)
