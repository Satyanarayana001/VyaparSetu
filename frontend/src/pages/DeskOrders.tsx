import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Pencil, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Banner, EmptyState, ErrorState, Skeleton, StatusBadge } from "../components/ui";
import { errorMessage, get, patch, post } from "../lib/api";
import { confidenceLabel, formatDate, formatINR } from "../lib/format";
import { useI18n, type TKey } from "../lib/i18n";
import type { Catalogue, DeskOrder, OrderItem, OrderStatus, OrderSummary } from "../types";

type Filter = OrderStatus | "all";
const FILTERS: Filter[] = ["placed", "confirmed", "dispatched", "rejected", "all"];

function ItemEditor({ order, item, products }: { order: DeskOrder; item: OrderItem; products: Catalogue["products"] }) {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [sku, setSku] = useState(item.sku);
  const [qty, setQty] = useState(String(item.quantity_cases));
  const [saveAlias, setSaveAlias] = useState(true);
  const [open, setOpen] = useState(false);
  useEffect(() => { setSku(item.sku); setQty(String(item.quantity_cases)); }, [item.sku, item.quantity_cases]);
  const editable = order.status === "placed";
  const n = Number(qty);
  const changed = sku !== item.sku || n !== item.quantity_cases;
  const save = useMutation({
    mutationFn: () => patch<DeskOrder>(`/desk/orders/${order.id}/items/${item.id}`, { sku: sku !== item.sku ? sku : undefined, quantity_cases: n !== item.quantity_cases ? n : undefined, save_alias: saveAlias }),
    onSuccess: (o) => { setOpen(false); qc.setQueryData(["desk-order", String(order.id)], o); ["desk-orders", "catalogue"].forEach((k) => qc.invalidateQueries({ queryKey: [k] })); qc.invalidateQueries({ queryKey: ["aliases"] }); },
  });
  const conf = item.ai_confidence != null ? confidenceLabel(item.ai_confidence) : null;
  return (
    <li className="py-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0">
          {item.original_phrase && <p className="text-sm text-muted">{t("youWrote")}: <q className="font-semibold text-ink">{item.original_phrase}</q></p>}
          <p className="font-bold">{item.product_name} <span className="font-normal text-muted">· {item.sku}</span></p>
          <p className="text-sm text-muted">{item.packaging_label} · {formatINR(item.case_price_paise)} / {t("case1")}{item.free_cases > 0 ? ` · +${item.free_cases} ${t("free")}` : ""}{item.discount_paise > 0 ? ` · −${formatINR(item.discount_paise)}` : ""}</p>
          {conf && <p className="text-sm">{t("confidence")}: <b className={conf === "low" ? "text-bad" : conf === "medium" ? "text-warn" : "text-ok"}>{Math.round(item.ai_confidence! * 100)}%</b>
            {item.ai_alternatives?.length ? <span className="text-muted"> · {item.ai_alternatives.map((a) => a.sku).join(", ")}</span> : null}
            {item.was_corrected && <span className="chip ml-2 bg-indigo-soft text-indigo-dark">{t("corrected")}</span>}</p>}
        </div>
        <p className="text-lg font-bold">{formatINR(item.line_total_paise)}</p>
      </div>
      {editable && !open && <button className="btn btn-ghost mt-1 -ml-3" onClick={() => setOpen(true)}><Pencil className="h-4 w-4" aria-hidden />{t("correct")}</button>}
      {editable && open && (
        <div className="mt-3 grid gap-2 rounded-xl bg-paper p-3 sm:grid-cols-[1fr_110px_auto] sm:items-end">
          <label className="block text-sm font-medium">{t("product")}
            <select className="input mt-1" value={sku} onChange={(e) => setSku(e.target.value)}>{products.map((p) => <option key={p.sku} value={p.sku}>{p.name} ({p.sku})</option>)}</select></label>
          <label className="block text-sm font-medium">{t("casesLabel")}
            <input className="input mt-1" inputMode="numeric" value={qty} onChange={(e) => setQty(e.target.value.replace(/\D/g, "").slice(0, 5))} /></label>
          <button className="btn btn-primary" disabled={!changed || !n || save.isPending} onClick={() => save.mutate()}>{save.isPending ? t("saving") : t("save")}</button>
          {sku !== item.sku && item.original_phrase && (
            <label className="flex items-center gap-2 text-sm sm:col-span-3"><input type="checkbox" className="h-5 w-5" checked={saveAlias} onChange={(e) => setSaveAlias(e.target.checked)} />{t("saveAlias")}</label>)}
        </div>)}
      {save.isError && <div className="mt-2"><Banner tone="bad">{errorMessage(save.error)}</Banner></div>}
    </li>
  );
}

