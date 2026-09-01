# markdown-docs

Write and update this project's documentation.

## Usage

When adding a feature, changing a response shape, adding a setting, or otherwise
making something already documented untrue.

## Instructions

1. **Docs live in `docs/` as plain Markdown.** There is no build step and no
   generator — GitHub renders them, and they are read as files. Do not add
   Sphinx, MkDocs, or a toolchain.

2. **The pages and who they are for:**
   - `README.md` — the index. Add new pages to its table
   - `installation.md` — getting it running
   - `quickstart.md` — first requests against a live server
   - `api-contract.md` — **the frontend-facing contract**. Response envelope,
     pagination, error codes, rate limiting, auth flow, conventions
   - `configuration.md` — every environment variable
   - `architecture.md` — layout, layer rules, patterns
   - `adding-modules.md` — extending the service

3. **`api-contract.md` is a specification, not a tour.** A frontend developer
   should be able to implement against it without opening the server code.
   When you change anything a client can observe — a field name, a status code,
   an error code, a header, a query parameter — that page changes in the same
   commit. It is the one doc where being out of date is a bug, not untidiness.

4. **`configuration.md` follows `core/config.py` exactly.** Read the `Settings`
   class rather than the previous version of the table; a renamed variable that
   only lives in the docs is worse than no docs.

5. **Show the real payload.** Copy examples from an actual response or from
   `/openapi.json`, not from memory. An example that has drifted from the
   implementation teaches the wrong thing confidently.

6. **What belongs where:** anything a client observes goes in `api-contract.md`;
   anything about how the server is built goes in `architecture.md`. Do not
   duplicate — cross-link instead, or the two will disagree.

7. **The generated schema is the API surface.** Do not hand-write an endpoint
   reference; `/openapi.json` and `/docs` are always correct and never go stale.
   Document meaning and behaviour, which the schema cannot express.

## Conventions

- Sentence-case headings, no title case
- Tables for anything enumerable — fields, variables, error codes
- Fenced blocks tagged with the language (`json`, `bash`, `python`, `text`)
- Relative links between pages, e.g. `[API Contract](api-contract.md)`
- No "TODO" or "coming soon" — omit the section instead
