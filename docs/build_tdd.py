"""Generates docs/TDD.pdf. Run: python build_tdd.py  (needs reportlab). Edit GITHUB_URL before submitting."""
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, ListFlowable, ListItem, PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table, TableStyle)

GITHUB_URL = "REPLACE-WITH-YOUR-GITHUB-REPOSITORY-URL"   # not available to the author of this document
LIVE_URL = "Not deployed (no live URL exists)"
INK, INDIGO, LINE = colors.HexColor("#12162B"), colors.HexColor("#3640D6"), colors.HexColor("#E3E5EC")

ss = getSampleStyleSheet()
body = ParagraphStyle("body", parent=ss["BodyText"], fontName="Helvetica", fontSize=9.6, leading=13.4, textColor=INK, spaceAfter=5)
h1 = ParagraphStyle("h1", parent=body, fontName="Helvetica-Bold", fontSize=15, leading=19, spaceBefore=12, spaceAfter=6, textColor=INDIGO)
h2 = ParagraphStyle("h2", parent=body, fontName="Helvetica-Bold", fontSize=11, leading=14, spaceBefore=8, spaceAfter=3)
title = ParagraphStyle("title", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=27, spaceAfter=4)
small = ParagraphStyle("small", parent=body, fontSize=8.4, leading=11.4)
cell = ParagraphStyle("cell", parent=body, fontSize=8.6, leading=11.2, spaceAfter=0)
code = ParagraphStyle("code", parent=body, fontName="Courier", fontSize=7.8, leading=10, backColor=colors.HexColor("#F5F6F8"), borderPadding=4)

def P(t, s=body): return Paragraph(t, s)
def bullets(items): return ListFlowable([ListItem(P(i), leftIndent=10) for i in items], bulletType="bullet", start="•", leftIndent=12, bulletFontSize=8)
def table(rows, widths, header=True):
    data = [[P(str(c), cell) for c in r] for r in rows]
    t = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.4, LINE), ("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if header: st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ECEEFF"))]
    t.setStyle(TableStyle(st)); return t

W = A4[0] - 40 * mm
S = []
S += [P("Technical Design Document", title), P("Company A Retailer Ordering App - IsoCode Labs take-home assignment", h2), Spacer(1, 4)]
S += [table([["GitHub repository", GITHUB_URL], ["Live app", LIVE_URL], ["Author", "Final-year B.Tech CSE student (independent submission)"], ["Date", "9 November 2026"]], [38 * mm, W - 38 * mm], header=False)]
S += [Spacer(1, 4), P("<b>Honesty note.</b> The GitHub URL above must be filled in by the author before submission. Everything in this document describes what exists in the repository; items not built are listed under <i>Features cut</i>. Business figures in the brief (600 orders/day, Rs 52.5 lakh combined impact, etc.) are client-provided context only; this application has not been run in production and no savings or results are claimed.", small)]

S += [P("1. Summary", h1), P("A retailer ordering platform for a distributor with ~1,800 kirana customers. Retailers sign in, browse a catalogue with their own prices, stock and schemes, build a cart or <i>type their order in Hindi/Hinglish/English</i>, review what the system understood, and confirm. The order desk reviews incoming orders, corrects mis-mapped lines, saves retailer-specific aliases, updates statuses and downloads a Tally-compatible CSV. The backend is the single source of truth for prices, schemes, stock, credit and totals.")]
S += [P("The core slice from the brief is implemented end-to-end: catalogue, cart/order creation, AI order capture from text, review and human confirmation, order desk with correction, and CSV export. Optional depth (salesman offline mode, voice, photos) is not built.")]