function Detail({ id }: { id: string }) {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const nav = useNavigate();
  const q = useQuery({ queryKey: ["desk-order", id], queryFn: () => get<DeskOrder>(`/desk/orders/${id}`) });
  const retailerId = q.data?.retailer.id;
  const cat = useQuery({ queryKey: ["catalogue", "desk", retailerId], queryFn: () => get<Catalogue>(`/retailers/${retailerId}/catalogue`), enabled: !!retailerId });
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState("");
  const status = useMutation({
    mutationFn: (v: { status: OrderStatus; reason?: string }) => post<DeskOrder>(`/desk/orders/${id}/status`, v),
    onSuccess: (o) => { qc.setQueryData(["desk-order", id], o); qc.invalidateQueries({ queryKey: ["desk-orders"] }); setRejecting(false); setReason(""); },
  });
  if (q.isPending) return <Skeleton className="h-96" />;
  if (q.isError) return <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} />;
  const o = q.data, c = o.retailer_detail.credit;
  return (
    <div className="tile space-y-4 p-5">
      <button className="btn btn-ghost -ml-3 lg:hidden" onClick={() => nav("/desk")}>← {t("back")}</button>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div><h2 className="text-2xl font-bold">{o.order_number}</h2><p className="text-sm text-muted">{t("created")} {formatDate(o.created_at, lang)} · {t(`placedVia_${o.source}` as TKey)}</p></div>
        <StatusBadge status={o.status} />
      </div>
      <section className="grid gap-3 rounded-xl bg-paper p-3 sm:grid-cols-2" aria-label={t("retailer")}>
        <div><p className="text-sm text-muted">{t("retailer")}</p><p className="font-bold">{o.retailer.name}</p><p className="text-sm text-muted">{o.retailer.code} · {o.retailer.city}</p></div>
        <dl className="grid grid-cols-3 gap-2 text-sm"><div><dt className="text-muted">{t("creditLimit")}</dt><dd className="font-semibold">{formatINR(c.credit_limit_paise)}</dd></div>
          <div><dt className="text-muted">{t("outstanding")}</dt><dd className="font-semibold">{formatINR(c.outstanding_paise)}</dd></div>
          <div><dt className="text-muted">{t("availableCredit")}</dt><dd className="font-semibold">{formatINR(c.available_paise)}</dd></div></dl>
      </section>
      {o.original_message && <section><p className="text-sm font-semibold text-muted">{t("original")}</p><p className="rounded-xl bg-paper p-3">{o.original_message}</p>
        {o.ai && <p className="mt-1 text-sm text-muted">{t("aiReading")}: {o.ai.mode === "llm" ? `${t("mode_llm")} (${o.ai.model})` : `${t("mode_fallback")}${o.ai.fallback_reason ? ` – ${o.ai.fallback_reason}` : ""}`}</p>}</section>}
      {o.status === "rejected" && <Banner tone="bad"><b>{t("reason")}:</b> {o.rejection_reason}</Banner>}
      <ul className="divide-y divide-line">{o.items.map((i) => <ItemEditor key={i.id} order={o} item={i} products={cat.data?.products ?? []} />)}</ul>
      <div className="max-w-sm ml-auto"><OrderLinesTotals order={o} /></div>
      {status.isError && <Banner tone="bad">{errorMessage(status.error)}</Banner>}
      <div className="flex flex-wrap gap-2 border-t border-line pt-4">
        {o.status === "placed" && <button className="btn btn-primary" disabled={status.isPending} onClick={() => status.mutate({ status: "confirmed" })}>{t("confirm")}</button>}
        {o.status === "confirmed" && <button className="btn btn-primary" disabled={status.isPending} onClick={() => status.mutate({ status: "dispatched" })}>{t("markDispatched")}</button>}
        {(o.status === "placed" || o.status === "confirmed") && !rejecting && <button className="btn btn-danger" onClick={() => setRejecting(true)}>{t("reject")}</button>}
      </div>
      {rejecting && (
        <div className="space-y-2 rounded-xl border border-bad/40 p-3">
          <label className="block text-sm font-medium" htmlFor="reason">{t("rejectReason")}</label>
          <input id="reason" className="input" value={reason} maxLength={300} onChange={(e) => setReason(e.target.value)} />
          <div className="flex gap-2"><button className="btn btn-danger" disabled={reason.trim().length < 3 || status.isPending} onClick={() => status.mutate({ status: "rejected", reason })}>{t("confirmReject")}</button>
            <button className="btn btn-secondary" onClick={() => setRejecting(false)}>{t("cancel")}</button></div>
        </div>)}
    </div>
  );
}

