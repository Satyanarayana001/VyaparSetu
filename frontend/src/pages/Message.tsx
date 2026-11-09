import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Info, Sparkles, Trash2 } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Banner, LineStatusBadge, Stepper } from "../components/ui";
import { ApiError, errorMessage, post } from "../lib/api";
import { confidenceLabel, formatINR, newIdempotencyKey } from "../lib/format";
import { useI18n, type TKey } from "../lib/i18n";
import { useAiStatus, useQuote } from "../lib/queries";
import type { OrderCreated, ParsedLine, ParseResult } from "../types";

const EXAMPLES = [
  "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti",
  "biscuit 5, 2 peti powder, 3 packet chai",
  "५ पेटी बिस्कुट, २ पेटी वॉशिंग पाउडर",
];

export interface LineState { parsed: ParsedLine; sku: string | null; qty: number | null; productOk: boolean; removed: boolean }

export function initLines(lines: ParsedLine[]): LineState[] {
  return lines.map((p) => ({ parsed: p, sku: p.sku, qty: p.quantity, productOk: p.clarification !== "product" && !!p.sku, removed: false }));
}
/** A line may be confirmed only when the person has settled product and quantity themselves or the match was clear. */
export function lineReady(l: LineState, issuesBySku: Map<string, number>): boolean {
  return !l.removed && !!l.sku && l.productOk && !!l.qty && l.qty >= 1 && !issuesBySku.get(l.sku);
}

