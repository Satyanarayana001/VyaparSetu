import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { EmptyState, ErrorState, Skeleton, StatusBadge } from "../components/ui";
import { errorMessage, get } from "../lib/api";
import { formatDate, formatINR } from "../lib/format";
import { useI18n, type TKey } from "../lib/i18n";
import type { OrderSummary } from "../types";

export default function Orders() {
  const { t, lang } = useI18n();
  const q = useQuery({ queryKey: ["orders"], queryFn: () => get<OrderSummary[]>("/orders") });
  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <h1 className="text-2xl font-bold">{t("orderHistory")}</h1>
      {q.isPending ? <><Skeleton className="h-20" /><Skeleton className="h-20" /></> : q.isError ? <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} /> :
        q.data.length === 0 ? <div className="tile"><EmptyState title={t("noOrders")} hint={t("noOrdersSub")} action={<Link to="/shop" className="btn btn-primary">{t("startShopping")}</Link>} /></div> :
        <ul className="space-y-3">{q.data.map((o) => (
          <li key={o.id}><Link to={`/orders/${o.id}`} className="tile flex min-h-[72px] items-center gap-3 p-4">
            <div className="min-w-0 flex-1"><p className="font-bold">{o.order_number}</p>
              <p className="text-sm text-muted">{formatDate(o.created_at, lang)} · {o.item_count} {o.item_count === 1 ? t("item1") : t("items")} · {t(`placedVia_${o.source}` as TKey)}</p></div>
            <div className="text-right"><p className="font-bold">{formatINR(o.total_paise)}</p><StatusBadge status={o.status} /></div>
          </Link></li>))}</ul>}
    </div>
  );
}
