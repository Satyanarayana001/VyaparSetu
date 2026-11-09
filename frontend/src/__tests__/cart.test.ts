import { cartReducer, emptyCart, MAX_QTY } from "../lib/cart";

describe("cartReducer", () => {
  it("adds, updates and removes lines", () => {
    let s = cartReducer(emptyCart, { type: "set", sku: "A", qty: 2 });
    s = cartReducer(s, { type: "set", sku: "B", qty: 1 });
    s = cartReducer(s, { type: "set", sku: "A", qty: 5 });
    expect(s.lines).toEqual([{ sku: "A", qty: 5 }, { sku: "B", qty: 1 }]);
    s = cartReducer(s, { type: "set", sku: "A", qty: 0 });
    expect(s.lines).toEqual([{ sku: "B", qty: 1 }]);
    expect(cartReducer(s, { type: "remove", sku: "B" }).lines).toEqual([]);
  });
  it("never accepts negative, fractional or absurd quantities", () => {
    expect(cartReducer(emptyCart, { type: "set", sku: "A", qty: -3 }).lines).toEqual([]);
    expect(cartReducer(emptyCart, { type: "set", sku: "A", qty: 2.9 }).lines).toEqual([{ sku: "A", qty: 2 }]);
    expect(cartReducer(emptyCart, { type: "set", sku: "A", qty: 10 ** 9 }).lines[0].qty).toBe(MAX_QTY);
    expect(cartReducer(emptyCart, { type: "set", sku: "A", qty: NaN }).lines).toEqual([]);
  });
  it("repeat-order load marks the cart as a repeat and drops empty lines", () => {
    const s = cartReducer(emptyCart, { type: "load", lines: [{ sku: "A", qty: 3 }, { sku: "B", qty: 0 }], repeatOf: { id: 7, number: "ORD-000007" } });
    expect(s).toEqual({ lines: [{ sku: "A", qty: 3 }], source: "repeat", repeatOf: { id: 7, number: "ORD-000007" } });
    expect(cartReducer(s, { type: "clear" })).toEqual(emptyCart);
  });
});
