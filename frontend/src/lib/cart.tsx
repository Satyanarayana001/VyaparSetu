import { createContext, useContext, useEffect, useMemo, useReducer, type ReactNode } from "react";

export interface CartLine { sku: string; qty: number }
export interface RepeatRef { id: number; number: string }
export interface CartState { lines: CartLine[]; source: "manual" | "repeat"; repeatOf: RepeatRef | null }
type Action =
  | { type: "set"; sku: string; qty: number }
  | { type: "remove"; sku: string }
  | { type: "load"; lines: CartLine[]; repeatOf: RepeatRef }
  | { type: "clear" };

export const MAX_QTY = 10000;
export const emptyCart: CartState = { lines: [], source: "manual", repeatOf: null };

export function cartReducer(state: CartState, a: Action): CartState {
  switch (a.type) {
    case "set": {
      const qty = Math.max(0, Math.min(MAX_QTY, Math.floor(a.qty) || 0));
      if (qty === 0) return { ...state, lines: state.lines.filter((l) => l.sku !== a.sku) };
      const exists = state.lines.some((l) => l.sku === a.sku);
      return { ...state, lines: exists ? state.lines.map((l) => (l.sku === a.sku ? { ...l, qty } : l)) : [...state.lines, { sku: a.sku, qty }] };
    }
    case "remove": return { ...state, lines: state.lines.filter((l) => l.sku !== a.sku) };
    case "load": return { lines: a.lines.filter((l) => l.qty > 0), source: "repeat", repeatOf: a.repeatOf };
    case "clear": return emptyCart;
  }
}

interface CartCtx {
  state: CartState; count: number; qtyOf: (sku: string) => number;
  setQty: (sku: string, qty: number) => void; remove: (sku: string) => void;
  loadRepeat: (lines: CartLine[], repeatOf: RepeatRef) => void; clear: () => void;
}
const Ctx = createContext<CartCtx | null>(null);

function init(): CartState {
  try { const s = sessionStorage.getItem("cart"); if (s) return { ...emptyCart, ...JSON.parse(s) }; } catch { /* ignore */ }
  return emptyCart;
}

export function CartProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(cartReducer, undefined, init);
  useEffect(() => { try { sessionStorage.setItem("cart", JSON.stringify(state)); } catch { /* ignore */ } }, [state]);
  useEffect(() => {
    const clear = () => dispatch({ type: "clear" });
    window.addEventListener("app:logout", clear);
    return () => window.removeEventListener("app:logout", clear);
  }, []);
  const value = useMemo<CartCtx>(() => ({
    state, count: state.lines.length, qtyOf: (sku) => state.lines.find((l) => l.sku === sku)?.qty ?? 0,
    setQty: (sku, qty) => dispatch({ type: "set", sku, qty }), remove: (sku) => dispatch({ type: "remove", sku }),
    loadRepeat: (lines, repeatOf) => dispatch({ type: "load", lines, repeatOf }), clear: () => dispatch({ type: "clear" }),
  }), [state]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useCart(): CartCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useCart must be used inside CartProvider");
  return c;
}
