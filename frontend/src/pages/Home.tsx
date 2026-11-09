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
      <div className="grid gap-4 md:grid-cols-6">
        <section className="tile p-5 md:col-span-3" aria-label={t("availableCredit")}>
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
        <Link to="/message" className="tile group flex flex-col justify-between border-2 border-ink bg-indigo p-5 text-white shadow-brut md:col-span-3">
          <MessageSquareText className="h-8 w-8" aria-hidden />
          <div><h2 className="mt-6 text-xl font-bold">{t("orderByMessage")}</h2><p className="mt-1 text-white/85">{t("orderByMessageSub")}</p></div>
        </Link>
        <button className="tile p-5 text-left md:col-span-3 disabled:opacity-60" disabled={!last.data || repeat.isPending} onClick={() => repeat.mutate()}>
          <Repeat2 className="h-7 w-7 text-indigo" aria-hidden />
          <h2 className="mt-4 text-lg font-bold">{t("repeatLast")}</h2>
          <p className="mt-1 text-muted">{last.isPending ? "…" : last.data ? `${last.data.order_number} · ${formatDate(last.data.created_at, lang)}` : t("noPrevious")}</p>
          {last.data && <p className="mt-1 text-sm text-muted">{t("repeatLastSub")}</p>}
        </button>
        <Link to="/shop" className="tile p-5 md:col-span-3">
          <Store className="h-7 w-7 text-indigo" aria-hidden />
          <h2 className="mt-4 text-lg font-bold">{t("browse")}</h2><p className="mt-1 text-muted">{t("browseSub")}</p>
        </Link>
        <section className="tile p-5 md:col-span-6" aria-label={t("recentOrders")}>
          <div className="mb-2 flex items-center justify-between"><h2 className="text-lg font-bold">{t("recentOrders")}</h2><Link to="/orders" className="btn btn-ghost">{t("viewAll")} <ArrowRight className="h-4 w-4" /></Link></div>
          {orders.isPending ? <Skeleton className="h-16" /> : orders.isError ? <ErrorState message={errorMessage(orders.error)} onRetry={() => orders.refetch()} /> :
            orders.data.length === 0 ? <EmptyState title={t("noOrders")} hint={t("noOrdersSub")} /> :
            <ul className="divide-y divide-line">{orders.data.slice(0, 3).map((o) => (
              <li key={o.id}><Link to={`/orders/${o.id}`} className="flex min-h-[56px] items-center gap-3 py-2">
                <div className="min-w-0 flex-1"><p className="font-semibold">{o.order_number}</p><p className="text-sm text-muted">{formatDate(o.created_at, lang)}</p></div>
                <StatusBadge status={o.status} /><span className="w-28 text-right font-semibold">{formatINR(o.total_paise)}</span>
              </Link></li>))}</ul>}
        </section>
      </div>
    </div>
  );
}