S += [P("2. Architecture", h1)]
S += [table([
["Layer", "Components", "Talks to"],
["Browser (React SPA, PWA shell)", "Pages: Login, Home, Shop, Cart, Message (AI capture), Orders, Desk queue/detail, Tally export, Retailer words. TanStack Query cache. Cart in sessionStorage.", "REST/JSON over HTTPS with a Bearer token"],
["API (FastAPI, one service)", "Routers: auth, catalogue, orders, ai, desk, salesman. Services: pricing/scheme engine, order validation and stock, AI capture (LLM or fallback), aliases, CSV export. Dependencies: role and ownership checks.", "SQLite via SQLAlchemy; optional LLM provider (server-side key only)"],
["Database (SQLite)", "users, retailers, salesmen, products, schemes, retailer_prices, retailer_aliases, ai_parses, orders, order_items.", "-"],
["LLM provider (optional)", "OpenAI-compatible API or Anthropic API, called with structured output and a timeout.", "-"]], [38 * mm, W - 38 * mm - 42 * mm, 42 * mm])]
S += [P("The API can also serve the built SPA (same origin, one deployable). In development Vite proxies <font name='Courier'>/api</font> to the backend. Principles: <b>(1)</b> money and stock logic live only in the backend (integer paise, no floats); <b>(2)</b> the LLM only <i>extracts</i> candidate lines and its output is validated like untrusted input; <b>(3)</b> a human confirms every AI order; <b>(4)</b> authorisation is enforced in dependencies on every route.")]

S += [P("3. Technology choices", h1), table([
["Choice", "Reason"],
["React + TS + Vite + Tailwind", "Required stack. Vite gives small, split bundles; Tailwind keeps CSS to ~5 KB gzipped."],
["React Router (lazy routes)", "Each screen is a separate chunk so the first load only downloads the shell and the current page."],
["TanStack Query", "Server-state caching, loading/error states, and polling of the desk queue (15 s)."],
["Lucide React", "Per-icon imports are tree-shaken (hundreds of bytes each)."],
["System font stack", "No web-font download on slow 3G; Android/Windows system fonts include Devanagari. Trade-off: less typographic distinctiveness."],
["FastAPI + Pydantic", "Typed request validation, uniform error shape, auto OpenAPI in dev."],
["SQLAlchemy 2 + SQLite", "Relational constraints (FKs enforced, CHECKs) with zero setup. Swappable via DATABASE_URL."],
["bcrypt + JWT (HS256)", "Password hashing with salt; short-lived bearer tokens. Token lives in sessionStorage (see limitations)."],
["httpx", "Direct, provider-independent LLM HTTP calls with explicit timeouts; no heavy vendor SDK."],
["Pytest / Vitest + RTL", "API-level tests against a real SQLite DB; component and flow tests in jsdom."]], [50 * mm, W - 50 * mm])]

S += [P("4. Data model", h1), P("All money is stored as integer paise. Order items snapshot product name, packaging, case size, unit/case price, scheme text, discount and free quantity, so later catalogue edits never rewrite history.")]
S += [table([
["Table", "Key fields and constraints"],
["users", "email (unique), bcrypt hash, role (retailer/desk/salesman), retailer_id / salesman_id. CHECK: retailer role must have a retailer."],
["retailers", "code (unique), name, city, salesman_id, credit_limit_paise, outstanding_paise (DEMO data), CHECK >= 0."],
["salesmen", "code (unique), name; one salesman has many retailers."],
["products", "sku (unique), name, name_hi, packaging_label, case_size, unit_price_paise (per pack), stock_cases (CHECK >= 0), is_active."],
["schemes", "product_id, type (free_goods | percent_discount), buy_qty, free_qty, min_cases, percent_bp (300 = 3%), description."],
["retailer_prices", "Optional per-retailer price override (unique retailer+product). Empty in seed data (one dealer price supplied)."],
["retailer_aliases", "retailer_id, product_id, alias_text (normalised); UNIQUE(retailer_id, alias_text). Never global."],
["ai_parses", "Server-side record of each interpretation: message, mode (llm/fallback), reason, model, result lines (JSON)."],
["orders", "order_number, retailer_id, status, source (manual/ai/repeat), original_message, ai_parse_id, totals, idempotency_key; UNIQUE(retailer_id, idempotency_key); exported_at."],
["order_items", "Snapshots + quantity_cases (CHECK > 0), free_cases, gross/discount/line_total, scheme_applied, AI audit: original_phrase, ai_confidence, ai_matched_sku, ai_alternatives, was_corrected."]], [32 * mm, W - 32 * mm])]

