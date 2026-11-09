const inr = new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

/** Display-only formatting of integer paise. All money arithmetic happens on the server. */
export function formatINR(paise: number): string {
  const sign = paise < 0 ? "-" : "";
  return `${sign}₹${inr.format(Math.abs(paise) / 100)}`;
}

export function formatDate(iso: string, lang: string): string {
  return new Date(iso).toLocaleString(lang === "hi" ? "hi-IN" : "en-IN", { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
}

export function newIdempotencyKey(): string {
  const c = globalThis.crypto;
  if (c && "randomUUID" in c) return c.randomUUID();
  return `k${Date.now().toString(36)}${Math.random().toString(36).slice(2, 12)}`;
}

export function confidenceLabel(c: number): "high" | "medium" | "low" {
  return c >= 0.85 ? "high" : c >= 0.7 ? "medium" : "low";
}
