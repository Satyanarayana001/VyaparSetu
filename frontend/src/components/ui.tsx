import { AlertCircle, CheckCircle2, Inbox, Loader2, Minus, Plus, X } from "lucide-react";
import type { ReactNode } from "react";
import { useI18n, type TKey } from "../lib/i18n";
import type { LineStatus, OrderStatus } from "../types";

export function Spinner({ label }: { label?: string }) {
  const { t } = useI18n();
  return (
    <div role="status" className="flex items-center justify-center gap-2 py-10 text-muted">
      <Loader2 className="h-5 w-5 animate-spin" aria-hidden /> <span>{label ?? t("loading")}</span>
    </div>
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return <div aria-hidden className={`animate-pulse rounded-xl bg-line/70 ${className}`} />;
}

export function EmptyState({ title, hint, action }: { title: string; hint?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center text-center gap-2 py-12 px-6">
      <Inbox className="h-10 w-10 text-muted/60" aria-hidden />
      <p className="text-lg font-semibold">{title}</p>
      {hint && <p className="text-muted max-w-sm">{hint}</p>}
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useI18n();
  return (
    <div role="alert" className="flex flex-col items-center text-center gap-2 py-10 px-6">
      <AlertCircle className="h-9 w-9 text-bad" aria-hidden />
      <p className="font-semibold">{t("errorTitle")}</p>
      <p className="text-muted max-w-sm">{message}</p>
      {onRetry && <button className="btn btn-secondary mt-2" onClick={onRetry}>{t("retry")}</button>}
    </div>
  );
}

export function Banner({ tone, children, onDismiss }: { tone: "ok" | "warn" | "bad" | "info"; children: ReactNode; onDismiss?: () => void }) {
  const { t } = useI18n();
  const cls = { ok: "bg-ok-soft text-ok", warn: "bg-warn-soft text-warn", bad: "bg-bad-soft text-bad", info: "bg-indigo-soft text-indigo-dark" }[tone];
  const Icon = tone === "ok" ? CheckCircle2 : AlertCircle;
  return (
    <div role={tone === "bad" ? "alert" : "status"} className={`flex items-start gap-3 rounded-xl px-4 py-3 ${cls}`}>
      <Icon className="h-5 w-5 mt-0.5 shrink-0" aria-hidden />
      <div className="flex-1 text-[15px] leading-snug">{children}</div>
      {onDismiss && <button onClick={onDismiss} aria-label={t("dismiss")} className="p-1 -m-1"><X className="h-4 w-4" /></button>}
    </div>
  );
}

const STATUS_STYLE: Record<OrderStatus, string> = {
  placed: "bg-warn-soft text-warn", confirmed: "bg-indigo-soft text-indigo-dark", dispatched: "bg-ok-soft text-ok", rejected: "bg-bad-soft text-bad",
};
export function StatusBadge({ status }: { status: OrderStatus }) {
  const { t } = useI18n();
  return <span className={`chip ${STATUS_STYLE[status]}`}>{t(`status_${status}` as TKey)}</span>;
}

const LINE_STYLE: Record<LineStatus, string> = {
  ok: "bg-ok-soft text-ok", needs_clarification: "bg-warn-soft text-warn", out_of_stock: "bg-bad-soft text-bad",
  insufficient_stock: "bg-bad-soft text-bad", invalid_quantity: "bg-bad-soft text-bad",
};
export function LineStatusBadge({ status }: { status: LineStatus }) {
  const { t } = useI18n();
  return <span className={`chip ${LINE_STYLE[status]}`}>{t(`st_${status}` as TKey)}</span>;
}

/** Large, touch-friendly quantity control. Typing is allowed; the value is clamped by the caller. */
export function Stepper({ value, onChange, min = 0, max = 10000, label }: { value: number | null; onChange: (n: number) => void; min?: number; max?: number; label: string }) {
  const { t } = useI18n();
  const v = value ?? 0;
  return (
    <div className="inline-flex items-center rounded-xl border border-line bg-white" role="group" aria-label={label}>
      <button type="button" className="h-12 w-12 grid place-items-center rounded-l-xl hover:bg-paper disabled:opacity-40" aria-label={t("decrease")}
        disabled={v <= min} onClick={() => onChange(Math.max(min, v - 1))}><Minus className="h-5 w-5" /></button>
      <input inputMode="numeric" pattern="[0-9]*" aria-label={label} value={value === null ? "" : String(value)} placeholder="0"
        onChange={(e) => { const d = e.target.value.replace(/\D/g, "").slice(0, 5); onChange(d === "" ? min : Math.min(max, Number(d))); }}
        className="h-12 w-16 text-center text-lg font-semibold bg-transparent border-x border-line" />
      <button type="button" className="h-12 w-12 grid place-items-center rounded-r-xl hover:bg-paper disabled:opacity-40" aria-label={t("increase")}
        disabled={v >= max} onClick={() => onChange(Math.min(max, v + 1))}><Plus className="h-5 w-5" /></button>
    </div>
  );
}

export function SchemeTag({ children }: { children: ReactNode }) {
  return <span className="tag-scheme">{children}</span>;
}