S += [P("5. Main flows", h1)]
S += [P("5.1 Catalogue to order", h2), bullets([
"<b>GET /catalogue</b> returns the retailer's own prices (override table first, else dealer price), stock status, scheme and a GST note.",
"The cart lives in the browser (sessionStorage). Every change calls <b>POST /orders/quote</b>; the UI renders only the server's lines, free cases, discounts, totals, issues and credit check.",
"<b>POST /orders</b> re-validates everything: product active, integer quantity 1..10,000, stock (including free cases), scheme, totals, credit. Stock is reserved with an atomic conditional UPDATE; client-supplied prices/totals are ignored.",
"<b>Idempotency:</b> the client sends a key per distinct cart; a repeated key returns the original order (HTTP 200, duplicate=true) and never reserves stock twice."])]
S += [P("5.2 Repeat order", h2), P("<b>GET /orders/last-repeatable</b> returns the previous confirmed/dispatched order as cart lines. The cart is then re-quoted at current prices and stock (a line that is out of stock is flagged and must be removed), the retailer edits quantities and places a new order with source=repeat.")]
S += [P("5.3 Order desk", h2), P("Status machine: placed -> confirmed | rejected; confirmed -> dispatched | rejected; dispatched and rejected are terminal. Rejection needs a reason and returns reserved stock. A line can be corrected (product and/or quantity) only while the order is <i>placed</i>: stock is released and re-reserved in one transaction (a failed correction changes nothing), the line is repriced and totals recomputed. Changing the product with an original AI phrase can save a <b>retailer-specific alias</b>. CSV export includes only confirmed orders (selected or not-yet-exported) and stamps exported_at.")]
S += [P("5.4 Credit hold (demo)", h2), P("Available credit = limit - demo outstanding - sum of this app's non-rejected orders. An order above available credit is refused by the backend (CREDIT_LIMIT_EXCEEDED). Retailer 2 is seeded with Rs 6,000 headroom to demonstrate this.")]

S += [P("6. AI order capture behaviour", h1)]
S += [P("<b>Pipeline.</b> message -> (LLM extraction if configured, else rule-based fallback) -> retailer alias override -> shared validation (<font name='Courier'>ai_capture._finalize</font>) -> stored AiParse -> UI review. Nothing is placed by parsing.")]
S += [table([
["Aspect", "Behaviour"],
["LLM mode", "OpenAI-compatible (json_schema strict output) or Anthropic (forced tool call). Output validated with Pydantic; SKUs not in the catalogue are discarded; confidence clamped 0..1. The message is passed as delimited, untrusted text with an instruction to ignore embedded instructions."],
["Failures", "Timeout, HTTP 429, 5xx/4xx, malformed JSON or schema violation -> fall back to the rule-based parser. The response carries mode=fallback and a reason, and the UI says so. No silent retries."],
["Fallback mode", "Deterministic rules, clearly labelled 'Basic reader (no AI model connected)'. Tokenises Latin and Devanagari, splits lines (commas, 'aur', '+', or repeated 'N peti'), finds quantity next to a packing word (peti/case/carton), separates product specs ('1 kilo', '250 wala', '75g') from quantities, scores products from keywords derived from product names plus a small alias table, understands Hindi/English number words and Devanagari digits. It is not an LLM."],
["Per-line output", "Original words, matched product, SKU, quantity, packaging, confidence, match source (keyword / alias / llm), two alternative SKUs (three when unmatched), validation status, messages, stock, and a priced preview."],
["Statuses", "ok | needs_clarification (product, unit or quantity) | out_of_stock | insufficient_stock | invalid_quantity."],
["Thresholds", "Confidence below 0.70, or a near-tie between two products (<0.15 apart), requires the person to choose the product. Retailer alias match = 0.98."],
["Units", "Only peti/case/carton count as cases. A bare number ('biscuit 5') asks 'cases or packs?'; 'packets/pcs' asks for cases and shows packs per case. The system never assumes or converts."],
["Out of stock", "Tea (stock 0) is shown with its words, flagged 'Out of stock', and blocks confirmation until the line is removed or changed. It is never dropped or shown as available."],
["Human control", "The retailer can switch product (matched + alternatives), edit cases, or remove a line; every edit is re-validated by the backend. Confirm is enabled only when all remaining lines are ready. Orders store the parse id, original message, phrase, confidence and whether the line was corrected."],
["Aliases", "Saved by the order desk per retailer; matched order-insensitively (all alias words present). No cross-retailer or global learning."]], [32 * mm, W - 32 * mm])]
S += [P("Sample message result: <i>'bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti'</i> -> Glucose biscuit 75 g x5 (ok), Detergent powder 1 kg x2 (ok), Tea leaf 250 g x1 (out of stock). The test suite also covers Devanagari input, no-comma input, number words, ambiguity, unmatched words, invalid quantities and insufficient stock.")]

