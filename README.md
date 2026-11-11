# Company A Retailer Ordering App

A working retailer ordering platform for the IsoCode Labs take-home brief (Company A, Jabalpur): retailer catalogue with
prices, stock and schemes; cart and order creation; AI order capture from Hindi/Hinglish/English text; human review and
confirmation; an order desk with line correction, retailer-specific aliases and Tally-compatible CSV export.

**Stack:** React + TypeScript + Vite + Tailwind + React Router + TanStack Query + Lucide | FastAPI + Pydantic + SQLAlchemy + SQLite | Pytest + Vitest.

## Run it (two terminals)

```bash
# 1. Backend  (http://localhost:8000, API docs at /api/docs)
cd backend
python3 -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload --port 8000                # creates and seeds the SQLite DB on first start

# 2. Frontend (http://localhost:5173, proxies /api to :8000)
cd frontend
npm install
npm run dev
```

Demo logins (synthetic, local only; one-click buttons appear on the sign-in screen in dev):

| Role | Email | Password |
|---|---|---|
| Retailer 1 (Sharma, credit headroom) | retailer1@demo.test | Retailer@123 |
| Retailer 2 (tight credit limit) | retailer2@demo.test | Retailer@123 |
| Order desk | desk@demo.test | Desk@12345 |

## Tests

```bash
cd backend && source .venv/bin/activate && python -m pytest -q     # 107 tests (incl. mock-LLM-server HTTP tests)
cd frontend && npm test                                            # 16 tests (jsdom)
cd frontend && npm run build                                       # type-checks, builds, writes Brotli copies

# Browser end-to-end: 24 steps in real Chromium. It MUTATES the demo DB, so reset the seed afterwards.
cd backend && python -m app.seed --reset && uvicorn app.main:app --port 8000   # also serves the built UI
cd frontend && CHROME_PATH="/path/to/chrome" npm run e2e
```

## 5-minute demo script

1. Sign in as **retailer1**. Home shows credit (demo data), "repeat last order" and recent orders.
2. **Shop**: three products, case prices, stock, schemes. Tea shows *Out of stock* and can't be added.
3. **Message**: tap the first example (the brief's sample message) and *Read my order*. Biscuit 5 and detergent 2 are matched;
   tea is flagged out of stock and blocks *Confirm order* until you remove it. Try the second example to see unit/product clarification.
4. Confirm the order, then sign in as **desk**. Open it, correct a line's product (tick "Remember these words"), confirm the order.
5. **Tally export**: select the confirmed order and download the CSV. **Retailer words** shows the saved alias.
6. As retailer1 again, read a message using those words: the saved alias is used (marked "Your saved word").
7. As **retailer2**, order 3 cases of detergent: the backend refuses it (credit limit), demonstrating the credit hold.

AI mode: no LLM is configured in the submitted build, so it runs the rule-based reader. With no `LLM_API_KEY` the UI says **"Basic reader (no AI model connected)"** (rule-based fallback). See `deployment.md` to connect a model.

## Repository layout

```
backend/app/        FastAPI app: models, schemas, routers, services (pricing, parser, LLM, orders, CSV)
backend/tests/      Pytest suite (auth, isolation, pricing, orders, AI, desk, export)
frontend/src/       React app: pages, components, lib (api, auth, cart, i18n), __tests__
docs/               Technical Design Document (PDF + source generator)
deployment.md       Setup, environment variables, deployment, known limitations
```

See `docs/TDD.pdf` for architecture, assumptions, features cut and future work.
