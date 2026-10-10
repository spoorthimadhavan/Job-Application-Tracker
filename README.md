# Job Application Tracker

[![CI](../../actions/workflows/ci.yml/badge.svg)](../../actions/workflows/ci.yml)
![License: MIT](https://img.shields.io/badge/license-MIT-blue)

> ## ⚠️ Created with Claude. It may contain errors.
> This whole project (code, tests, CI and docs) was **created by Claude**, Anthropic's AI assistant, from a conversation with its owner.
> It has been tested (see below) but **not professionally reviewed**. Expect bugs, wrong status guesses and rough edges.
> Check anything important against your real inbox, and please read [SECURITY.md](SECURITY.md) before pointing it at a real mailbox.

## Fork it and contribute
Please use it, fork it and make it better. Pull requests are welcome, see [CONTRIBUTING.md](CONTRIBUTING.md).
The most useful contribution: **an email template the classifier gets wrong** (add a test, then fix `api/_lib/classify.py`).

## Quick start (no Google keys needed)
```bash
git clone <your fork> && cd <repo>
make install      # pip + npm + Playwright chromium
make dev-api      # terminal 1
make dev-web      # terminal 2, open http://localhost:5173 and click "Try the demo"
```
Or with Docker: `make docker`, then open http://localhost:8000.

## Tests and DevOps
| What | Tool | Command |
|---|---|---|
| Backend unit + API tests (classifier, Gmail client, OAuth/session, routes) | pytest, pytest-cov, httpx MockTransport | `make test-api` |
| Frontend unit + component tests (status, range, docs store, components, App) | Vitest, Testing Library, fake-indexeddb | `make test-web` |
| End-to-end in a real browser against the real server (demo login, tiles, filters, email drawer, upload) | Playwright | `make e2e` |
| Lint and format | ruff | `make lint` |
| Everything CI runs | | `make ci` |

DevOps pieces in this repo:
- **GitHub Actions CI** (`.github/workflows/ci.yml`): backend lint + tests with a coverage gate, frontend tests + build, Playwright e2e, Docker build + smoke test; concurrency cancel, least-privilege permissions, cached dependencies.
- **CodeQL** security scanning (weekly and on every PR) and **Dependabot** updates for pip, npm, Actions and Docker.
- **Docker**: multi-stage `Dockerfile` (Node build, slim Python runtime, non-root user, healthcheck) and `docker-compose.yml`.
- **Makefile**, `.editorconfig`, **pre-commit** (`pre-commit install`), issue and PR templates.
- **Health endpoint** `/api/health` for probes; config only through environment variables (12-factor, see `.env.example`).
- Deploy target: Vercel (`vercel.json`); the same image also runs anywhere Docker does.

Sign in with Google and get one live list of every job application found in your Gmail
(LinkedIn, Indeed, StepStone and company career systems). Click a row to read the email behind it.

```
api/            Python (FastAPI) – runs as one Vercel serverless function
  index.py        entry point
  _lib/classify.py  email -> status rules (the "brain", fully unit tested)
  _lib/gmail.py     Gmail REST client (list + read a message)
  _lib/auth.py      Google OAuth + encrypted cookie session (no database)
  _lib/demo.py      made-up mailbox for the demo login
web/            React (Vite) – Login, TopBar, StatTiles, Toolbar, ApplicationList, EmailDrawer
tests/          pytest (backend)
web/e2e/        Playwright end-to-end tests
web/src/**/*.test.*  Vitest tests
```

## Statuses
Selected · Under review · Applied (up to 6 weeks) · Rejected · Rejected after interview ·
Rejected, no response (Applied with no reply for more than 6 weeks) · Account created, not applied.

## How "real time" works
The page asks `/api/applications` every 30 seconds while the tab is open. The server reads Gmail
(cached for 20 seconds per user) and re-classifies, so new rejections or invitations appear by themselves.

## Why no LLM / RAG / ML
Job mails come from a few fixed templates, so plain rules are exact, free and testable.
Mails that rules can't decide are shown as "Under review" with a `check` tag instead of guessing.

## Linking LinkedIn, Indeed, StepStone
None of them offers an API for a person's applications. They all send email, so they are read through
Gmail and shown with their source. A row's email copy is shown in a sandboxed frame.

## Google sign-in setup
1. Google Cloud Console > create a project > enable **Gmail API**.
2. OAuth consent screen: add scope `gmail.readonly`. While in "Testing", add your own email as a test user.
   Letting anyone sign in needs Google's verification for this restricted scope (a security review).
3. Credentials > OAuth client ID > Web application. Authorized redirect URI:
   `https://<your-host>/api/auth/callback`
4. Set env vars (see `.env.example`): `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY`.

## Welcome email (optional)
After a Google sign-in the app can email the user a welcome message through [Resend](https://resend.com).
1. Create a Resend account and an API key; verify a sending domain (the test sender `onboarding@resend.dev` only delivers to your own Resend account address).
2. Set `RESEND_API_KEY` and `MAIL_FROM` (see `.env.example`). With no key, no email is sent.
There is no database, so "first sign-in" means "this browser has no welcome marker cookie yet". A new browser or device sends it again.
Email/password registration is not part of this app (login is Google only); it would need a database and is a good first contribution.

## Deploy
Vercel: import the repo (or `docker compose up` anywhere), no framework preset needed (`vercel.json` builds `web/` and serves `api/`).
Add the env vars above, then redeploy.

## Resume and cover letter per job
Open a row, then upload a resume and/or cover letter for that job (PDF, Word, text; up to 5 MB each).
Files are stored in the browser (IndexedDB) per signed-in user, so no database is needed.
To keep them across devices, swap `web/src/docs.js` for Vercel Blob or S3 behind a new API route.

## Look-back filter
"Look back" chooses how far back the mailbox is read: since the day you signed up, last month, 3 or 6 months,
last year, all time, or a custom date. The choice is remembered in the browser and sent as `?since=YYYY-MM-DD`
to `/api/applications`, so Gmail only returns mail from that day on.

## Known limitations
- Gmail read-only is a Google *restricted* scope: letting strangers sign in needs Google's verification. Until then only test users you add can sign in.
- LinkedIn, Indeed and StepStone have no application APIs, so everything is inferred from their emails. Unusual templates may be misclassified (they show "Under review" with a `check` tag when unsure).
- Resumes and cover letters live in the browser (IndexedDB), not in the cloud or across devices.
- Not deployed anywhere by default; no database by design.

## License
MIT, see [LICENSE](LICENSE).
