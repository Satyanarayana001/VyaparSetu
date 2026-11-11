import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";
import { Banner, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { downloadPost, errorMessage, get } from "../lib/api";
import { formatDate, formatINR } from "../lib/format";
import { useI18n } from "../lib/i18n";
import type { OrderStatus, OrderSummary } from "../types";

const COLUMNS = ["Order ID", "Order Date", "Retailer Code", "Retailer", "SKU", "Product Name", "Quantity (Cases)", "Free Quantity (Cases)", "Packs per Case", "Unit Price per Pack (INR)", "Price per Case (INR)", "Discount (INR)", "Total (INR)", "Order Status"];

export default function DeskExport() {
  const { t, lang } = useI18n();
  const qc = useQueryClient();
  const [includeExported, setIncludeExported] = useState(false);
  const [picked, setPicked] = useState<Set<number> | null>(null);   // null = untouched: every exportable order is pre-selected
  const q = useQuery({ queryKey: ["desk-orders", "confirmed", ""], queryFn: () => get<{ orders: OrderSummary[]; counts: Record<OrderStatus, number> }>("/desk/orders?status=confirmed&limit=200") });
  const rows = (q.data?.orders ?? []).filter((o) => includeExported || !o.exported_at);
  const effective = rows.filter((o) => (picked ? picked.has(o.id) : !o.exported_at));
  const allOn = rows.length > 0 && effective.length === rows.length;
  const exp = useMutation({
    mutationFn: () => downloadPost("/desk/export/tally", { order_ids: effective.map((o) => o.id) }, "tally-orders.csv"),
    onSuccess: () => { setPicked(null); qc.invalidateQueries({ queryKey: ["desk-orders"] }); },
  });
  const sum = effective.reduce((a, o) => a + o.total_paise, 0);
  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <div><h1 className="text-2xl font-bold">{t("exportTitle")}</h1><p className="mt-1 text-muted">{t("exportSub")}</p></div>
      {exp.isSuccess && <Banner tone="ok">{t("downloaded", { n: exp.data })}</Banner>}
      {exp.isError && <Banner tone="bad">{errorMessage(exp.error)}</Banner>}
      <div className="tile p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <label className="flex min-h-[44px] items-center gap-2"><input type="checkbox" className="h-5 w-5" checked={includeExported} onChange={(e) => setIncludeExported(e.target.checked)} />{t("includeExported")}</label>
          <label className="flex min-h-[44px] items-center gap-2 font-medium"><input type="checkbox" className="h-5 w-5" checked={allOn} disabled={!rows.length} onChange={(e) => setPicked(e.target.checked ? new Set(rows.map((o) => o.id)) : new Set())} />{t("selectAll")}</label>
        </div>
        {q.isPending ? <Skeleton className="h-32" /> : q.isError ? <ErrorState message={errorMessage(q.error)} onRetry={() => q.refetch()} /> :
          rows.length === 0 ? <EmptyState title={t("noExportable")} hint={t("noExportableSub")} /> :
          <ul className="divide-y divide-line">{rows.map((o) => (
            <li key={o.id}><label className="flex min-h-[56px] cursor-pointer items-center gap-3 py-2">
              <input type="checkbox" className="h-5 w-5" checked={effective.some((x) => x.id === o.id)} onChange={(e) => { const n = new Set(effective.map((x) => x.id)); if (e.target.checked) n.add(o.id); else n.delete(o.id); setPicked(n); }} aria-label={o.order_number} />
              <div className="min-w-0 flex-1"><p className="font-semibold">{o.order_number} · {o.retailer.name}</p><p className="text-sm text-muted">{formatDate(o.created_at, lang)} · {o.item_count} {t("items")}</p></div>
              {o.exported_at && <span className="chip bg-paper text-muted">{t("exported")}</span>}
              <span className="font-bold">{formatINR(o.total_paise)}</span></label></li>))}</ul>}
        <div className="mt-3 flex items-center justify-between border-t border-line pt-3">
          <p className="font-semibold">{effective.length} · {formatINR(sum)}</p>
          <button className="btn btn-primary" disabled={!effective.length || exp.isPending} onClick={() => exp.mutate()}><Download className="h-5 w-5" />{t("downloadCsv")}</button>
        </div>
      </div>
      <details className="tile p-4"><summary className="min-h-[44px] cursor-pointer font-semibold">{t("columns")}</summary><p className="mt-2 text-sm text-muted">{COLUMNS.join(" · ")}</p></details>
    </div>
  );
}
