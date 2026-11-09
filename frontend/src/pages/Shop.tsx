import { Check, Search, ShoppingCart } from "lucide-react";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ProductArt } from "../components/ProductArt";
import { Banner, EmptyState, ErrorState, SchemeTag, Skeleton, Stepper } from "../components/ui";
import { errorMessage } from "../lib/api";
import { useCart } from "../lib/cart";
import { formatINR } from "../lib/format";
import { useI18n } from "../lib/i18n";
import { useCatalogue } from "../lib/queries";
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
    <article className={`tile overflow-hidden ${out ? "opacity-95" : ""}`} aria-label={p.name}>
      <div className="relative"><ProductArt sku={p.sku} className={`aspect-[4/3] w-full ${out ? "grayscale" : ""}`} />
        {out && <span className="absolute left-3 top-3 chip border-2 border-ink bg-bad text-white shadow-brut-sm">{t("outOfStock")}</span>}
        {sch && !out && <span className="absolute left-3 top-3"><SchemeTag>{sch}</SchemeTag></span>}
      </div>
      <div className="space-y-3 p-4">
        <div><h2 className="text-lg font-bold leading-snug">{name}</h2>{sub && <p className="text-sm text-muted">{sub}</p>}
          <p className="mt-0.5 text-sm text-muted">{p.sku} · {p.packaging_label}</p></div>
        <div><p className="text-3xl font-bold tracking-tight">{formatINR(p.case_price_paise)} <span className="text-base font-medium text-muted">{t("caseOf")}</span></p>
          <p className="text-sm text-muted">{formatINR(p.unit_price_paise)} × {p.case_size} {lang === "hi" ? "पैक" : "packs"}</p></div>
        <p className={`text-sm font-semibold ${out ? "text-bad" : "text-ok"}`}>{out ? t("outOfStockHelp") : `${p.stock_cases} ${t("cases")} ${t("inStock")}`}</p>
        {out ? <button className="btn btn-secondary w-full" disabled>{t("outOfStock")}</button> : (
          <div className="flex items-center gap-3">
            <Stepper value={qty} min={1} max={Math.max(1, p.stock_cases)} onChange={setQty} label={`${t("qty")} – ${p.name}`} />
            <button className="btn btn-primary flex-1" onClick={() => { cart.setQty(p.sku, qty); setAdded(true); setTimeout(() => setAdded(false), 1800); }}>
              {added ? <Check className="h-5 w-5" aria-hidden /> : <ShoppingCart className="h-5 w-5" aria-hidden />}{inCart ? t("updateCart") : t("addToCart")}
            </button>
          </div>)}
        {inCart > 0 && <p className="text-sm font-medium text-indigo" role="status">{t("inCart")}: {inCart} {t("cases")}</p>}
      </div>
    </article>
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
    <div className="space-y-4">
      <div className="relative">
        <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" aria-hidden />
        <input className="input !pl-12" type="search" aria-label={t("searchPlaceholder")} placeholder={t("searchPlaceholder")} value={input} onChange={(e) => setInput(e.target.value)} />
      </div>
      {cat.data && <Banner tone="info"><p>{t("priceNote")}</p><p>{cat.data.gst_note}</p></Banner>}
      {cat.isPending ? <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-96" />)}</div> :
        cat.isError ? <ErrorState message={errorMessage(cat.error)} onRetry={() => cat.refetch()} /> :
        cat.data.products.length === 0 ? <EmptyState title={t("noProducts")} hint={t("noProductsSub")} /> :
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{cat.data.products.map((p) => <ProductCard key={p.sku} p={p} />)}</div>}
      {cart.count > 0 && <Link to="/cart" className="btn btn-primary fixed bottom-24 right-4 z-20 shadow-brut"><ShoppingCart className="h-5 w-5" />{t("navCart")} ({cart.count})</Link>}
    </div>
  );
}
