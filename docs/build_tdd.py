
"""Generate TDD.pdf for the VyaparSetu FMCG retailer ordering application.
Run: python build_tdd.py (requires reportlab).
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

GITHUB_URL = "https://github.com/Satyanarayana001/VyaparSetu"
LIVE_URL = "Not deployed (no live URL exists)"

INK = colors.HexColor("#1F2933")
GREEN = colors.HexColor("#246B52")
LINE = colors.HexColor("#DCE5DF")
HEADER_BG = colors.HexColor("#E8F1EC")

ss = getSampleStyleSheet()

body = ParagraphStyle(
    "body",
    parent=ss["BodyText"],
    fontName="Helvetica",
    fontSize=9.6,
    leading=13.4,
    textColor=INK,
    spaceAfter=5,
)

h1 = ParagraphStyle(
    "h1",
    parent=body,
    fontName="Helvetica-Bold",
    fontSize=15,
    leading=19,
    spaceBefore=12,
    spaceAfter=6,
    textColor=GREEN,
)

h2 = ParagraphStyle(
    "h2",
    parent=body,
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=14,
    spaceBefore=8,
    spaceAfter=3,
)

title = ParagraphStyle(
    "title",
    parent=body,
    fontName="Helvetica-Bold",
    fontSize=22,
    leading=27,
    spaceAfter=4,
)

small = ParagraphStyle(
    "small",
    parent=body,
    fontSize=8.4,
    leading=11.4,
)

cell = ParagraphStyle(
    "cell",
    parent=body,
    fontSize=8.6,
    leading=11.2,
    spaceAfter=0,
)


def P(text, style=body):
    return Paragraph(text, style)


def bullets(items):
    return ListFlowable(
        [ListItem(P(item), leftIndent=10) for item in items],
        bulletType="bullet",
        start="•",
        leftIndent=12,
        bulletFontSize=8,
    )


def make_table(rows, widths, header=True):
    data = [[P(str(value), cell) for value in row] for row in rows]

    table = Table(
        data,
        colWidths=widths,
        repeatRows=1 if header else 0,
    )

    styles = [
        ("GRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]

    if header:
        styles.append(
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG)
        )

    table.setStyle(TableStyle(styles))
    return table


W = A4[0] - 40 * mm
S = []

# ---------------------------------------------------------------------
# Cover and project information
# ---------------------------------------------------------------------

S += [
    P("Technical Design Document", title),
    P(
        "Company A Retailer Ordering App - "
        "IsoCode Labs Take-Home Assignment",
        h2,
    ),
    Spacer(1, 4),
]

S += [
    make_table(
        [
            ["GitHub repository", GITHUB_URL],
            ["Live application", LIVE_URL],
            ["Author", "Satyanarayana"],
            ["Submission date", "13 November 2026"],
        ],
        [38 * mm, W - 38 * mm],
        header=False,
    )
]

S += [
    Spacer(1, 4),
    P(
        "<b>Submission note.</b> The GitHub URL above points to the "
        "public source repository. This document describes the "
        "implemented application. Features that were not built or "
        "verified are explicitly identified. Business figures in the "
        "assignment brief are client-provided context only. The "
        "application has not been run in production, and no production "
        "savings or results are claimed.",
        small,
    ),
]

# ---------------------------------------------------------------------
# 1. Summary
# ---------------------------------------------------------------------

S += [
    P("1. Summary", h1),
    P(
        "VyaparSetu is a retailer ordering platform for an FMCG "
        "distributor serving approximately 1,800 kirana retailers. "
        "Retailers can sign in, browse a product catalogue with "
        "applicable prices, stock and schemes, build a cart, or enter "
        "an order in Hindi, Hinglish or English. They review the "
        "system's interpretation before confirming."
    ),
    P(
        "The order desk can review incoming orders, correct "
        "mis-matched product lines, save retailer-specific aliases, "
        "update order statuses and download a Tally-compatible CSV. "
        "The backend is the source of truth for pricing, schemes, "
        "stock, credit checks and order totals."
    ),
    P(
        "The implemented core includes catalogue browsing, cart and "
        "order creation, text-based AI-assisted order capture, "
        "human review and confirmation, order-desk correction, "
        "and CSV export. Optional features such as salesman offline "
        "sync, voice notes and photo capture were not implemented."
    ),
]

# ---------------------------------------------------------------------
# 2. Architecture
# ---------------------------------------------------------------------

S += [
    P("2. Architecture", h1),
    make_table(
        [
            ["Layer", "Components", "Communication"],
            [
                "Browser",
                "React SPA, PWA shell, Login, Home, Shop, Cart, "
                "AI Message, Orders, Desk and Tally export.",
                "REST/JSON with Bearer token",
            ],
            [
                "API",
                "FastAPI routers for authentication, catalogue, "
                "orders, AI capture, desk and salesman workflows.",
                "SQLite and optional LLM provider",
            ],
            [
                "Database",
                "SQLite tables for users, retailers, salesmen, "
                "products, schemes, aliases, orders and order items.",
                "SQLAlchemy",
            ],
            [
                "LLM provider",
                "Optional OpenAI-compatible or Anthropic API "
                "using server-side credentials.",
                "HTTP API",
            ],
        ],
        [32 * mm, W - 75 * mm, 43 * mm],
    ),
    P(
        "The API can serve the built frontend from the same origin. "
        "During development, Vite proxies API requests to FastAPI. "
        "Pricing and stock calculations are performed by the backend. "
        "LLM output is treated as untrusted input, validated, and "
        "presented for human confirmation."
    ),
]

# ---------------------------------------------------------------------
# 3. Technology choices
# ---------------------------------------------------------------------

S += [
    P("3. Technology Choices", h1),
    make_table(
        [
            ["Technology", "Purpose"],
            [
                "React, TypeScript, Vite and Tailwind CSS",
                "Responsive frontend application and styling.",
            ],
            [
                "React Router",
                "Application navigation and lazy-loaded routes.",
            ],
            [
                "TanStack Query",
                "Server-state caching, loading and error handling.",
            ],
            [
                "Lucide React",
                "Interface icons.",
            ],
            [
                "FastAPI and Pydantic",
                "Backend APIs, validation and typed schemas.",
            ],
            [
                "SQLAlchemy and SQLite",
                "Relational data persistence.",
            ],
            [
                "bcrypt and JWT",
                "Password hashing and authentication.",
            ],
            [
                "httpx",
                "Optional LLM provider HTTP integration.",
            ],
            [
                "Pytest, Vitest and React Testing Library",
                "Backend and frontend automated testing.",
            ],
        ],
        [50 * mm, W - 50 * mm],
    ),
]

# ---------------------------------------------------------------------
# 4. Data model
# ---------------------------------------------------------------------

S += [
    P("4. Data Model", h1),
    P(
        "All monetary values are stored as integer paise. Order items "
        "retain product, packaging, case size, price and scheme "
        "snapshots so that later catalogue changes do not alter "
        "historical orders."
    ),
    make_table(
        [
            ["Table", "Purpose"],
            ["users", "Authentication, role and account associations."],
            ["retailers", "Retailer profile, credit limit and outstanding."],
            ["salesmen", "Salesman profile and retailer assignments."],
            ["products", "SKU, product name, packaging, case size and stock."],
            ["schemes", "Free-goods and percentage-discount rules."],
            ["retailer_prices", "Optional retailer-specific price overrides."],
            ["retailer_aliases", "Retailer-specific product name aliases."],
            ["ai_parses", "Stored AI interpretation and parsing metadata."],
            ["orders", "Order status, retailer, source and monetary totals."],
            ["order_items", "Product quantities, price snapshots and AI audit data."],
        ],
        [36 * mm, W - 36 * mm],
    ),
]

# ---------------------------------------------------------------------
# 5. Main application workflows
# ---------------------------------------------------------------------

S += [
    P("5. Main Workflows", h1),
    P("5.1 Catalogue and order creation", h2),
    bullets(
        [
            "<b>GET /catalogue</b> returns products, applicable retailer "
            "prices, stock and schemes.",
            "Cart changes are sent to <b>POST /orders/quote</b> for "
            "server-side price and total calculation.",
            "<b>POST /orders</b> validates product availability, "
            "quantities, schemes, stock and credit before placing an order.",
            "Idempotency keys prevent duplicate order creation.",
        ]
    ),
    P("5.2 Repeat orders", h2),
    P(
        "The previous repeatable order can be retrieved and used as "
        "the basis for a new cart. The cart is re-quoted against "
        "current prices and stock before submission."
    ),
    P("5.3 Order desk", h2),
    P(
        "The order desk can review placed orders, correct product "
        "or quantity mappings, manage retailer-specific aliases, "
        "confirm or reject orders, update statuses and export "
        "confirmed orders as CSV."
    ),
    P("5.4 Credit checks", h2),
    P(
        "The backend calculates available credit using the configured "
        "credit limit, demo outstanding amount and non-rejected orders. "
        "Orders exceeding available credit are rejected."
    ),
]

# ---------------------------------------------------------------------
# 6. AI order capture
# ---------------------------------------------------------------------

S += [
    P("6. AI-Assisted Order Capture", h1),
    P(
        "The order capture workflow accepts retailer messages and "
        "attempts to identify product names, quantities and packaging. "
        "The extracted result is validated and shown to the retailer "
        "for review. Parsing alone never places an order."
    ),
    make_table(
        [
            ["Area", "Implementation"],
            [
                "LLM integration",
                "Optional OpenAI-compatible or Anthropic API integration "
                "with structured output and request timeouts.",
            ],
            [
                "Fallback parser",
                "Deterministic rule-based parsing when no LLM provider "
                "is configured or when an LLM request fails.",
            ],
            [
                "Validation",
                "Pydantic validation, catalogue SKU checks, quantity "
                "and unit checks, and stock validation.",
            ],
            [
                "Human confirmation",
                "Retailers review, correct or remove interpreted lines "
                "before confirming an order.",
            ],
            [
                "Aliases",
                "Order-desk corrections can save aliases for an "
                "individual retailer.",
            ],
        ],
        [36 * mm, W - 36 * mm],
    ),
    P(
        "<b>AI status in this submission:</b> no live LLM API key was "
        "configured. The delivered application uses its rule-based "
        "fallback parser. The optional LLM integration was tested "
        "using a mock HTTP server, not a live model."
    ),
    P(
        "Example retailer message: <i>bhaiya 5 peti biscuit chhota, "
        "2 peti washing powder 1 kilo, chai patti 250 wala 1 peti</i>. "
        "The system interprets the product lines and flags the tea "
        "product as out of stock. The retailer must review the result."
    ),
]

# ---------------------------------------------------------------------
# 7. Security
# ---------------------------------------------------------------------

S += [
    P("7. Security", h1),
    bullets(
        [
            "Passwords are hashed using bcrypt.",
            "JWT bearer tokens are used for authenticated API requests.",
            "Role-based access checks protect application routes.",
            "Retailer data is scoped to the authenticated retailer.",
            "Pydantic validates API inputs and request schemas.",
            "CORS origins are configured through environment variables.",
            "LLM API credentials, when configured, remain server-side.",
            "CSV formula injection is handled during export.",
        ]
    ),
]

# ---------------------------------------------------------------------
# 8. UI design
# ---------------------------------------------------------------------

S += [
    P("8. UI Design Decisions", h1),
    P(
        "The interface uses a clean, mobile-first design with "
        "forest-green accents and neutral surfaces. Product, cart, "
        "retailer and order-desk workflows use consistent spacing, "
        "clear information hierarchy and status colours."
    ),
    bullets(
        [
            "The retailer home screen prioritises credit information, "
            "order-by-message, repeat order, catalogue and recent orders.",
            "The catalogue displays product illustrations, case pricing, "
            "stock and scheme information.",
            "The cart displays server-computed order totals.",
            "AI alternatives are available for unclear product matches.",
            "The order desk provides order review, correction and export workflows.",
            "The interface supports Hindi and English language selection.",
            "Responsive navigation supports retailer phone screens "
            "and desktop order-desk workflows.",
        ]
    ),
]

# ---------------------------------------------------------------------
# 9. Assumptions
# ---------------------------------------------------------------------

S += [
    P("9. Assumptions", h1),
    bullets(
        [
            "Dealer prices are interpreted as prices per individual pack. "
            "Case prices are calculated using the case size.",
            "The biscuit buy-10-get-1-free scheme applies to completed "
            "groups of ten cases.",
            "The detergent discount applies to eligible orders of "
            "five or more cases.",
            "GST treatment was not specified in the assignment, so "
            "no GST rate is invented or applied.",
            "Stock is reserved when an order is placed and returned "
            "when an order is rejected.",
            "Credit figures are demo data and do not represent a "
            "live accounting integration.",
            "Quantities are whole cases. Unspecified units are not "
            "automatically converted.",
        ]
    ),
]

# ---------------------------------------------------------------------
# 10. Testing and results
# ---------------------------------------------------------------------

S += [
    P("10. Testing and Results", h1),
    P(
        "The following results were recorded from the delivered "
        "project's automated test and build commands."
    ),
    make_table(
        [
            ["Suite", "Verified result"],
            [
                "Backend tests (pytest)",
                "<b>107 passed</b> in 59.92 seconds. "
                "Includes authentication, role separation, data isolation, "
                "pricing, schemes, orders, stock, credit, AI parsing, "
                "order-desk workflows and CSV export.",
            ],
            [
                "Frontend tests (Vitest)",
                "<b>16 passed</b> across 5 test files.",
            ],
            [
                "TypeScript",
                "<b>Passed.</b> npm run typecheck completed without errors.",
            ],
            [
                "Production build",
                "<b>Passed.</b> Vite production build completed successfully.",
            ],
            [
                "JavaScript bundle",
                "Main JavaScript bundle: 246.01 KB minified, "
                "79.42 KB gzip.",
            ],
            [
                "CSS bundle",
                "26.53 KB, 5.75 KB gzip.",
            ],
            [
                "Brotli precompression",
                "19 files, 338.1 KB reduced to 95.4 KB.",
            ],
            [
                "Browser E2E",
                "An E2E script is present in the repository. "
                "A complete browser E2E run was not independently "
                "verified for this submission; no pass count is claimed.",
            ],
        ],
        [37 * mm, W - 37 * mm],
    ),
    P(
        "<b>Build note:</b> Vite reported a non-blocking warning that "
        "one JavaScript chunk exceeds 200 KB after minification."
    ),
    P(
        "<b>Not verified:</b> live LLM provider operation, production "
        "deployment, physical-device PWA installation, Safari and "
        "Firefox compatibility, Lighthouse scores, screen-reader "
        "behaviour and real-network performance measurements."
    ),
]

# ---------------------------------------------------------------------
# 11. Features not implemented
# ---------------------------------------------------------------------

S += [
    P("11. Features Not Implemented", h1),
    bullets(
        [
            "Hindi voice-note transcription.",
            "Handwritten order-list photo recognition.",
            "Salesman-facing interface and offline draft synchronisation.",
            "Offline ordering and offline AI processing.",
            "Live Tally, credit, payment and WhatsApp integrations.",
            "GST computation, payment processing and returns management.",
            "Database migrations, CI pipeline and distributed rate limiting.",
        ]
    ),
]

# ---------------------------------------------------------------------
# 12. Future improvements
# ---------------------------------------------------------------------

S += [
    P("12. Future Improvements", h1),
    bullets(
        [
            "Deploy with a managed database and HTTPS.",
            "Add database migrations and continuous integration.",
            "Add Hindi voice-note transcription and handwritten-list OCR.",
            "Build a salesman PWA with offline drafts and synchronisation.",
            "Evaluate the LLM extraction workflow against labelled "
            "retailer messages.",
            "Add audit logging, bulk order-desk actions and "
            "retailer-specific price lists.",
        ]
    ),
]

# ---------------------------------------------------------------------
# Generate PDF
# ---------------------------------------------------------------------

document = SimpleDocTemplate(
    "TDD.pdf",
    pagesize=A4,
    leftMargin=20 * mm,
    rightMargin=20 * mm,
    topMargin=18 * mm,
    bottomMargin=18 * mm,
    title="Technical Design Document - VyaparSetu",
    author="Satyanarayana",
)

document.build(S)

print("TDD.pdf generated successfully.")
