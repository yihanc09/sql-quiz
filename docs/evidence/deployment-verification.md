# RAG deployment verification

## Code and CI

On October 21, 2026, four separate changes were pushed to each repository:

| Area | Coursework repository | Vercel deployment repository |
|---|---|---|
| Vector retrieval | `113137b` | `ec162d4` |
| AI SQL generation | `57575c9` | `d4a5618` |
| Quiz workspace UI | `f7e1a13` | `7fece3e` |
| Architecture and setup documentation | `390bc0b` | `e9397a5` |

Both GitHub Actions runs completed successfully. Each includes unit tests, native Chroma vector tests, and PostgreSQL integration/security tests using the existing GitHub Secret:

- [Coursework CI run](https://github.com/yihanc09/IDS706-SQL-Quiz/actions/runs/39676055518)
- [Deployment repository CI run](https://github.com/yihanc09/sql-quiz/actions/runs/39676048751)

[Vercel build 8SN6Am6YxHNEfLvNrkkrASNrT7MP](https://vercel.com/yihan5/sql-quiz/8SN6Am6YxHNEfLvNrkkrASNrT7MP) completed successfully. The JavaScript served at [the public application](https://sql-quiz-jade.vercel.app/) matched the committed source byte-for-byte. The public API returned five questions and eleven tables without instructor SQL; an unauthenticated generation request returned HTTP 401.

## Environment activation and authenticated verification

The eight new production settings are imported separately into Vercel, not as one combined variable. The local `.local/deployment.env` import file is ignored by Git and contains only the OpenAI/Chroma configuration; it excludes existing database settings. Saving changes requires a new deployment before they become available to running functions.

All eight new variables were confirmed in Vercel as Production Secrets, and [production redeployment 3afFQngT4bHGwwgxGauzATCt3QNd](https://vercel.com/yihan5/sql-quiz/3afFQngT4bHGwwgxGauzATCt3QNd) completed successfully with the saved settings. Authenticated public generation was then verified in the browser at `https://sql-quiz-jade.vercel.app/#question-1`:

- The existing user signed in successfully.
- Generate SQL returned `SELECT COUNT(*) AS total_artists FROM public.artist;` with `gpt-4.1-mini` and five retrieved sources.
- Retrieval details confirmed **Chroma Cloud**, **17 documents**, **1536 dimensions**, and **text-embedding-3-small**.
- Use in editor followed by Run query returned `total_artists = 275` through the restricted production reader.
- The test did not save a draft or submit a grade; existing saved answers were retained.

The earlier screenshot captures have been removed. Replacement screenshots are still needed for the Week 8 submission.

The CLI JSON examples remain available in `docs/evidence/examples/`. The application requires explicit Run/Submit actions and does not implement automatic execution/validation extra credit.
