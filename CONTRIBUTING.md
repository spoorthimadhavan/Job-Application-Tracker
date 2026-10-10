# Contributing

Fork it, change it, send a pull request. Small PRs are easiest to review. This project was created with Claude, so fixes to mistakes are very welcome.

## Setup
```bash
git clone <your fork> && cd <repo>
make install        # pip + npm + Playwright chromium
make dev-api        # terminal 1: API on :8000
make dev-web        # terminal 2: app on :5173
```
Open http://localhost:5173 and click **Try the demo**. No Google keys needed.

## Before you open a PR
```bash
make lint test e2e   # same checks as CI
```
- Add a test for every behaviour change (`tests/` for Python, `web/src/**/*.test.*` for Vitest, `web/e2e/` for Playwright).
- The best contribution is a **new email template** the classifier gets wrong: add the sender/subject/snippet to `tests/test_classify.py` first, then fix `api/_lib/classify.py`.
- Never include real emails or personal data in tests. Use invented companies.
- Commits: short imperative subject ("Handle Xing rejection mails").

## Layout
`api/_lib` FastAPI + classifier + Gmail client · `web/src` React app · `tests`, `web/e2e` test suites · `.github` CI.
