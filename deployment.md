
# Deployment and Local Setup

**GitHub Repository:** https://github.com/Satyanarayana001/VyaparSetu

**Deployment status:** Not deployed.

This project is submitted through GitHub. No live deployment URL is available.

The deployment instructions below describe local setup and a possible future single-service deployment. The future deployment steps have not been executed.

## 1. Prerequisites

- Python 3.11+ (developed with Python 3.12)
- Node.js 20+ (developed with Node.js 22)
- npm
- Git

## 2. Local Setup

### Backend

Open a terminal from the repository root.

**Windows PowerShell**

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
cp .env.example .env
```

Open `backend/.env` and configure a secure local `JWT_SECRET`.

Generate a random secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `JWT_SECRET`.

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

Backend address: http://localhost:8000

API documentation: http://localhost:8000/api/docs

### Database Initialization

The application uses SQLite. Database tables are created automatically on startup. Demo data is seeded when the database is empty and `SEED_DEMO_DATA=true`.

To reset the database to the initial demo state, run from the backend directory:

```bash
python -m app.seed --reset
```

The reset restores the supplied sample inventory.

There are currently no database migrations. The schema is created using SQLAlchemy `create_all`.

### Frontend

Open a second terminal from the repository root.

```bash
cd frontend
npm install
```

Create the local environment file.

**Windows PowerShell**

```powershell
Copy-Item .env.example .env
```

**macOS / Linux**

```bash
cp .env.example .env
```

For local demo shortcuts, configure `frontend/.env`:

```dotenv
VITE_API_BASE=
VITE_SHOW_DEMO_LOGINS=true
```

Start the development server:

```bash
npm run dev
```

Frontend address: http://localhost:5173

The Vite development proxy forwards API requests to the backend at http://localhost:8000.

## 3. Build and Test Commands

### Backend tests

Run from the backend directory:

```bash
python -m pytest -q
```

**Verified result: 107 passed.**

A Starlette/httpx deprecation warning was reported. It did not cause test failures.

### Frontend tests and production build

Run from the frontend directory:

```bash
npm test
npm run typecheck
npm run build
```

**Verified results:**

- Vitest: 16 tests passed.
- TypeScript typecheck: passed.
- Vite production build: passed.
- Brotli precompression: 19 files processed.

The production build reported a 246.01 KB main JavaScript bundle (79.42 KB gzip). Vite displayed a non-blocking advisory because the chunk exceeds its 200 KB recommendation.

Browser E2E tests require a running backend and the built frontend. Refer to the README for E2E setup. No browser E2E result is claimed in this document.

## 4. Environment Variables

Only variable names are listed here. Do not commit actual secrets, passwords, or API keys to the repository.

### Backend

| Variable | Purpose |
|---|---|
| `APP_ENV` | Application environment |
| `DATABASE_URL` | Database connection string |
| `JWT_SECRET` | Token signing secret |
| `ACCESS_TOKEN_MINUTES` | Access token lifetime |
| `CORS_ORIGINS` | Allowed frontend origins |
| `SEED_DEMO_DATA` | Enable synthetic demo data |
| `LOGIN_MAX_FAILURES` | Login failure threshold |
| `LOGIN_LOCKOUT_SECONDS` | Login lockout duration |
| `LLM_PROVIDER` | Optional LLM provider |
| `LLM_API_KEY` | Server-side model API key |
| `LLM_MODEL` | Model identifier |
| `LLM_BASE_URL` | Optional provider base URL |
| `LLM_TIMEOUT_SECONDS` | Model request timeout |
| `FRONTEND_DIST` | Optional built frontend directory |

### Frontend

| Variable | Purpose |
|---|---|
| `VITE_API_BASE` | API base URL |
| `VITE_SHOW_DEMO_LOGINS` | Show local demo login shortcuts |

**Security notes:**

- Keep `JWT_SECRET` private and use a strong random value outside local development.
- Keep `LLM_API_KEY` on the backend only.
- Never expose backend secrets through frontend environment variables.
- Do not commit `.env` files.
- Commit the supplied `.env.example` templates only.
- If `JWT_SECRET` is not configured, the backend generates a random per-process secret. Existing sessions will become invalid after a restart.

## 5. Optional AI Model Configuration

The application supports optional external language models through OpenAI-compatible APIs and Anthropic.

Relevant environment variables:

- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_MODEL`
- `LLM_BASE_URL`
- `LLM_TIMEOUT_SECONDS`

The AI component extracts candidate product lines from retailer messages. The backend validates product identifiers, quantities, stock availability and pricing before an order can be confirmed.

The retailer must review and confirm the extracted order.

If the model request fails, times out, reaches a rate limit or returns invalid output, the application falls back to its rule-based parser.

**AI testing limitation:** Provider integration was tested against a local mock server using the expected OpenAI-compatible and Anthropic request formats. It was not verified against a live provider because no real provider API key was available.

The default local configuration uses the rule-based reader and labels it as:

**Basic reader (no AI model connected)**

## 6. Deployment Information

**Current status: Not deployed.**

The application has not been deployed to Render, Railway, AWS or any other hosting provider. There is no live application URL.

The FastAPI backend can serve the built frontend. A possible future single-service deployment would involve:

1. Installing backend and frontend dependencies.
2. Building the frontend using `npm run build`.
3. Configuring backend environment variables.
4. Configuring persistent database storage.
5. Starting FastAPI with a production ASGI server.
6. Serving the application over HTTPS.

These are proposed deployment steps, not a completed deployment.

A production setup would also require persistent storage, secure secrets, an appropriate production database configuration and deployment-specific security settings.

## 7. Demo Login Credentials

The following synthetic accounts are provided for reviewer evaluation.

| Role | Email | Password |
|---|---|---|
| Retailer 1 | `retailer1@demo.test` | `Retailer@123` |
| Retailer 2 | `retailer2@demo.test` | `Retailer@123` |
| Order Desk | `desk@demo.test` | `Desk@12345` |
| Salesman (API only) | `salesman@demo.test` | `Salesman@123` |

The salesman account has API access but does not have a dedicated salesman user interface.

These credentials are for local demonstration only. Do not use them in a production environment.

## 8. Known Limitations

- The application is not deployed and has no live URL.
- No continuous integration pipeline is configured.
- The AI rule-based fallback supports common aliases for the supplied sample products; it is not a general-purpose product recognition system.
- The live AI provider integration has not been tested against a real provider.
- Hindi voice-note processing and handwritten order-photo recognition are not implemented.
- Salesman screens and offline draft synchronization are not implemented.
- The PWA manifest, icons and app-shell service worker are included, but installation has not been verified on a physical device.
- Ordering requires a working server connection; offline ordering is not supported.
- The interface supports English and Hindi, while server-generated validation and AI messages are currently English.
- Authentication uses session storage. Password reset, refresh tokens and two-factor authentication are not implemented.
- Login throttling is in-memory and intended for the current single-process demonstration setup.
- SQLite is used for the demonstration database. Database migrations are not configured.
- Credit information is demonstration data and is not connected to a real financial or banking system.
- GST calculation is not implemented because the supplied brief does not specify the required tax treatment.
- Tally integration is limited to CSV export; there is no direct integration with a live Tally installation.

## 9. Submission

**GitHub Repository:** https://github.com/Satyanarayana001/VyaparSetu

The source code and project documentation are provided in the public GitHub repository.

This submission does not include a live deployment URL because the application has not been hosted.
