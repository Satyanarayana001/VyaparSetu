import { useQuery } from "@tanstack/react-query";
import { Link, useLocation, useParams } from "react-router-dom";
import { OrderLines } from "../components/OrderLines";
import { Banner, ErrorState, Skeleton, StatusBadge } from "../components/ui";
import { errorMessage, get } from "../lib/api";
import { formatDate } from "../lib/format";
import { useI18n, type TKey } from "../lib/i18n";
import type { Order } from "../types";

export default function OrderDetail() {
  const { id } = useParams();
  const { t, lang } = useI18n();
  const placed = (useLocation().state as { placed?: boolean } | null)?.placed;
  const q = useQuery({ queryKey: ["order", id], queryFn: () => get<Order>(`/orders/${id}`) });
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <Link to="/orders" className="btn btn-ghost -ml-3">← {t("back")}</Link>
      {placed && <Banner tone="ok"><b>{t("orderPlaced")}.</b> {t("orderPlacedSub")}</Banner>}
      {q.isPending ? <Skeleton className="h-64" /> : q.isError ? <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} /> : (
        <div className="tile space-y-3 p-5">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div><h1 className="text-2xl font-bold">{q.data.order_number}</h1><p className="text-sm text-muted">{formatDate(q.data.created_at, lang)} · {t(`placedVia_${q.data.source}` as TKey)}</p></div>
            <StatusBadge status={q.data.status} />
          </div>
          {q.data.status === "rejected" && <Banner tone="bad"><b>{t("reason")}:</b> {q.data.rejection_reason}</Banner>}
          {q.data.original_message && <div><p className="text-sm font-semibold text-muted">{t("yourMessage")}</p><p className="rounded-xl bg-paper p-3">{q.data.original_message}</p></div>}
          <OrderLines order={q.data} />
        </div>)}
    </div>
  );
}
