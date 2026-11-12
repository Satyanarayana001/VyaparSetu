import { Check, Info, Plus, Search, ShoppingCart } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ProductArt } from "../components/ProductArt";
import { EmptyState, ErrorState, SchemeTag, Skeleton, Stepper } from "../components/ui";
import { errorMessage } from "../lib/api";
import { useCart } from "../lib/cart";
import { formatINR } from "../lib/format";
import { useI18n } from "../lib/i18n";
import { useCatalogue, useQuote } from "../lib/queries";
import type { Product } from "../types";

function schemeText(p: Product, lang: string): string | null {
  const s = p.scheme;
  if (!s) return null;
  if (s.type === "free_goods") return lang === "hi" ? `${s.buy_qty} पेटी पर ${s.free_qty} फ्री` : `Buy ${s.buy_qty}, get ${s.free_qty} free`;
  return lang === "hi" ? `${s.min_cases}+ पेटी पर ${s.percent_bp / 100}% छूट` : `${s.percent_bp / 100}% off on ${s.min_cases}+ cases`;
}

function ProductCard({ p }: { p: Product }) {
  const { t, lang } = useI18n();
  const cart = useCart();
  const inCart = cart.qtyOf(p.sku);
  const [qty, setQty] = useState(inCart || 1);
  const [added, setAdded] = useState(false);
  const out = p.stock_status === "out_of_stock";
  const name = lang === "hi" && p.name_hi ? p.name_hi : p.name;
  const sub = lang === "hi" ? p.name : p.name_hi;
  const sch = schemeText(p, lang);
  return (
    <article className="tile overflow-hidden" aria-label={p.name}>
      <div className="relative">
        <div className={`bg-[#F1F4EF] ${out ? "grayscale" : ""}`}><ProductArt sku={p.sku} className="mx-auto aspect-[16/10] w-full max-w-md sm:aspect-[4/3]" /></div>
        {out && <span className="absolute left-3 top-3 chip border border-bad/20 bg-bad text-white shadow-sm">{t("outOfStock")}</span>}
        {sch && !out && <span className="absolute left-3 top-3"><SchemeTag>{sch}</SchemeTag></span>}
      </div>
      <div className="space-y-3 p-4 sm:p-5">
        <div>
          <h2 className="text-base font-bold leading-snug text-ink sm:text-lg">{name}</h2>
          <p className="text-sm text-muted">{sub ? `${sub} · ` : ""}{p.sku} · {p.packaging_label}</p>
        </div>
        <div className="flex items-end justify-between gap-3">
          <div>
            <p className="text-2xl font-bold leading-none tracking-tight text-ink sm:text-3xl">{formatINR(p.case_price_paise)}<span className="ml-1.5 text-base font-medium text-muted">{t("perCase")}</span></p>
            <p className="mt-1 text-sm text-muted">{formatINR(p.unit_price_paise)} × {p.case_size} {t("packs")}</p>
          </div>
          <p className={`chip shrink-0 ${out ? "bg-bad-soft text-bad" : "bg-ok-soft text-ok"}`}>{out ? t("outOfStock") : `${p.stock_cases} ${t("cases")}`}</p>
        </div>
        {out ? <p className="text-sm text-muted">{t("outOfStockHelp")}</p> : (
          <div className="flex items-center gap-2 pt-1">
            <Stepper value={qty} min={1} max={Math.max(1, p.stock_cases)} onChange={setQty} label={`${t("qty")} – ${p.name}`} />
            <button className="btn btn-primary flex-1 whitespace-nowrap !px-3" aria-label={`${inCart ? t("updateCart") : t("addToCart")} – ${p.name}`}
              onClick={() => { cart.setQty(p.sku, qty); setAdded(true); setTimeout(() => setAdded(false), 1500); }}>
              {added ? <Check className="h-5 w-5" aria-hidden /> : <Plus className="h-5 w-5" aria-hidden />}{inCart ? t("update") : t("add")}
            </button>
          </div>)}
        {inCart > 0 && <p className="text-sm font-semibold text-indigo" role="status">{t("inCart")}: {inCart} {inCart === 1 ? t("case1") : t("cases")}</p>}
      </div>
    </article>
  );
}

/** Always-visible cart shortcut. The total shown is the server's, never computed in the browser. */
function CartBar() {
  const { t } = useI18n();
  const cart = useCart();
  const quote = useQuote(cart.state.lines.map((l) => ({ sku: l.sku, quantity_cases: l.qty })));
  if (cart.count === 0) return null;
  return (
    <Link to="/cart" aria-label={t("viewCart")} className="fixed inset-x-3 bottom-[calc(68px+env(safe-area-inset-bottom))] z-20 mx-auto flex max-w-xl items-center gap-3 rounded-2xl border border-forest bg-forest px-4 py-3 text-white shadow-float">
      <ShoppingCart className="h-6 w-6 shrink-0" aria-hidden />
      <span className="font-semibold">{cart.count} {cart.count === 1 ? t("item1") : t("items")}</span>
      <span className="ml-auto text-lg font-bold">{quote.data ? formatINR(quote.data.total_paise) : "…"}</span>
      <span className="rounded-lg bg-white px-3 py-1.5 font-bold text-indigo">{t("viewCart")}</span>
    </Link>
  );
}

export default function Shop() {
  const { t } = useI18n();
  const [input, setInput] = useState("");
  const [q, setQ] = useState("");
  useEffect(() => { const id = setTimeout(() => setQ(input.trim()), 250); return () => clearTimeout(id); }, [input]);
  const cat = useCatalogue(q);
  const cart = useCart();
  return (
    <div className={`space-y-3 ${cart.count > 0 ? "pb-20" : ""}`}>
      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" aria-hidden />
        <input className="input !pl-12" type="search" aria-label={t("searchPlaceholder")} placeholder={t("searchPlaceholder")} value={input} onChange={(e) => setInput(e.target.value)} />
      </div>
      <p className="flex items-start gap-2 px-1 text-sm text-muted"><Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /><span>{t("pricesPerCase")}. {t("gstUnspecified")}</span></p>
      {cat.isPending ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-80" />)}</div> :
        cat.isError ? <ErrorState message={errorMessage(cat.error)} onRetry={() => cat.refetch()} /> :
        cat.data.products.length === 0 ? <EmptyState title={t("noProducts")} hint={t("noProductsSub")} /> :
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{cat.data.products.map((p) => <ProductCard key={p.sku} p={p} />)}</div>}
      <CartBar />
    </div>
  );
}
