# Deployment and setup

> **Status: not deployed.** No live URL exists. The deployment steps below describe a standard single-service
> deployment but were **not executed** by the author. Local setup and the test suites were run.

## Prerequisites
Python 3.11+ (developed on 3.12), Node 20+ (developed on 22), npm.

## Local setup

### Backend
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env     # optional; the app reads real environment variables, so export them or use your shell/IDE
uvicorn app.main:app --reload --port 8000
```

### Database initialisation
SQLite tables are created automatically on startup, and the demo data is seeded if the database is empty
(`SEED_DEMO_DATA=true`). To reset to a clean demo state (stock back to 340 / 85 / 0):
```bash
python -m app.seed --reset
```
There are no migrations; the schema is created with `create_all`. Delete `app.db` or use `--reset` after model changes.

### Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173 (dev proxy forwards /api to http://localhost:8000)
npm run build        # production build to frontend/dist
npm test             # Vitest
```

## Environment variables (names only)

Backend: `APP_ENV`, `DATABASE_URL`, `JWT_SECRET`, `ACCESS_TOKEN_MINUTES`, `CORS_ORIGINS`, `SEED_DEMO_DATA`,
`LOGIN_MAX_FAILURES`, `LOGIN_LOCKOUT_SECONDS`, `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`,
`LLM_TIMEOUT_SECONDS`, `FRONTEND_DIST`, `BCRYPT_ROUNDS` (tests only).
Frontend (build time): `VITE_API_BASE`, `VITE_SHOW_DEMO_LOGINS`.

If `JWT_SECRET` is unset the backend generates a random per-process secret (sessions end on restart). **Set it for any shared deployment.**
API keys live only in backend environment variables; nothing secret is sent to or bundled in the frontend.

## Connecting a real AI model (optional)
```bash
# OpenAI-compatible API (use LLM_BASE_URL for other compatible gateways)
export LLM_PROVIDER=openai LLM_API_KEY=... LLM_MODEL=<model name>
# or Anthropic
export LLM_PROVIDER=anthropic LLM_API_KEY=... LLM_MODEL=<model name>
```
The model only extracts candidate lines; the backend validates every SKU, quantity, stock level and price, and the retailer must
confirm. On timeout, rate limit, API error or invalid output the app falls back to the rule-based parser and shows why.
**The live-model path was tested only with stubbed HTTP/provider responses, not against a real provider.**

## Deploying (single service, e.g. Render / Railway / a VM) - not executed
The API can serve the built frontend, so one service gives one origin (no CORS needed).
1. Build: `cd frontend && npm ci && npm run build && cd ../backend && pip install -r requirements.txt`
2. Set env: `APP_ENV=production`, `JWT_SECRET=<long random>`, `SEED_DEMO_DATA=true` only if you want the demo accounts
   (**never** in a real environment: they have documented passwords), `DATABASE_URL`, optional LLM variables.
3. Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT` from `backend/`.
4. SQLite needs a persistent disk; on ephemeral platforms the data resets at each deploy. Use `DATABASE_URL` for a mounted path.
5. Serve over HTTPS (the platform normally terminates TLS). Run a single worker (login throttling is in-memory).
In production mode (`APP_ENV=production`) `/api/docs` and the OpenAPI schema are disabled.

## Demo login credentials (synthetic, demo only)
| Role | Email | Password |
|---|---|---|
| Retailer 1 | retailer1@demo.test | Retailer@123 |
| Retailer 2 (tight credit) | retailer2@demo.test | Retailer@123 |
| Order desk | desk@demo.test | Desk@12345 |
| Salesman (API only, no screens) | salesman@demo.test | Salesman@123 |

## Known limitations
- **Not deployed**; no live URL. No CI.
- **No visual/browser verification** was possible in the build environment (no headless browser). The UI was verified by
  type-checking, jsdom component/flow tests, and by exercising the same API the UI calls. Please click through it once.
- AI: rule-based fallback understands common aliases for the three supplied products only; the real LLM path is untested against a live provider.
- **Text only.** Hindi voice notes and handwritten-list photos are not implemented. No offline AI.
- **Salesman screens and offline draft sync are not built** (the salesman role, assignment model and authorised API access exist).
- PWA: manifest, icons and an app-shell service worker are included; installability was not verified on a device. The app
  does not work offline (ordering needs the server); API responses are never cached.
- Hindi/English UI toggle covers the interface; server-generated messages (validation, AI notes) are English only.
- Performance numbers are build-time measurements (JS ~76 KB gzipped); "first load under 3 s on slow 3G" was **not measured**.
- Auth token is kept in `sessionStorage` (cleared when the tab closes); no refresh tokens, password reset, or 2FA.
- Login throttling is in-memory (single process). SQLite, no migrations. Credit is demo data with no real credit/banking integration.
- No GST calculation: the brief does not specify GST treatment (shown in the UI as unspecified).
- No live Tally integration: CSV file export only.
