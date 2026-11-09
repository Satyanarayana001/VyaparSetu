import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import fixtures from "./fixtures/ai-flow.json";
import { I18nProvider } from "../lib/i18n";
import Message from "../pages/Message";

// Fixtures were captured from the real backend for the client's sample message (see fixtures/ai-flow.json).
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

function mockApi() {
  const calls: { url: string; body: any }[] = [];
  vi.spyOn(globalThis, "fetch").mockImplementation(async (input, init) => {
    const url = String(input);
    const body = init?.body ? JSON.parse(String(init.body)) : null;
    calls.push({ url, body });
    if (url.endsWith("/ai/status")) return json({ mode: "fallback", model: null, reason: "No LLM API key configured" });
    if (url.endsWith("/ai/parse")) return json(fixtures.parse);
    if (url.endsWith("/orders/quote")) return json(body.items.some((i: any) => i.sku === "SKU-TE-250") ? fixtures.quote_all : fixtures.quote_ok);
    if (url.endsWith("/orders")) return json({ order: { id: 1 }, duplicate: false }, 201);
    return json({ error: { code: "X", message: "unexpected" } }, 500);
  });
  return calls;
}

function setup() {
  return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><I18nProvider initial="en"><MemoryRouter><Message /></MemoryRouter></I18nProvider></QueryClientProvider>);
}

describe("AI order capture review (sample message from the brief)", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shows fallback mode honestly, flags the out-of-stock tea, and only confirms after it is removed", async () => {
    const calls = mockApi();
    const user = userEvent.setup();
    setup();
    expect(await screen.findByText(/Basic reader \(no AI model connected\)/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Order by message"), fixtures.parse.original_message);
    await user.click(screen.getByRole("button", { name: "Read my order" }));

    // three lines, with the customer's own words shown
    expect(await screen.findByText("5 peti biscuit chhota")).toBeInTheDocument();
    expect(screen.getByText("2 peti washing powder 1 kilo")).toBeInTheDocument();
    expect(screen.getByText("chai patti 250 wala 1 peti")).toBeInTheDocument();

    // tea is flagged, never silently dropped or shown as available
    await waitFor(() => expect(screen.getByText(/Tea leaf 250 g is out of stock/)).toBeInTheDocument());
    const confirm = screen.getByRole("button", { name: "Confirm order" });
    expect(confirm).toBeDisabled();

    // removing the flagged line unblocks confirmation
    const teaCard = screen.getByText("chai patti 250 wala 1 peti").closest("li")!;
    await user.click(within(teaCard).getByRole("button", { name: "Remove line" }));
    await waitFor(() => expect(screen.getByRole("button", { name: "Confirm order" })).toBeEnabled());

    await user.click(screen.getByRole("button", { name: "Confirm order" }));
    await waitFor(() => expect(calls.some((c) => c.url.endsWith("/orders") && c.body?.source === "ai")).toBe(true));
    const placed = calls.find((c) => c.url.endsWith("/orders") && c.body?.source === "ai")!.body;
    expect(placed.ai_parse_id).toBe(fixtures.parse.parse_id);
    expect(placed.items).toEqual([
      { sku: "SKU-BS-075", quantity_cases: 5, ai_line_id: "l1" },
      { sku: "SKU-DT-1KG", quantity_cases: 2, ai_line_id: "l2" },
    ]);
    expect(placed.total_paise).toBeUndefined();            // the client never sends prices or totals
  });
});
