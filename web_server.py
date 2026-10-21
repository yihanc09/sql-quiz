"""Stable local and Vercel entrypoint. Application code lives in sql_quiz.web."""

from sql_quiz.web import handler, main

if __name__ == "__main__":
    main()