function OrderLinesTotals({ order }: { order: DeskOrder }) {
  const { t } = useI18n();
  return (
    <dl className="space-y-1">
      <div className="flex justify-between"><dt className="text-muted">{t("subtotal")}</dt><dd>{formatINR(order.subtotal_paise)}</dd></div>
      {order.discount_paise > 0 && <div className="flex justify-between"><dt className="text-muted">{t("discount")}</dt><dd className="text-ok">− {formatINR(order.discount_paise)}</dd></div>}
      <div className="flex justify-between text-xl font-bold"><dt>{t("total")}</dt><dd>{formatINR(order.total_paise)}</dd></div>
    </dl>
  );
}

export default function DeskOrders() {
  const { t, lang } = useI18n();
  const { id } = useParams();
  const [filter, setFilter] = useState<Filter>("placed");
  const [input, setInput] = useState("");
  const [search, setSearch] = useState("");
  useEffect(() => { const h = setTimeout(() => setSearch(input.trim()), 250); return () => clearTimeout(h); }, [input]);
  const list = useQuery({
    queryKey: ["desk-orders", filter, search],
    queryFn: () => get<{ orders: OrderSummary[]; counts: Record<OrderStatus, number> }>(`/desk/orders?${new URLSearchParams({ ...(filter !== "all" ? { status: filter } : {}), ...(search ? { q: search } : {}) })}`),
    refetchInterval: 15_000,
  });
  const total = list.data ? Object.values(list.data.counts).reduce((a, b) => a + b, 0) : 0;
  return (
    <div className="grid gap-4 lg:grid-cols-[380px_1fr]">
      <section className={`space-y-3 ${id ? "hidden lg:block" : ""}`} aria-label={t("deskOrders")}>
        <div className="relative"><Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" aria-hidden />
          <input className="input !pl-12" type="search" placeholder={t("search")} aria-label={t("search")} value={input} onChange={(e) => setInput(e.target.value)} /></div>
        <div className="flex flex-wrap gap-2" role="tablist" aria-label="Status">
          {FILTERS.map((f) => (
            <button key={f} role="tab" aria-selected={filter === f} onClick={() => setFilter(f)} className={`chip min-h-[40px] border ${filter === f ? "border-ink bg-ink text-white" : "border-line bg-white"}`}>
              {f === "all" ? t("all") : f === "placed" ? t("toReview") : t(`status_${f}` as TKey)} <b>{f === "all" ? total : list.data?.counts[f] ?? 0}</b></button>))}
        </div>
        {list.isPending ? <><Skeleton className="h-20" /><Skeleton className="h-20" /></> : list.isError ? <ErrorState message={errorMessage(list.error)} onRetry={() => list.refetch()} /> :
          list.data.orders.length === 0 ? <div className="tile"><EmptyState title={t("noDeskOrders")} hint={t("noDeskOrdersSub")} /></div> :
          <ul className="space-y-2">{list.data.orders.map((o) => (
            <li key={o.id}><Link to={`/desk/orders/${o.id}`} className={`tile flex min-h-[72px] items-center gap-3 p-3 ${String(o.id) === id ? "!border-indigo ring-2 ring-indigo/30" : ""}`}>
              <div className="min-w-0 flex-1"><p className="font-bold">{o.order_number}</p><p className="truncate text-sm text-muted">{o.retailer.name}</p><p className="text-xs text-muted">{formatDate(o.created_at, lang)} · {o.item_count} {t("items")}</p></div>
              <div className="text-right"><p className="font-bold">{formatINR(o.total_paise)}</p><StatusBadge status={o.status} /></div>
            </Link></li>))}</ul>}
      </section>
      <section className={id ? "" : "hidden lg:block"}>{id ? <Detail key={id} id={id} /> : <div className="tile"><EmptyState title={t("selectOrder")} /></div>}</section>
    </div>
  );
}
