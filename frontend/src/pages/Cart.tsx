import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useRef } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Banner, EmptyState, ErrorState, SchemeTag, Skeleton, Stepper } from "../components/ui";
import { ApiError, errorMessage, post } from "../lib/api";
import { useCart } from "../lib/cart";
import { formatINR, newIdempotencyKey } from "../lib/format";
import { useI18n } from "../lib/i18n";
import { useQuote } from "../lib/queries";
import type { OrderCreated } from "../types";

export default function Cart() {
  const { t } = useI18n();
  const cart = useCart();
  const nav = useNavigate();
  const qc = useQueryClient();
  const items = cart.state.lines.map((l) => ({ sku: l.sku, quantity_cases: l.qty }));
  const quote = useQuote(items);

  // One idempotency key per distinct cart content: double taps and retries can never create two orders.
  const sig = JSON.stringify(items) + cart.state.source;
  const keyRef = useRef<{ sig: string; key: string }>({ sig: "", key: "" });
  if (keyRef.current.sig !== sig) keyRef.current = { sig, key: newIdempotencyKey() };

  const place = useMutation({
    mutationFn: () => post<OrderCreated>("/orders", {
      items, source: cart.state.source, repeat_of_order_id: cart.state.repeatOf?.id ?? null, idempotency_key: keyRef.current.key }),
    onSuccess: (res) => {
      cart.clear();
      qc.invalidateQueries({ queryKey: ["orders"] }); qc.invalidateQueries({ queryKey: ["profile"] });
      qc.invalidateQueries({ queryKey: ["catalogue"] }); qc.invalidateQueries({ queryKey: ["last-repeatable"] });
      nav(`/orders/${res.order.id}`, { state: { placed: true } });
    },
    onError: () => qc.invalidateQueries({ queryKey: ["quote"] }),
  });

  if (items.length === 0) return <div className="tile"><EmptyState title={t("cartEmpty")} hint={t("cartEmptySub")} action={<div className="flex gap-2"><Link to="/shop" className="btn btn-primary">{t("startShopping")}</Link><Link to="/message" className="btn btn-secondary">{t("orderByMessage")}</Link></div>} /></div>;

  const q = quote.data;
  const bySku = new Map(q?.lines.map((l) => [l.sku, l]));
  const blocked = !q || !q.can_order || !q.credit_ok || quote.isFetching;
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between"><div><p className="section-kicker">Your order</p><h1 className="page-title mt-1">{t("cartTitle")}</h1></div><button className="btn btn-ghost" onClick={cart.clear}>{t("clearCart")}</button></div>
      {cart.state.repeatOf && <Banner tone="info">{t("loadedFrom")} {cart.state.repeatOf.number}. {t("reviewQty")}</Banner>}
      {quote.isError && <ErrorState message={errorMessage(quote.error)} onRetry={() => quote.refetch()} />}
      <div className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <ul className="space-y-3">
          {cart.state.lines.map((l) => {
            const ql = bySku.get(l.sku);
            const bad = !!ql?.issues.length;
            return (
              <li key={l.sku} className={`tile p-4 ${bad ? "!border-bad" : ""}`}>
                <div className="flex items-start gap-3">
                  <div className="min-w-0 flex-1">
                    <p className="font-bold">{ql?.product_name ?? l.sku}</p><p className="text-sm text-muted">{l.sku}{ql?.case_price_paise != null ? ` · ${l.qty} × ${formatINR(ql.case_price_paise)}` : ""}</p>
                    {ql?.scheme_applied && <div className="mt-2"><SchemeTag>{ql.scheme_applied}</SchemeTag></div>}
                    {ql?.issues.map((i) => <p key={i.code} role="alert" className="mt-2 text-sm font-semibold text-bad">{i.message}</p>)}
                  </div>
                  <button className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-bad-soft hover:text-bad" aria-label={`${t("remove")} ${ql?.product_name ?? l.sku}`} onClick={() => cart.remove(l.sku)}><Trash2 className="h-5 w-5" /></button>
                </div>
                <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
                  <Stepper value={l.qty} min={1} onChange={(n) => cart.setQty(l.sku, n)} label={`${t("qty")} – ${ql?.product_name ?? l.sku}`} />
                  {ql?.line_total_paise != null ? <div className="text-right">
                    {!!ql.discount_paise && <p className="text-sm text-muted line-through">{formatINR(ql.gross_paise ?? 0)}</p>}
                    <p className="text-xl font-bold">{formatINR(ql.line_total_paise)}</p>
                    {ql.free_cases > 0 && <p className="text-sm font-semibold text-ok">+ {ql.free_cases} {t("cases")} {t("free")}</p>}
                  </div> : quote.isFetching ? <Skeleton className="h-10 w-24" /> : null}
                </div>
              </li>);
          })}
        </ul>
        <aside className="tile h-fit space-y-3 p-5 lg:sticky lg:top-20" aria-label={t("total")}>
          {!q ? <Skeleton className="h-28" /> : (<>
            <dl className="space-y-2">
              <div className="flex justify-between"><dt className="text-muted">{t("subtotal")}</dt><dd className="font-semibold">{formatINR(q.subtotal_paise)}</dd></div>
              {q.discount_paise > 0 && <div className="flex justify-between"><dt className="text-muted">{t("discount")}</dt><dd className="font-semibold text-ok">− {formatINR(q.discount_paise)}</dd></div>}
              {q.free_cases > 0 && <div className="flex justify-between"><dt className="text-muted">{t("freeCases")}</dt><dd className="font-semibold text-ok">{q.free_cases}</dd></div>}
              <div className="flex justify-between border-t border-line pt-2 text-xl"><dt className="font-bold">{t("total")}</dt><dd className="font-bold">{formatINR(q.total_paise)}</dd></div>
            </dl>
            <p className="text-sm text-muted">{t("gstUnspecified")}</p>
            <p className="text-sm text-muted">{t("availableCredit")}: <b>{formatINR(q.credit.available_paise)}</b> ({t("demoData")})</p>
            {!q.credit_ok && <Banner tone="bad">{t("overCredit")}</Banner>}
            {!q.can_order && <Banner tone="warn">{t("fixCart")}</Banner>}
          </>)}
          {place.isError && <Banner tone="bad">{errorMessage(place.error)}{place.error instanceof ApiError && Array.isArray(place.error.details) && place.error.details.length > 0 && <ul className="mt-1 list-disc pl-4">{(place.error.details as { message: string }[]).map((d, i) => <li key={i}>{d.message}</li>)}</ul>}</Banner>}
          <button className="btn btn-primary w-full" disabled={blocked || place.isPending} onClick={() => place.mutate()}>{place.isPending ? t("placing") : t("placeOrder")}</button>
        </aside>
      </div>
    </div>
  );
}
