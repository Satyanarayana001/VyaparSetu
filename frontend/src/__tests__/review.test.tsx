import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useState } from "react";
import { Stepper } from "../components/ui";
import { I18nProvider } from "../lib/i18n";
import { initLines, lineReady } from "../pages/Message";
import type { ParsedLine } from "../types";

const base: ParsedLine = {
  line_id: "l1", original_phrase: "5 peti biscuit chhota", sku: "SKU-BS-075", product_name: "Glucose biscuit 75 g", quantity: 5, raw_quantity: 5,
  unit: "case", packaging: "Case of 96", confidence: 0.95, match_source: "keyword", alternatives: [], validation_status: "ok",
  clarification: null, messages: [], stock_cases: 340, free_cases: 0, line_total_paise: 388800,
};
const none = new Map<string, number>();

describe("AI review gating (a human must resolve every flagged line)", () => {
  it("a clear match is ready", () => expect(lineReady(initLines([base])[0], none)).toBe(true));

  it("an ambiguous unit is not ready until the person enters cases", () => {
    const l = initLines([{ ...base, unit: "unknown", quantity: null, clarification: "unit", validation_status: "needs_clarification" }])[0];
    expect(lineReady(l, none)).toBe(false);
    expect(lineReady({ ...l, qty: 5 }, none)).toBe(true);
  });

  it("a low-confidence product is not ready until the person picks it", () => {
    const l = initLines([{ ...base, confidence: 0.6, clarification: "product", validation_status: "needs_clarification" }])[0];
    expect(l.productOk).toBe(false);
    expect(lineReady(l, none)).toBe(false);
    expect(lineReady({ ...l, productOk: true }, none)).toBe(true);
  });

  it("an out-of-stock line blocks until removed or changed", () => {
    const tea = { ...base, sku: "SKU-TE-250", validation_status: "out_of_stock" as const, quantity: 1 };
    const l = initLines([tea])[0];
    expect(lineReady(l, new Map([["SKU-TE-250", 1]]))).toBe(false);          // server says: out of stock
    expect(lineReady({ ...l, removed: true }, none)).toBe(false);            // removed lines aren't "ready"…
    expect([l].filter((x) => !x.removed).length).toBe(1);
    expect([{ ...l, removed: true }].filter((x) => !x.removed).every((x) => lineReady(x, none))).toBe(true); // …and don't block confirmation
  });

  it("an unmatched line has no product and is never ready", () => {
    const l = initLines([{ ...base, sku: null, product_name: null, quantity: 3, clarification: "product", validation_status: "needs_clarification", confidence: 0 }])[0];
    expect(lineReady(l, none)).toBe(false);
  });
});

describe("Stepper", () => {
  function Host() {
    const [v, setV] = useState(1);
    return <I18nProvider initial="en"><Stepper value={v} min={1} max={5} onChange={setV} label="Cases" /></I18nProvider>;
  }
  it("increments, decrements and respects bounds", async () => {
    const user = userEvent.setup();
    render(<Host />);
    const input = screen.getByRole("textbox", { name: "Cases" });
    expect(input).toHaveValue("1");
    await user.click(screen.getByRole("button", { name: "Increase quantity" }));
    expect(input).toHaveValue("2");
    expect(screen.getByRole("button", { name: "Decrease quantity" })).toBeEnabled();
    await user.click(screen.getByRole("button", { name: "Decrease quantity" }));
    expect(screen.getByRole("button", { name: "Decrease quantity" })).toBeDisabled();
    await user.clear(input); await user.type(input, "99");
    expect(input).toHaveValue("5");
  });
});
