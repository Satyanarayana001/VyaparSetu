
# Company A Retailer Ordering App

A retailer ordering platform built for the **IsoCode Labs take-home brief** (Company A, Jabalpur).

**GitHub Repository:** https://github.com/Satyanarayana001/VyaparSetu

**Live Demo:** Not deployed — run locally using the instructions below.

VyaparSetu supports retailer product discovery and ordering, AI-assisted order capture from Hindi/Hinglish/English text, human review before order placement, and an operations order desk.

## Features

### Retailer

- Browse a product catalogue with case prices, available stock and applicable schemes.
- Add products to a cart and place orders.
- Repeat a previous order and review order history.
- Submit Hindi, Hinglish or English order messages for assisted extraction.
- Review matched products, original phrases, confidence and alternatives.
- Resolve unclear lines and stock/credit issues before confirming an order.

### Order Desk

- View and manage incoming retailer orders.
- Correct product and quantity lines before confirmation.
- Save retailer-specific aliases from corrections.
- Export confirmed orders as a Tally-compatible CSV.

### Security and Validation

- Retailer and order-desk roles are separated.
- Retailer data is isolated by account.
- Product, quantity, stock, scheme and credit validations are performed by the backend.
- AI suggestions do not place orders automatically; a retailer must review and confirm.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, TypeScript, Vite, Tailwind CSS, React Router, TanStack Query, Lucide |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite |
| Testing | Pytest, Vitest, Browser E2E |

## Requirements

- Python 3.11+
- Node.js 20+
- npm

## Local Setup

The project runs locally using two terminals. No hosted deployment is required.

### 1. Backend Setup

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

Open `backend/.env` and configure a local `JWT_SECRET`.

Generate a secure secret:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copy the generated value into `JWT_SECRET` in your `.env` file.

Start the backend:

```bash
uvicorn app.main:app --reload --port 8000
```

The backend creates SQLite tables and seeds synthetic demo data on first startup when `SEED_DEMO_DATA=true`.

- API: http://localhost:8000
- API documentation: http://localhost:8000/api/docs

### 2. Frontend Setup

Open a second terminal from the repository root.

```bash
cd frontend
npm install
```

Create the frontend environment file.

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

Start the frontend:

```bash
npm run dev
```

Open http://localhost:5173.

The Vite development server proxies `/api` requests to the backend running on port 8000.

## Demo Accounts

These are synthetic accounts for local evaluation only.

| Role | Email | Password |
|---|---|---|
| Retailer 1 (Sharma; credit headroom) | `retailer1@demo.test` | `Retailer@123` |
| Retailer 2 (tight credit limit) | `retailer2@demo.test` | `Retailer@123` |
| Order Desk | `desk@demo.test` | `Desk@12345` |

Public registration creates retailer accounts only. Order-desk accounts are provisioned separately.

## Running Tests

Install backend and frontend dependencies before running the test suites.

### Backend — Pytest

From the repository root:

```bash
cd backend
python -m pytest -q
```

The backend test suite covers:

- Authentication and retailer isolation
- Order workflows
- Pricing and catalogue rules
- AI order parsing
- LLM provider HTTP behaviour
- Order-desk corrections
- Tally CSV export

**Verified result:** 107 tests passed.

### Frontend — Vitest and Build

```bash
cd frontend
npm test
npm run typecheck
npm run build
```

The build command type-checks the TypeScript application and creates the production frontend bundle.

**Verified results:**
- Vitest: 16 tests passed.
- TypeScript typecheck: passed.
- Production build: passed.
- Brotli precompression: 19 files processed.

The production build reports a main JavaScript bundle of 246.01 KB (79.42 KB gzip). Vite displays a non-blocking advisory because this chunk exceeds its 200 KB recommendation.

### Browser End-to-End Tests

The browser E2E suite uses Chromium and changes demo database state. Run it only after building the frontend and resetting demo data.

First, start the backend:

```bash
cd backend
python -m app.seed --reset
uvicorn app.main:app --port 8000
```

In another terminal, set the Chrome executable path.

**Windows PowerShell**

```powershell
cd frontend
$env:CHROME_PATH = "C:\Path\To\chrome.exe"
npm run e2e
```

**macOS / Linux**

```bash
cd frontend
CHROME_PATH="/path/to/chrome" npm run e2e
```

Set the path to your local Chrome or Chromium executable.

Reset the demo database after the E2E run if you want to restore the original sample data.

Browser E2E results should be reported separately from the verified backend and frontend test results above.

## 5-Minute Demo Walkthrough

1. Sign in as **Retailer 1**. Review the dashboard, credit information, repeat-order action and recent orders.
2. Open **Shop**. Inspect the three sample products, case prices, stock and schemes. Tea is out of stock and cannot be added.
3. Open **Message** and select the first sample message. Choose **Read my order**. The reader should match five cases of biscuits and two cases of detergent. The tea line is flagged as out of stock and blocks confirmation until removed.
4. Try the second sample message to see product or unit clarification.
5. Confirm a valid order. Sign in as **Order Desk**, open the order, correct a line and enable **Remember these words**, then confirm the order.
6. Open **Tally Export**, select the confirmed order and download the CSV. Check **Retailer Words** for the saved alias.
7. Sign in as Retailer 1 and submit a message containing the saved words to see the retailer-specific alias match.
8. Sign in as **Retailer 2** and try ordering three cases of detergent. The backend should reject the order when it exceeds the available credit.

## AI Order Capture

The submitted local configuration uses the built-in rule-based reader when no model provider is configured.

The interface identifies this mode as:

**Basic reader (no AI model connected)**

An external LLM is optional. The application validates extracted SKUs and quantities and still requires human review and confirmation.

The LLM integration supports OpenAI-compatible and Anthropic API formats. Its HTTP behaviour is tested using a mock server; it has not been verified against a live model in this submission.

Optional model configuration is documented in `backend/.env.example`.

Keep provider API keys in backend environment variables only. Never place secrets in frontend environment variables or commit `.env` files.

## Repository Structure

```text
backend/
├── app/
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   └── services/
├── tests/
└── .env.example

frontend/
├── src/
│   ├── pages/
│   ├── components/
│   ├── lib/
│   └── __tests__/
└── .env.example

docs/
├── build_tdd.py
└── TDD.pdf

deployment.md
README.md
```

See [`docs/TDD.pdf`](docs/TDD.pdf) for architecture, assumptions, design decisions, scope cuts, testing details and future work.

## GitHub Submission

**Repository:** https://github.com/Satyanarayana001/VyaparSetu

The application is not deployed. No live URL is available. The complete application can be run locally using the instructions in this README.

Before submission:

- Keep `.env` files, API keys, passwords and local databases out of Git.
- Commit `.env.example` templates only.
- Preserve the existing Git history.
- Ensure the repository is public.
- Include `docs/TDD.pdf` and `deployment.md` in the repository.

## Scope and Limitations

The submitted implementation focuses on the core retailer ordering and order-desk workflow.

The following optional or production integrations are not implemented:

- Hindi voice-note transcription.
- Handwritten order photo OCR.
- Salesman-facing offline ordering and synchronization.
- Live Tally, WhatsApp or payment integrations.
- Production deployment and managed database hosting.
- Live LLM verification.

These are documented as potential future improvements rather than completed features.
