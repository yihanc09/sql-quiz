"""IDS706 SQL quiz: per-question drafts, persistent grades, and navigation."""

import streamlit as st
from sql_quiz.auth import (
    get_supabase_client,
    sign_in,
    sign_up,
    save_answer,
    load_answer_records,
    save_graded_answer,
    record_query_event,
)
from sql_quiz.database import run_query
from sql_quiz.grading import grade_result
from sql_quiz.quiz_reference import get_live_reference
from sql_quiz.dataset import SCHEMA
from sql_quiz.quiz import get_questions, get_total_points

st.set_page_config(page_title="IDS706 SQL Quiz", page_icon="🎓", layout="wide")
st.title("IDS706 SQL Quiz")
st.caption("Practice SQL with the Chinook Music Store Database")
QUESTIONS = get_questions()
BY_ID = {q["id"]: q for q in QUESTIONS}
IDS = list(BY_ID)


def reset_quiz_state():
    """Remove all user-specific state, including drafts and widget state."""
    for key in list(st.session_state):
        if key.startswith(("draft_", "editor_")) or key in (
            "loaded_user_id",
            "grades",
            "selected_question",
            "query_result",
            "query_question",
        ):
            st.session_state.pop(key, None)


def sync_editor():
    """Copy editor text into durable session state before Streamlit removes hidden widgets."""
    qid = st.session_state.selected_question
    st.session_state[f"draft_{qid}"] = st.session_state[f"editor_{qid}"]


def select_question(qid):
    st.session_state.selected_question = qid


st.session_state.setdefault("user", None)
st.session_state.setdefault("supabase_client", None)

if st.session_state.user is None:
    st.subheader("Welcome!")
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Sign In")
        if login_button:
            try:
                response = sign_in(email, password)
                if response.user and response.session:
                    reset_quiz_state()
                    st.session_state.user = response.user
                    client = get_supabase_client()
                    client.auth.set_session(
                        response.session.access_token, response.session.refresh_token
                    )
                    st.session_state.supabase_client = client
                    st.rerun()
                else:
                    st.warning("Please confirm your email before signing in.")
            except Exception as exc:
                st.error(f"Sign in failed: {exc}")
    with tab2:
        with st.form("signup_form"):
            new_email = st.text_input("Email", key="signup_email")
            new_password = st.text_input(
                "Password", type="password", key="signup_password"
            )
            signup_button = st.form_submit_button("Create Account")
        if signup_button:
            try:
                response = sign_up(new_email, new_password)
                if response.user:
                    st.success(
                        "Account created! Confirm your email if required, then sign in."
                    )
                else:
                    st.info("Please check your email for confirmation.")
            except Exception as exc:
                st.error(f"Sign up failed: {exc}")
