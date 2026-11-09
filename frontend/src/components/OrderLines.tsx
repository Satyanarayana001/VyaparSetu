import { SchemeTag } from "./ui";
import { formatINR } from "../lib/format";
import { useI18n } from "../lib/i18n";
import type { Order } from "../types";

export function OrderLines({ order }: { order: Order }) {
  const { t } = useI18n();
  return (
    <>
      <ul className="divide-y divide-line">
        {order.items.map((i) => (
          <li key={i.id} className="flex flex-wrap items-start justify-between gap-2 py-3">
            <div className="min-w-0">
              <p className="font-semibold">{i.product_name}</p>
              <p className="text-sm text-muted">{i.sku} · {i.quantity_cases} {t("cases")} × {formatINR(i.case_price_paise)}</p>
              {i.free_cases > 0 && <p className="text-sm font-semibold text-ok">+ {i.free_cases} {t("cases")} {t("free")}</p>}
              {i.scheme_applied && <div className="mt-1"><SchemeTag>{i.scheme_applied}</SchemeTag></div>}
              {i.original_phrase && <p className="mt-1 text-sm text-muted">{t("youWrote")}: “{i.original_phrase}”{i.was_corrected ? ` · ${t("corrected")}` : ""}</p>}
            </div>
            <div className="text-right">
              {i.discount_paise > 0 && <p className="text-sm text-muted line-through">{formatINR(i.gross_paise)}</p>}
              <p className="font-bold">{formatINR(i.line_total_paise)}</p>
            </div>
          </li>))}
      </ul>
      <dl className="mt-2 space-y-1 border-t border-line pt-3">
        <div className="flex justify-between"><dt className="text-muted">{t("subtotal")}</dt><dd>{formatINR(order.subtotal_paise)}</dd></div>
        {order.discount_paise > 0 && <div className="flex justify-between"><dt className="text-muted">{t("discount")}</dt><dd className="text-ok">− {formatINR(order.discount_paise)}</dd></div>}
        <div className="flex justify-between text-xl font-bold"><dt>{t("total")}</dt><dd>{formatINR(order.total_paise)}</dd></div>
      </dl>
    </>
  );
}