S += [P("7. Security", h1), bullets([
"bcrypt password hashes; identical error for unknown user vs wrong password; a dummy hash check equalises timing; in-memory login throttling (5 failures/60 s per email+IP).",
"JWT bearer tokens (8 h). Role checks via dependencies on every route; retailers are scoped by token to their own retailer id, never by a client-supplied id. Cross-tenant lookups return 404 (no existence leak). Salesmen reach only assigned retailers.",
"Pydantic validation everywhere (strict integer quantities, length limits, idempotency key pattern); uniform error body without stack traces or echoed input; search input escaped for LIKE wildcards.",
"CORS allow-list from env, no credentials; security headers (nosniff, frame deny, referrer policy); API responses are no-store; docs disabled in production.",
"Secrets only in environment variables; the LLM key is server-side only. CSV formula-injection neutralised. Query-cache and cart are cleared on sign-out."])]

S += [P("8. UI design decisions", h1), P("Primary style is <b>minimalism with a modern bento layout</b> (home screen tiles of different sizes for credit, order-by-message, repeat order, catalogue, recent orders). <b>Subtle glassmorphism</b> is limited to the sticky top bar and bottom navigation (translucent white with blur). <b>Neo-brutalist accents</b> (2 px ink border and hard offset shadow) are used only for the primary action, scheme tags and the out-of-stock chip so that the important things stand out against a quiet neutral background. Palette: cool neutral background, white surfaces, ink text, one indigo accent, with green/amber/red reserved for status.")]
S += [bullets([
"Catalogue is built for use between customers: large product illustrations (lightweight inline SVG, unbranded), case price in large type, packs x unit price beneath, stock and scheme visible without tapping, 48 px steppers and buttons.",
"Mobile-first: bottom navigation with thumb-reachable targets; desk uses a two-pane layout on desktop and a single pane on phones. Skeleton, empty and error states on every data screen; offline banner.",
"Hindi/English toggle for the interface (product names include Hindi translations added for display). Colours were chosen for AA-level contrast but no formal accessibility audit was run.",
"No fake analytics, decorative charts or hero sections."])]

S += [P("9. Assumptions (explicit)", h1), table([
["ID", "Assumption and rationale"],
["A1", "<b>Dealer price is per pack, not per case.</b> A case of 96 biscuit packs at Rs 8.10 gives Rs 777.60 per case; Rs 8.10 for a whole case of 96 would be implausible. Case price = price x case size: Rs 777.60 / 2,030.00 / 4,720.00 (biscuit / detergent / tea). The supplied prices are unchanged; the UI shows both figures."],
["A2", "Biscuit scheme 'buy 10, get 1 free': free cases = floor(qty/10) (completed groups only; 9 -> 0, 10 -> 1, 19 -> 1, 20 -> 2). Free cases are not charged and come from the same stock, so 340 in stock allows at most 309 + 30 free."],
["A3", "Detergent '3% off for 5+ cases' applies to that product's line total (qty x case price), rounded half-up to the paisa; no discount below 5 cases."],
["A4", "<b>GST:</b> the brief does not state GST treatment. No GST rate is invented or added; the UI and API state that GST is unspecified."],
["A5", "Stock is reserved when the retailer places the order and returned if the order is rejected."],
["A6", "Credit data is synthetic demo data. Exposure counts demo outstanding plus non-rejected orders placed through this app; no payments or approvals are modelled."],
["A7", "A placed order waits for desk review; only 'confirmed' orders are exported. Re-export is possible by choice (include_exported)."],
["A8", "Quantities are whole cases. Pieces/packs or an unstated unit are never converted or assumed."],
["A9", "One dealer price for every retailer (a per-retailer override table exists but is empty). Hindi product names are display translations."],
["A10", "Desk corrections are allowed only while an order is 'placed'; they do not re-run the credit check (a human is making the change)."]], [12 * mm, W - 12 * mm])]