else:
    try:
        client = st.session_state.supabase_client
        session = client.auth.get_session() if client else None
        if not session:
            raise ValueError("No active session")
        verified = client.auth.get_user(session.access_token)
        if not verified.user:
            raise ValueError("Invalid user session")
    except Exception:
        reset_quiz_state()
        st.session_state.user = None
        st.session_state.supabase_client = None
        st.warning("Your session has expired. Please sign in again.")
        st.stop()

    # Load all saved records only on login, never on every question change.
    if st.session_state.get("loaded_user_id") != verified.user.id:
        try:
            records = load_answer_records(client, verified.user.id)
        except Exception:
            records = {}
            st.warning("You are signed in, but saved submissions could not be loaded. You can still run SQL; saving may be unavailable.")
        reset_quiz_state()
        st.session_state.grades = {}
        for qid in IDS:
            record = records.get(qid, {})
            draft = record.get("sql_answer") or ""
            st.session_state[f"draft_{qid}"] = draft
            if record.get("score") is not None and record.get("is_correct") is not None:
                st.session_state.grades[qid] = {
                    "sql": draft,
                    "score": int(record["score"]),
                    "correct": bool(record["is_correct"]),
                }
        st.session_state.selected_question = "guide"
        st.session_state.loaded_user_id = verified.user.id

    st.success(f"Signed in as {verified.user.email}")
    if st.button("Sign Out"):
        try:
            client.auth.sign_out()
        finally:
            reset_quiz_state()
            st.session_state.user = None
            st.session_state.supabase_client = None
        st.rerun()

    st.divider()
    st.header("SQL Quiz Dashboard")
    st.write(
        f"Complete {len(QUESTIONS)} SQL questions for a total of {get_total_points()} points."
    )
    grades = st.session_state.grades
    # Only the grade for an edited question becomes stale. Other questions retain their grades.
    for qid in IDS:
        saved_grade = grades.get(qid)
        if saved_grade and saved_grade["sql"] != st.session_state.get(
            f"draft_{qid}", ""
        ):
            grades.pop(qid, None)
    earned = sum(entry["score"] for entry in grades.values())
    st.metric("Total graded score", f"{earned} / {get_total_points()}")
    st.caption(
        "Scores are saved when you submit for grading. Unsaved edits are drafts, not submitted grades."
    )

    # The guide and results are navigation pages, not graded questions.
    GUIDE_PAGE = "guide"
    RESULTS_PAGE = "results"
    pages = [GUIDE_PAGE] + IDS + [RESULTS_PAGE]
    labels = {
        qid: f"Question {qid}: {BY_ID[qid]['title']} ({BY_ID[qid]['points']} points)"
        for qid in IDS
    }
    labels[GUIDE_PAGE] = "Welcome & Dataset Guide"
    labels[RESULTS_PAGE] = "Quiz Results"
    selected_id = st.selectbox(
        "Select a page",
        pages,
        key="selected_question",
        format_func=lambda page: labels[page],
    )
    pos = pages.index(selected_id)
    left, right = st.columns(2)
    left.button(
        (
            "← Review Question 5"
            if selected_id == RESULTS_PAGE
            else ("← Dataset Guide" if selected_id == IDS[0] else "← Previous Question")
        ),
        disabled=pos == 0,
        on_click=select_question,
        args=(pages[max(0, pos - 1)],),
        use_container_width=True,
    )
    right.button(
        (
            "Start Quiz →"
            if selected_id == GUIDE_PAGE
            else ("View Results →" if selected_id == IDS[-1] else "Next Question →")
        ),
        disabled=pos == len(pages) - 1,
        on_click=select_question,
        args=(pages[min(len(pages) - 1, pos + 1)],),
        use_container_width=True,
    )

    # Reference material stays available while students work on any question.
    with st.sidebar:
        st.header("Database Reference")
        st.caption("Chinook is a sample digital music store database.")
        st.markdown("**All 11 uploaded tables (public schema)**")
        for table in SCHEMA['tables']:
            columns = ', '.join(column['name'] for column in table['columns'])
            st.markdown(f"**public.{table['name']}** — {table['description']}")
            st.caption(columns)
        st.markdown("**How tables connect**")
        st.code('\n'.join(
            f"{table['name']}.{column} = {target}"
            for table in SCHEMA['tables']
            for column, target in table['foreign_keys'].items()
        ), language='text')
        st.caption("Use the `public.` schema prefix in your SQL queries.")

    if selected_id == GUIDE_PAGE:
        st.subheader("Welcome to the Chinook Music Store!")
        st.write(
            "Imagine you are a data analyst for a digital music store. "
            "The database tracks artists, albums, songs, customers, and sales. "
            "You will answer five business questions by querying its PostgreSQL tables."
        )
        st.markdown(
            "**What you will practice:** `SELECT`, `JOIN`, `COUNT`, "
            "`AVG`, `SUM`, `GROUP BY`, and `ORDER BY`."
        )
        st.markdown("**How to use the quiz**")
        st.write(
            "1. Read each question and the relevant table reference. "
            "\n2. Write a SQL query and select Run Query to inspect the output. "
            "\n3. Select Submit for Grading to save your answer and score. "
            "\n4. Use Previous/Next to navigate and View Results to see your progress."
        )
        st.info(
            "You do not need to memorize the dataset. "
            "The Database Reference in the sidebar is available throughout the quiz."
        )
        st.button(
            "Start Quiz →",
            type="primary",
            on_click=select_question,
            args=(IDS[0],),
            use_container_width=True,
        )
    elif selected_id == RESULTS_PAGE:
        st.subheader("SQL Quiz Results")
        graded_count = len(grades)
        st.write(f"Graded questions: {graded_count} / {len(QUESTIONS)}")
        st.metric("Total Score", f"{earned} / {get_total_points()}")
        if graded_count == len(QUESTIONS):
            st.success(
                "All five questions have been graded! You can review or revise your answers."
            )
        else:
            st.info(
                "You can view results at any time. Unsubmitted questions are marked Not graded."
            )

        result_rows = []
        for qid in IDS:
            item = BY_ID[qid]
            grade = grades.get(qid)
            result_rows.append(
                {
                    "Question": f"Q{qid}: {item['title']}",
                    "Status": (
                        "Correct"
                        if grade and grade["correct"]
                        else ("Incorrect" if grade else "Not graded")
                    ),
                    "Score": f"{grade['score'] if grade else 0} / {item['points']}",
                }
            )
        st.dataframe(result_rows, use_container_width=True, hide_index=True)
        st.caption(
            "Finish & Sign Out ends your session; it does not lock your answers or grades."
        )
        review_col, finish_col = st.columns(2)
        review_col.button(
            "Review Answers",
            on_click=select_question,
            args=(IDS[0],),
            use_container_width=True,
        )
        if finish_col.button(
            "Finish & Sign Out", type="primary", use_container_width=True
        ):
            try:
                client.auth.sign_out()
            finally:
                reset_quiz_state()
                st.session_state.user = None
                st.session_state.supabase_client = None
            st.rerun()
    else:
        question = BY_ID[selected_id]
        st.subheader(question["title"])
        contexts = {
            1: (
                "The catalog team wants to know how many artists are available.",
                "`public.artist` — each row represents an artist.",
            ),
            2: (
                "The catalog manager wants to identify artists with the largest album catalogs.",
                "`public.artist` and `public.album` — join on `artist_id`.",
            ),
            3: (
                "The content team wants to compare average track length across genres.",
                "`public.genre` and `public.track` — join on `genre_id`; "
                "`milliseconds` stores duration in thousandths of a second.",
            ),
            4: (
                "The marketing team wants to identify the highest-spending customers.",
                "`public.customer` and `public.invoice` — join on `customer_id`; "
                "`invoice.total` is the purchase amount.",
            ),
            5: (
                "The sales team wants to identify which music genres sell the most tracks.",
                "`public.genre`, `public.track`, and `public.invoice_line` — "
                "use `genre_id` and `track_id` to connect them; "
                "`quantity` counts units sold.",
            ),
        }
        scenario, reference = contexts[selected_id]
        st.caption(f"Business scenario: {scenario}")
        st.write(question["description"])
        with st.expander("Relevant Tables & Fields", expanded=False):
            st.markdown(reference)
            st.caption(
                "See Database Reference in the sidebar for more table relationships."
            )
        st.markdown("**Hint**")
        st.write(question['hint']['connections'])
        st.write(question['hint']['approach'])
        if st.button("Show / refresh expected SQL & live result", key=f"hint_{selected_id}"):
            try:
                live = get_live_reference(selected_id)
                st.caption("Fetched now from the uploaded public tables in Supabase.")
                st.code(live['expected_sql'], language='sql')
                import pandas as pd
                st.dataframe(pd.DataFrame(live['rows'], columns=live['columns']), hide_index=True)
            except Exception:
                st.error("Could not fetch the live reference result. Check the database connection and retry.")
        editor_key = f"editor_{selected_id}"
        draft_key = f"draft_{selected_id}"
        # Streamlit deletes widget keys when widgets disappear. Restore from durable draft key.
        if editor_key not in st.session_state:
            st.session_state[editor_key] = st.session_state.get(draft_key, "")
        st.text_area(
            "Write your SQL query",
            height=180,
            placeholder="SELECT ...",
            key=editor_key,
            on_change=sync_editor,
        )
        sql = st.session_state[draft_key]

        if st.button("Save Answer"):
            if not sql.strip():
                st.warning("Please write some SQL before saving.")
            else:
                try:
                    # Saving an unchanged, already-graded SQL must not erase its grade.
                    existing = grades.get(selected_id)
                    if existing and existing["sql"] == sql:
                        st.info(
                            "This answer is already saved and graded; your score is unchanged."
                        )
                    else:
                        save_answer(client, verified.user.id, selected_id, sql)
                        grades.pop(selected_id, None)
                        st.success("Draft saved! Submit for grading when ready.")
                except Exception as exc:
                    st.error(f"Failed to save answer: {exc}")

        col_run, col_submit = st.columns(2)
        run_clicked = col_run.button("Run Query", use_container_width=True)
        submit_clicked = col_submit.button(
            "Submit for Grading", type="primary", use_container_width=True
        )
        if run_clicked or submit_clicked:
            query_text = sql.strip()
            if not query_text:
                st.warning("Please enter a SQL query.")
            elif not query_text.lower().startswith(
                ("select ", "select\n", "with ", "with\n")
            ):
                st.error("Only SELECT queries are allowed.")
            elif query_text.rstrip(";").count(";") > 0:
                st.error("Only one SQL statement is allowed.")
            else:
                audit_action = "SUBMIT_QUERY" if submit_clicked else "RUN_QUERY"
                try:
                    result = run_query(query_text)
                except Exception as exc:
                    # Log failed executions too; never confuse them with successful runs.
                    try:
                        record_query_event(client, selected_id, audit_action, False, sql)
                    except Exception as audit_exc:
                        st.warning(f"Could not record audit event: {audit_exc}")
                    st.error(f"Query execution failed: {exc}")
                else:
                    try:
                        record_query_event(client, selected_id, audit_action, True, sql)
                    except Exception as audit_exc:
                        st.warning(f"Could not record audit event: {audit_exc}")
                    st.success(
                        f"Query executed successfully! {len(result)} rows returned."
                    )
                    st.dataframe(result, use_container_width=True, hide_index=True)
                    try:
                        if submit_clicked:
                            correct, feedback = grade_result(selected_id, result)
                            points = question["points"] if correct else 0
                            save_graded_answer(
                                client, verified.user.id, selected_id, sql, points, correct
                            )
                            grades[selected_id] = {
                                "sql": sql,
                                "correct": correct,
                                "score": points,
                            }
                            if correct:
                                st.success(
                                    f"Correct! {points} / {question['points']} points. {feedback}"
                                )
                            else:
                                st.warning(
                                    f"Not yet correct: 0 / {question['points']} points. {feedback}"
                                )
                            st.info(
                                f"Updated total score: {sum(g['score'] for g in grades.values())} / {get_total_points()}"
                            )
                            st.rerun()
                    except Exception as exc:
                        st.error(f"Grade submission failed: {exc}")

        grade = grades.get(selected_id)
        if grade and grade["sql"] == sql:
            if grade["correct"]:
                st.success(
                    f"Saved grade: Correct — {grade['score']} / {question['points']} points"
                )
            else:
                st.warning(
                    f"Saved grade: Not yet correct — 0 / {question['points']} points"
                )
