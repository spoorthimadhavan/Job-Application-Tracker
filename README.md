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

## Live demo
**Live deployment: not published yet.** Deploy your own in ~2 minutes (see [Deployment](#deployment-vercel)) and put your URL here:

`https://<your-project>.vercel.app` (add a link here after you deploy, and use **Try the demo** on the login page to look around without Google keys)

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fspoorthimadhavan%2FJob-Application-Tracker&env=GOOGLE_CLIENT_ID,GOOGLE_CLIENT_SECRET,SECRET_KEY&envDescription=Google%20OAuth%20keys%20and%20a%20long%20random%20string)

## Technologies
| Layer | Tech |
|---|---|
| Frontend | React 18, Vite 5, plain CSS, IndexedDB (resume / cover-letter files in the browser) |
| Backend | Python 3.12, FastAPI, httpx, cryptography (Fernet encrypted cookie session) |
| Auth and data source | Google OAuth 2.0 + Gmail REST API (`gmail.readonly`) |
| Email (optional) | Resend HTTP API (welcome email) |
| Tests | pytest + pytest-cov + pytest-asyncio, Vitest + Testing Library + jsdom, Playwright |
| Quality | ruff (lint + format), pre-commit, CodeQL, Dependabot |
| DevOps | GitHub Actions CI, Docker (multi-stage) + docker-compose, Makefile, Vercel (serverless) |
| Not used on purpose | database, LLM, RAG, ML (see below) |

## Project layout
```
api/            Python (FastAPI), runs as one Vercel serverless function
  index.py        entry point
  _lib/classify.py  email -> status rules (the "brain", fully unit tested)
  _lib/gmail.py     Gmail REST client (list + read a message)
  _lib/auth.py      Google OAuth + encrypted cookie session (no database)
  _lib/mailer.py    welcome email via Resend
  _lib/demo.py      made-up mailbox for the demo login
web/            React (Vite): Login, TopBar, StatTiles, Toolbar, ApplicationList, EmailDrawer, Documents
web/e2e/        Playwright end-to-end tests
web/src/**/*.test.*  Vitest tests
tests/          pytest (backend)
.github/        CI, CodeQL, Dependabot, issue and PR templates
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

## Linking LinkedIn, Indeed and StepStone
There is nothing to connect inside those sites: **none of them offers an API** for a person's own applications.
They all send you an email when you apply and when the employer answers, so the app reads those emails through Gmail
and tags each row with its source (LinkedIn, Indeed, StepStone, or a company's own system).

To link them for yourself:
1. **Use the same email address on all three sites** that you sign in to this app with (the Gmail account).
   Check in each site's account settings that notifications and application updates are sent by email.
   - LinkedIn: Settings > Communications > Email > make sure "Jobs" / application updates are on.
   - Indeed: Account settings > Email > application and employer messages on.
   - StepStone: Profile > Notifications > application status emails on.
2. Apply as usual. Confirmation and rejection emails land in Gmail and show up in the list within ~30 seconds.
3. Use **Look back** to go further into the past (the app reads mail from that date on).
4. Applications made before you turned notifications on are only found if their emails are still in your mailbox.

Not handled: other mail providers (Outlook, iCloud) and sites that send no email. Adding another provider is a
contribution: write a function like `gmail.py` that returns the same message shape, then add its sender templates to `classify.py`.

## Run locally
**Needs:** Python 3.12+, Node 20+, optionally Docker and make.
```bash
git clone https://github.com/spoorthimadhavan/Job-Application-Tracker && cd Job-Application-Tracker
make install      # pip install -r requirements-dev.txt, npm ci, Playwright chromium
```
**Backend** (FastAPI on http://localhost:8000):
```bash
cp .env.example .env            # optional: only needed for real Google login
python -m uvicorn index:app --app-dir api --reload --port 8000     # or: make dev-api
```
**Frontend** (React on http://localhost:5173, proxies `/api` to the backend):
```bash
cd web && npm run dev                                              # or: make dev-web
```
Open http://localhost:5173 and click **Try the demo**. No Google keys needed.
Local env vars: for plain http set `COOKIE_SECURE=false` (Docker and the e2e tests already do).

**Docker (one container, API + built app):** `make docker`, then open http://localhost:8000.

**Tests:** `make test` (pytest + Vitest), `make e2e` (Playwright), `make lint`, `make ci` (everything).

## Google sign-in setup (needed for real Gmail, not for the demo)
1. https://console.cloud.google.com > create a project > **APIs & Services > Library > enable Gmail API**.
2. **OAuth consent screen**: add scope `.../auth/gmail.readonly`. While the app is in *Testing*, add your own address under **Test users**.
   Letting anyone sign in needs Google's verification for this restricted scope (a security review).
3. **Credentials > Create credentials > OAuth client ID > Web application**. Authorized redirect URIs:
   - `http://localhost:8000/api/auth/callback` (local)
   - `https://<your-project>.vercel.app/api/auth/callback` (production)
4. Copy the client id and secret into your environment (below).

## Environment variables
| Name | Required | Meaning |
|---|---|---|
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | for real login | from step 3 above |
| `SECRET_KEY` | yes in production | long random string that encrypts the login cookie (`python -c "import secrets;print(secrets.token_urlsafe(48))"`) |
| `REDIRECT_URI` | no | defaults to `https://<host>/api/auth/callback` |
| `SINCE` | no | default start date, e.g. `2026/05/01` |
| `COOKIE_SECURE` | no | `false` only for plain-http local runs |
| `RESEND_API_KEY`, `MAIL_FROM` | no | welcome email (see below) |

## Deployment (Vercel)
1. Push your fork to GitHub.
2. https://vercel.com/new > **Import** the repo (or click the Deploy button at the top). Leave the framework preset as **Other**;
   `vercel.json` already builds `web/` and serves `api/` as a Python function.
3. Add the environment variables above (at least `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY`) and click **Deploy**.
4. Copy your production URL, add `https://<url>/api/auth/callback` as an authorized redirect URI in Google Cloud, and redeploy if you changed env vars.
5. Visit the URL: **Try the demo** works immediately; **Sign in with Google** works once step 4 is done.
6. Every push to `main` now deploys automatically; pull requests get preview URLs (CI must be green first).

Other hosts: the `Dockerfile` runs anywhere (Render, Railway, Fly.io, a VPS): `docker build -t jobtracker . && docker run -p 8000:8000 --env-file .env jobtracker`.

## Welcome email (optional)
After a Google sign-in the app can email the user a welcome message through [Resend](https://resend.com).
1. Create a Resend account and an API key; verify a sending domain (the test sender `onboarding@resend.dev` only delivers to your own Resend account address).
2. Set `RESEND_API_KEY` and `MAIL_FROM`. With no key, no email is sent.
There is no database, so "first sign-in" means "this browser has no welcome marker cookie yet". Email/password registration is not part of this app (login is Google only); it would need a database and is a good first contribution.

## Tests and DevOps
| What | Tool | Command |
|---|---|---|
| Backend unit + API tests | pytest, pytest-cov, httpx MockTransport | `make test-api` |
| Frontend unit + component tests | Vitest, Testing Library, fake-indexeddb | `make test-web` |
| End-to-end in a real browser | Playwright | `make e2e` |
| Lint and format | ruff | `make lint` |
| Everything CI runs | | `make ci` |

- **GitHub Actions CI** (`.github/workflows/ci.yml`): backend lint + tests with a coverage gate, frontend tests + build, Playwright e2e, Docker build + smoke test.
- **CodeQL** scanning and **Dependabot** (grouped minor/patch updates; major versions are upgraded by hand).
- **Docker** multi-stage image (non-root, healthcheck) and `docker-compose.yml`; **Makefile**, **pre-commit**, issue and PR templates.
- `/api/health` for probes; configuration only through environment variables.

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
