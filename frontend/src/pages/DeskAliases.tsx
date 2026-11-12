import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useState } from "react";
import { Banner, EmptyState, ErrorState, Skeleton } from "../components/ui";
import { del, errorMessage, get, post } from "../lib/api";
import { useI18n } from "../lib/i18n";
import type { Alias, Catalogue, DeskRetailer } from "../types";

export default function DeskAliases() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const retailers = useQuery({ queryKey: ["desk-retailers"], queryFn: () => get<DeskRetailer[]>("/desk/retailers") });
  const [rid, setRid] = useState<number | null>(null);
  const current = rid ?? retailers.data?.[0]?.id ?? null;
  const aliases = useQuery({ queryKey: ["aliases", current], queryFn: () => get<Alias[]>(`/desk/retailers/${current}/aliases`), enabled: current !== null });
  const cat = useQuery({ queryKey: ["catalogue", "desk", current], queryFn: () => get<Catalogue>(`/retailers/${current}/catalogue`), enabled: current !== null });
  const [phrase, setPhrase] = useState("");
  const [sku, setSku] = useState("");
  const add = useMutation({
    mutationFn: () => post<Alias>(`/desk/retailers/${current}/aliases`, { alias_text: phrase, sku: sku || cat.data!.products[0].sku }),
    onSuccess: () => { setPhrase(""); qc.invalidateQueries({ queryKey: ["aliases", current] }); },
  });
  const remove = useMutation({ mutationFn: (id: number) => del(`/desk/retailers/${current}/aliases/${id}`), onSuccess: () => qc.invalidateQueries({ queryKey: ["aliases", current] }) });
  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <div><p className="section-kicker">Retailer-specific learning</p><h1 className="page-title mt-1">{t("aliasesTitle")}</h1><p className="mt-1 text-sm text-muted">{t("aliasesSub")}</p></div>
      {retailers.isError && <ErrorState message={errorMessage(retailers.error)} onRetry={() => retailers.refetch()} />}
      <label className="block font-medium">{t("retailer")}
        <select className="input mt-1" value={current ?? ""} onChange={(e) => setRid(Number(e.target.value))}>{retailers.data?.map((r) => <option key={r.id} value={r.id}>{r.name} ({r.code})</option>)}</select></label>
      <form className="tile grid gap-3 p-4 sm:grid-cols-[1fr_1fr_auto] sm:items-end" onSubmit={(e) => { e.preventDefault(); if (phrase.trim()) add.mutate(); }}>
        <label className="block text-sm font-medium">{t("aliasPhrase")}<input className="input mt-1" value={phrase} maxLength={120} onChange={(e) => setPhrase(e.target.value)} placeholder="chhota biscuit" /></label>
        <label className="block text-sm font-medium">{t("product")}<select className="input mt-1" value={sku} onChange={(e) => setSku(e.target.value)}>{cat.data?.products.map((p) => <option key={p.sku} value={p.sku}>{p.name}</option>)}</select></label>
        <button className="btn btn-primary" disabled={!phrase.trim() || add.isPending || !cat.data}>{t("addAlias")}</button>
      </form>
      {add.isError && <Banner tone="bad">{errorMessage(add.error)}</Banner>}
      {remove.isError && <Banner tone="bad">{errorMessage(remove.error)}</Banner>}
      {aliases.isPending ? <Skeleton className="h-24" /> : aliases.isError ? <ErrorState message={errorMessage(aliases.error)} onRetry={() => aliases.refetch()} /> :
        aliases.data.length === 0 ? <div className="tile"><EmptyState title={t("noAliases")} hint={t("noAliasesSub")} /></div> :
        <ul className="tile divide-y divide-line">{aliases.data.map((a) => (
          <li key={a.id} className="flex min-h-[56px] items-center gap-3 px-4 py-2"><div className="min-w-0 flex-1"><p className="font-semibold">“{a.alias_text}”</p><p className="text-sm text-muted">→ {a.product_name} ({a.sku})</p></div>
            <button className="grid h-11 w-11 place-items-center rounded-xl text-muted hover:bg-bad-soft hover:text-bad" aria-label={`${t("delete")} ${a.alias_text}`} onClick={() => remove.mutate(a.id)}><Trash2 className="h-5 w-5" /></button></li>))}</ul>}
    </div>
  );
}