function Line({ l, onChange, issues, nameOf }: { l: LineState; onChange: (p: Partial<LineState>) => void; issues: { code: string; message: string }[]; nameOf: (sku: string) => string }) {
  const { t } = useI18n();
  const p = l.parsed;
  const conf = confidenceLabel(p.confidence);
  const choices = [p.sku, ...p.alternatives.map((a) => a.sku)].filter((s): s is string => !!s);
  const needsUnit = p.clarification === "unit" && l.qty === null;
  const unresolved = !l.productOk || !l.qty;
  const code = issues[0]?.code;
  const shown: ParsedLine["validation_status"] = unresolved ? (p.validation_status === "invalid_quantity" ? "invalid_quantity" : "needs_clarification")
    : code === "OUT_OF_STOCK" ? "out_of_stock" : code ? "insufficient_stock" : "ok";
  const productMsgs = !l.productOk && p.clarification === "product" ? p.messages.slice(0, 1) : [];
  const qtyMsgs = l.qty === null ? (p.clarification === "product" ? p.messages.slice(1) : p.messages) : [];
  const messages = [...productMsgs, ...qtyMsgs, ...issues.map((i) => i.message)];
  return (
    <li className={`tile p-4 ${shown !== "ok" ? "!border-warn/60" : ""}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <p className="text-sm text-muted">{t("youWrote")}: <q className="font-semibold text-ink">{p.original_phrase}</q></p>
        <LineStatusBadge status={shown} />
      </div>
      <div className="mt-2 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-lg font-bold">{l.sku ? nameOf(l.sku) : t("chooseProduct")}</p>
          <p className="text-sm text-muted">{l.sku ?? "—"}{p.packaging ? ` · ${p.packaging}` : ""}</p>
        </div>
        <div className="text-right text-sm"><p className="text-muted">{t("confidence")}</p>
          <p className={`font-bold ${conf === "low" ? "text-bad" : conf === "medium" ? "text-warn" : "text-ok"}`}>{Math.round(p.confidence * 100)}% · {t(conf)}</p>
          {p.match_source === "alias" && <p className="text-xs text-indigo">{t("viaAlias")}</p>}</div>
      </div>
      {messages.map((m, i) => <p key={i} role="alert" className="mt-2 flex gap-2 text-sm font-semibold text-warn"><Info className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />{m}</p>)}
      <div className="mt-3">
        <p className="mb-1 text-sm text-muted">{t("notRight")}</p>
        <div className="flex flex-wrap gap-2" role="group" aria-label={t("chooseProduct")}>
          {choices.map((sku) => (
            <button key={sku} type="button" aria-pressed={l.sku === sku && l.productOk} onClick={() => onChange({ sku, productOk: true })}
              className={`min-h-[44px] rounded-xl border px-3 text-left text-sm font-semibold ${l.sku === sku && l.productOk ? "border-indigo bg-indigo-soft text-indigo-dark" : "border-line bg-white"}`}>{nameOf(sku)}</button>))}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Stepper value={l.qty} min={0} onChange={(n) => onChange({ qty: n === 0 ? null : n })} label={`${t("casesLabel")} – ${p.original_phrase}`} />
          <span className="text-muted">{t("casesLabel")}</span>
          {needsUnit && p.raw_quantity && Number.isInteger(p.raw_quantity) && p.raw_quantity > 0 && p.unit === "unknown" &&
            <button type="button" className="btn btn-secondary !min-h-[44px] text-sm" onClick={() => onChange({ qty: p.raw_quantity })}>{t("useCases", { n: p.raw_quantity })}</button>}
        </div>
        <button type="button" className="btn btn-danger !min-h-[44px] text-sm" onClick={() => onChange({ removed: true })}><Trash2 className="h-4 w-4" />{t("removeLine")}</button>
      </div>
    </li>
  );
}

export default function Message() {
  const { t } = useI18n();
  const nav = useNavigate();
  const qc = useQueryClient();
  const ai = useAiStatus();
  const [text, setText] = useState("");
  const [result, setResult] = useState<ParseResult | null>(null);
  const [lines, setLines] = useState<LineState[]>([]);
  const parse = useMutation({
    mutationFn: () => post<ParseResult>("/ai/parse", { message: text.trim() }),
    onSuccess: (r) => { setResult(r); setLines(initLines(r.lines)); },
  });

  const active = lines.filter((l) => !l.removed);
  const quoteItems = useMemo(() => active.filter((l) => l.sku && l.productOk && l.qty && l.qty >= 1).map((l) => ({ sku: l.sku!, quantity_cases: l.qty! })), [active]);
  const quote = useQuote(quoteItems);
  const issuesBySku = new Map<string, number>();
  const issueText = new Map<string, { code: string; message: string }[]>();
  quote.data?.lines.forEach((ql) => { issuesBySku.set(ql.sku, ql.issues.length); issueText.set(ql.sku, ql.issues); });
  const nameOf = (sku: string) => result?.lines.flatMap((l) => [{ sku: l.sku, name: l.product_name }, ...l.alternatives]).find((x) => x?.sku === sku)?.name ?? sku;

  const ready = active.length > 0 && active.every((l) => lineReady(l, issuesBySku)) && !quote.isFetching && !!quote.data?.can_order;
  const attention = active.filter((l) => !lineReady(l, issuesBySku)).length;
  const keyRef = useRef(newIdempotencyKey());

  const confirm = useMutation({
    mutationFn: () => post<OrderCreated>("/orders", {
      source: "ai", ai_parse_id: result!.parse_id, idempotency_key: keyRef.current,
      items: active.map((l) => ({ sku: l.sku, quantity_cases: l.qty, ai_line_id: l.parsed.line_id })) }),
    onSuccess: (res) => {
      keyRef.current = newIdempotencyKey();
      ["orders", "profile", "catalogue", "last-repeatable"].forEach((k) => qc.invalidateQueries({ queryKey: [k] }));
      nav(`/orders/${res.order.id}`, { state: { placed: true } });
    },
  });
  const change = (id: string) => (patch: Partial<LineState>) => { setLines((ls) => ls.map((l) => (l.parsed.line_id === id ? { ...l, ...patch } : l))); keyRef.current = newIdempotencyKey(); };

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <div><h1 className="text-2xl font-bold">{t("aiTitle")}</h1><p className="mt-1 text-muted">{t("aiSub")}</p></div>
      {ai.data && (ai.data.mode === "llm"
        ? <Banner tone="info"><Sparkles className="mr-1 inline h-4 w-4" />{t("modeLlm")}: {ai.data.model}</Banner>
        : <Banner tone="warn"><b>{t("modeFallback")}.</b> {t("modeFallbackHelp")}</Banner>)}
      {!result && (
        <div className="tile space-y-3 p-4">
          <label htmlFor="msg" className="sr-only">{t("aiTitle")}</label>
          <textarea id="msg" className="input min-h-[140px] py-3" maxLength={1000} lang="hi" placeholder={t("aiPlaceholder")} value={text} onChange={(e) => setText(e.target.value)} />
          <div><p className="mb-1 text-sm text-muted">{t("examples")}</p>
            <div className="flex flex-col gap-2">{EXAMPLES.map((e) => <button key={e} type="button" onClick={() => setText(e)} className="min-h-[44px] rounded-xl border border-line px-3 py-2 text-left text-sm hover:bg-paper">{e}</button>)}</div></div>
          {parse.isError && <Banner tone="bad">{errorMessage(parse.error)}</Banner>}
          <button className="btn btn-primary w-full" disabled={!text.trim() || parse.isPending} onClick={() => parse.mutate()}>{parse.isPending ? t("reading") : t("readOrder")}</button>
        </div>)}
      {result && (<>
        <div className="flex items-center justify-between"><h2 className="text-xl font-bold">{t("reviewLines")}</h2>
          <button className="btn btn-ghost" onClick={() => { setResult(null); setLines([]); }}>{t("readAgain")}</button></div>
        <blockquote className="rounded-xl bg-white p-3 text-sm text-muted border border-line">{result.original_message}</blockquote>
        {result.mode === "fallback" && <p className="text-sm text-muted">{t("mode_fallback")}{result.fallback_reason ? ` – ${result.fallback_reason}` : ""}</p>}
        {result.lines.length === 0 && <Banner tone="warn">{t("nothingFound")}</Banner>}
        <ul className="space-y-3">{lines.filter((l) => !l.removed).map((l) => (
          <Line key={l.parsed.line_id} l={l} onChange={change(l.parsed.line_id)} nameOf={nameOf} issues={l.sku ? issueText.get(l.sku) ?? [] : []} />))}</ul>
        <div className="tile sticky bottom-24 space-y-2 p-4 shadow-soft">
          {quote.data && quoteItems.length > 0 && <div className="flex items-end justify-between"><span className="text-muted">{t("total")}</span><span className="text-2xl font-bold">{formatINR(quote.data.total_paise)}</span></div>}
          {!quote.data?.credit_ok && quote.data && <Banner tone="bad">{t("overCredit")}</Banner>}
          {confirm.isError && <Banner tone="bad">{errorMessage(confirm.error)}{confirm.error instanceof ApiError && Array.isArray(confirm.error.details) && <ul className="list-disc pl-4">{(confirm.error.details as { message: string }[]).map((d, i) => <li key={i}>{d.message}</li>)}</ul>}</Banner>}
          <p className={`text-sm font-semibold ${ready ? "text-ok" : "text-warn"}`}>{ready ? t("allChecked") : active.length === 0 ? t("nothingFound") : `${t("needsAttention", { n: attention })}. ${t("clarifyFirst")}`}</p>
          <button className="btn btn-primary w-full" disabled={!ready || !quote.data?.credit_ok || confirm.isPending} onClick={() => confirm.mutate()}>{confirm.isPending ? t("placing") : t("confirmOrder")}</button>
        </div></>)}
    </div>
  );
}
export type { TKey };