S += [P("10. Testing and results", h1), P("Run on the delivered code in the build environment:")]
S += [table([
["Suite", "Result"],
["Backend (pytest)", "97 passed in ~7 s. Covers: login/hashing/throttle, token errors, role separation, retailer data isolation (orders, prices, credit, aliases, AI parses, repeat references), salesman scoping, catalogue data and search, scheme boundaries (9/10/11/19/20; 4/5/6 cases), half-up rounding, invalid quantities, quote/order creation and snapshots, stock reservation including free cases, idempotency, credit hold, repeat flow, AI parsing (sample message, Devanagari, number words, no commas, ambiguity, unit clarification, unmatched words, stock flags), LLM path with fake providers, provider HTTP errors/timeouts/invalid output, desk status machine, corrections with alias saving and rollback, alias management, CSV columns/values/selection/formula-injection."],
["Frontend (vitest)", "16 passed: money formatting, cart reducer limits, AI-review gating rules, stepper bounds, login errors, and a full AI-review flow rendered against API responses captured from the real backend (sample message -> tea flagged -> confirm blocked -> remove -> confirm sends source=ai without prices)."],
["Build", "tsc --noEmit clean; vite build OK. Initial JS 76 KB gzipped, CSS 4.9 KB gzipped, each screen a 1-4 KB gzipped lazy chunk; responses gzip-compressed by the API; hashed assets cached for a year."],
["Server smoke test", "Real uvicorn process: login, AI parse, order, duplicate key, desk confirm, CSV download, 403 for role violation, SPA fallback, JSON 404."]], [32 * mm, W - 32 * mm])]
S += [P("<b>Not verified:</b> real-LLM calls; rendering in a real browser/device (no headless browser available in the build environment); PWA installability; Lighthouse or slow-3G timing; screen-reader behaviour.")]

S += [P("11. Features cut (and why)", h1), bullets([
"Hindi voice notes and handwritten-list photos: outside the required text core; would add speech-to-text/vision providers.",
"Salesman interface and offline draft sync: optional depth. The salesman role, retailer assignment and scoped API access exist; no screens or sync.",
"Offline ordering/AI: the service worker caches only static assets; API data is never cached.",
"Real Tally/credit/WhatsApp integrations (mocked per brief); GST computation; payments; returns/redelivery.",
"Database migrations, CI pipeline, distributed rate limiting, browser E2E tests."])]
S += [P("12. Future improvements", h1), bullets([
"Deploy with a managed database and HTTPS; add Alembic migrations and CI (tests + build + bundle budget).",
"Voice-note transcription (Hindi) feeding the same review pipeline; photo OCR of handwritten lists.",
"Salesman PWA with IndexedDB drafts and idempotent sync using the existing idempotency keys.",
"Evaluate the LLM path on a labelled set of real retailer messages (precision on SKU/units, calibration of confidence) before trusting thresholds; add per-retailer frequent-item priors.",
"Server-side message localisation, httpOnly-cookie sessions with CSRF protection, audit log, desk bulk actions, price lists per retailer."])]

SimpleDocTemplate("TDD.pdf", pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
                  title="Technical Design Document - Company A Retailer Ordering App", author="Candidate").build(S)
print("TDD.pdf written")
