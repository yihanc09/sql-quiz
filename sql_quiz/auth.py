"""Supabase authentication and per-user quiz answer persistence."""

from supabase import create_client

from sql_quiz.database import get_connection
from sql_quiz.runtime_config import get_setting


def get_supabase_client():
    return create_client(get_setting("SUPABASE_URL"), get_setting("SUPABASE_ANON_KEY"))


def sign_up(email, password):
    return get_supabase_client().auth.sign_up({"email": email, "password": password})


def sign_in(email, password):
    return get_supabase_client().auth.sign_in_with_password(
        {"email": email, "password": password}
    )


def sign_out(client):
    client.auth.sign_out()


def save_answer(client, user_id, question_id, sql_answer):
    """Save a draft; clear any previous grade for that answer."""
    return (
        client.table("quiz_answers")
        .upsert(
            {
                "user_id": user_id,
                "question_id": question_id,
                "sql_answer": sql_answer,
                "score": None,
                "is_correct": None,
            },
            on_conflict="user_id,question_id",
        )
        .execute()
    )


def save_graded_answer(client, user_id, question_id, sql_answer, score, is_correct):
    """Persist SQL and its grade in the same upsert operation."""
    return (
        client.table("quiz_answers")
        .upsert(
            {
                "user_id": user_id,
                "question_id": question_id,
                "sql_answer": sql_answer,
                "score": score,
                "is_correct": is_correct,
            },
            on_conflict="user_id,question_id",
        )
        .execute()
    )


def load_answer_records(client, user_id):
    """Return per-question SQL and saved grade for the authenticated user."""
    response = (
        client.table("quiz_answers")
        .select("question_id,sql_answer,score,is_correct")
        .eq("user_id", user_id)
        .execute()
    )
    return {row["question_id"]: row for row in response.data}


def load_answers(client, user_id):
    """Backward-compatible helper returning only SQL text."""
    return {
        question_id: row["sql_answer"]
        for question_id, row in load_answer_records(client, user_id).items()
    }


def record_query_event(client, question_id, action, success, sql_answer):
    """Write a server-observed event; identity comes from the verified JWT.

    DATABASE_URL stays on the backend. The taker connection is never used to
    write logs. SQL text and user data are bound as values, never interpolated.
    """
    if type(question_id) is not int or question_id not in range(1, 6):
        raise ValueError("Invalid question ID.")
    if action not in ("RUN_QUERY", "SUBMIT_QUERY") or type(success) is not bool:
        raise ValueError("Invalid query event.")
    if not isinstance(sql_answer, str) or not sql_answer.strip():
        raise ValueError("SQL text is required.")
    user = client.auth.get_user().user
    if not user:
        raise ValueError("Authentication required.")
    with get_connection(read_only=False) as conn:
        conn.execute(
            "INSERT INTO public.quiz_audit_log "
            "(user_id, action, question_id, success, sql_answer, source) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (user.id, action, question_id, success, sql_answer, "server"),
        )
