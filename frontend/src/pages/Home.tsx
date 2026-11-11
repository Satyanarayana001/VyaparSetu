import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, MessageSquareText, Repeat2, Store } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { EmptyState, ErrorState, Skeleton, StatusBadge } from "../components/ui";
import { ApiError, errorMessage, get } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useCart } from "../lib/cart";
import { formatDate, formatINR } from "../lib/format";
import { useI18n } from "../lib/i18n";
import { useProfile } from "../lib/queries";
import type { OrderSummary, Repeat } from "../types";

export default function Home() {
  const { t, lang } = useI18n();
  const { user } = useAuth();
  const nav = useNavigate();
  const cart = useCart();
  const qc = useQueryClient();
  const profile = useProfile();
  const orders = useQuery({ queryKey: ["orders"], queryFn: () => get<OrderSummary[]>("/orders") });
  const last = useQuery({
    queryKey: ["last-repeatable"], queryFn: () => get<Repeat>("/orders/last-repeatable"),
    retry: (n, e) => !(e instanceof ApiError && e.status === 404) && n < 1,
  });
  const repeat = useMutation({
    mutationFn: async () => last.data!,
    onSuccess: (r) => { cart.loadRepeat(r.items.map((i) => ({ sku: i.sku, qty: i.quantity_cases })), { id: r.order_id, number: r.order_number }); qc.invalidateQueries({ queryKey: ["quote"] }); nav("/cart"); },
  });
  const credit = profile.data?.credit;
  const usedPct = credit && credit.credit_limit_paise ? Math.min(100, Math.round(((credit.credit_limit_paise - credit.available_paise) / credit.credit_limit_paise) * 100)) : 0;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold">{t("hello")}, {user?.name.replace(" (demo)", "")}</h1>
      <div className="grid grid-cols-2 gap-3 md:grid-cols-6 md:gap-4">
        <section className="tile col-span-2 p-5 md:col-span-3" aria-label={t("availableCredit")}>
          <div className="flex items-center justify-between"><h2 className="font-semibold text-muted">{t("availableCredit")}</h2><span className="chip bg-paper text-muted">{t("demoData")}</span></div>
          {profile.isPending ? <Skeleton className="mt-3 h-12" /> : profile.isError ? <ErrorState message={errorMessage(profile.error)} onRetry={() => profile.refetch()} /> : credit && (<>
            <p className="mt-2 text-4xl font-bold tracking-tight">{formatINR(credit.available_paise)}</p>
            <div className="mt-4 h-2.5 overflow-hidden rounded-full bg-line" role="progressbar" aria-valuenow={usedPct} aria-valuemin={0} aria-valuemax={100} aria-label={t("creditLimit")}><div className="h-full rounded-full bg-indigo" style={{ width: `${usedPct}%` }} /></div>
            <dl className="mt-3 grid grid-cols-3 gap-2 text-sm">
              <div><dt className="text-muted">{t("creditLimit")}</dt><dd className="font-semibold">{formatINR(credit.credit_limit_paise)}</dd></div>
              <div><dt className="text-muted">{t("outstanding")}</dt><dd className="font-semibold">{formatINR(credit.outstanding_paise)}</dd></div>
              <div><dt className="text-muted">{t("openOrders")}</dt><dd className="font-semibold">{formatINR(credit.open_orders_paise)}</dd></div>
            </dl></>)}
        </section>
        <Link to="/message" className="tile flex min-h-[150px] flex-col justify-between border-2 border-ink !bg-indigo p-4 text-white shadow-brut md:col-span-3 md:p-5">
          <MessageSquareText className="h-7 w-7" aria-hidden />
          <div><h2 className="text-lg font-bold leading-tight">{t("orderByMessage")}</h2><p className="mt-1 hidden text-white/85 md:block">{t("orderByMessageSub")}</p></div>
        </Link>
        <Link to="/shop" className="tile flex min-h-[150px] flex-col justify-between p-4 md:col-span-3 md:p-5">
          <Store className="h-7 w-7 text-indigo" aria-hidden />
          <div><h2 className="text-lg font-bold leading-tight">{t("browse")}</h2><p className="mt-1 hidden text-muted md:block">{t("browseSub")}</p></div>
        </Link>
        <button className="tile col-span-2 flex items-center gap-4 p-4 text-left md:col-span-6 md:p-5 disabled:opacity-60" disabled={!last.data || repeat.isPending} onClick={() => repeat.mutate()}>
          <Repeat2 className="h-7 w-7 shrink-0 text-indigo" aria-hidden />
          <div className="min-w-0"><h2 className="text-lg font-bold leading-tight">{t("repeatLast")}</h2>
            <p className="mt-0.5 text-muted">{last.isPending ? "…" : last.data ? `${last.data.order_number} · ${formatDate(last.data.created_at, lang)}` : t("noPrevious")}</p></div>
          {last.data && <ArrowRight className="ml-auto h-5 w-5 shrink-0 text-muted" aria-hidden />}
        </button>
        <section className="tile col-span-2 p-5 md:col-span-6" aria-label={t("recentOrders")}>
          <div className="mb-2 flex items-center justify-between"><h2 className="text-lg font-bold">{t("recentOrders")}</h2><Link to="/orders" className="btn btn-ghost">{t("viewAll")} <ArrowRight className="h-4 w-4" /></Link></div>
          {orders.isPending ? <Skeleton className="h-16" /> : orders.isError ? <ErrorState message={errorMessage(orders.error)} onRetry={() => orders.refetch()} /> :
            orders.data.length === 0 ? <EmptyState title={t("noOrders")} hint={t("noOrdersSub")} /> :
            <ul className="divide-y divide-line">{orders.data.slice(0, 3).map((o) => (
              <li key={o.id}><Link to={`/orders/${o.id}`} className="flex min-h-[56px] items-center gap-3 py-2">
                <div className="min-w-0 flex-1"><p className="whitespace-nowrap font-semibold">{o.order_number}</p><p className="text-sm text-muted">{formatDate(o.created_at, lang)}</p></div>
                <div className="flex flex-col items-end gap-1"><span className="font-semibold">{formatINR(o.total_paise)}</span><StatusBadge status={o.status} /></div>
              </Link></li>))}</ul>}
        </section>
      </div>
    </div>
  );
}
