import { ArrowRight, Boxes, Eye, EyeOff, ShieldCheck, Store } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Banner } from "../components/ui";
import { errorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";

const DEMOS = [
  { label: "Sharma General Stores", role: "Retailer", email: "retailer1@demo.test", password: "Retailer@123" },
  { label: "Krishna Kirana Store", role: "Retailer · credit demo", email: "retailer2@demo.test", password: "Retailer@123" },
  { label: "Company A Order Desk", role: "Order desk", email: "desk@demo.test", password: "Desk@12345" },
];
const SHOW_DEMOS = import.meta.env.VITE_SHOW_DEMO_LOGINS !== "false";

export default function Login() {
  const { t, lang, setLang } = useI18n();
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [shopName, setShopName] = useState("");
  const [ownerName, setOwnerName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e?: FormEvent, creds?: { email: string; password: string }) {
    e?.preventDefault();
    setBusy(true); setError(null);
    try {
      const u = mode === "signup" && !creds
        ? await register({ shop_name: shopName.trim(), owner_name: ownerName.trim(), email: email.trim(), password })
        : await login(creds?.email ?? email, creds?.password ?? password);
      nav(u.role === "desk" ? "/desk" : "/", { replace: true });
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <main className="min-h-screen bg-paper">
      <div className="grid min-h-screen lg:grid-cols-[1.05fr_.95fr]">
        <section className="relative hidden overflow-hidden bg-forest px-12 py-10 text-white lg:flex lg:flex-col lg:justify-between xl:px-20">
          <div className="absolute -right-28 -top-28 h-96 w-96 rounded-full border border-white/10" />
          <div className="absolute -bottom-44 -left-20 h-[30rem] w-[30rem] rounded-full border border-white/10" />
          <div className="relative flex items-center gap-3">
            <span className="grid h-11 w-11 place-items-center rounded-xl bg-white text-forest"><Boxes className="h-6 w-6" /></span>
            <div><p className="text-xl font-bold tracking-tight">VyaparSetu</p><p className="text-xs text-white/65">Company A · Jabalpur</p></div>
          </div>
          <div className="relative max-w-xl py-16">
            <p className="mb-4 text-xs font-bold uppercase tracking-[.2em] text-[#F3C77B]">Wholesale, made simpler</p>
            <h1 className="text-5xl font-bold leading-[1.08] tracking-tight xl:text-6xl">Your shop.<br/>Your stock.<br/><span className="text-[#E8C88F]">Your next order.</span></h1>
            <p className="mt-6 max-w-md text-lg leading-relaxed text-white/75">A simpler way for kirana retailers to check availability, access their prices and place orders with confidence.</p>
            <div className="mt-10 flex flex-wrap gap-3 text-sm text-white/85">
              <span className="rounded-full border border-white/20 px-4 py-2">Live stock visibility</span>
              <span className="rounded-full border border-white/20 px-4 py-2">Retailer schemes</span>
              <span className="rounded-full border border-white/20 px-4 py-2">AI-assisted orders</span>
            </div>
          </div>
          <p className="relative text-xs text-white/50">A demonstration ordering platform · Fictional sample accounts</p>
        </section>

        <section className="flex min-h-screen items-center justify-center px-5 py-8 sm:px-8">
          <div className="w-full max-w-md">
            <div className="mb-8 flex items-center justify-between lg:justify-end">
              <div className="flex items-center gap-3 lg:hidden">
                <span className="grid h-10 w-10 place-items-center rounded-xl bg-forest text-white"><Boxes className="h-5 w-5"/></span>
                <div><p className="font-bold text-ink">VyaparSetu</p><p className="text-xs text-muted">Company A · Jabalpur</p></div>
              </div>
              <button type="button" className="btn btn-ghost !min-h-10 !px-3" onClick={() => setLang(lang === "en" ? "hi" : "en")}>{t("language")}</button>
            </div>

            <div className="mb-7">
              <p className="section-kicker">{mode === "signin" ? "Welcome back" : "Retailer registration"}</p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight text-ink">{mode === "signin" ? "Sign in to your account" : "Set up your shop account"}</h2>
              <p className="mt-2 text-sm leading-relaxed text-muted">{mode === "signin" ? "Access your retailer catalogue, pricing and orders." : "Create a retailer account to start exploring the catalogue. New accounts begin with no assigned credit."}</p>
            </div>

            <div className="mb-5 grid grid-cols-2 rounded-xl bg-[#EDEFEA] p-1">
              <button type="button" onClick={() => { setMode("signin"); setError(null); }} className={`min-h-11 rounded-lg text-sm font-semibold transition ${mode === "signin" ? "bg-white text-forest shadow-sm" : "text-muted"}`}>Sign in</button>
              <button type="button" onClick={() => { setMode("signup"); setError(null); }} className={`min-h-11 rounded-lg text-sm font-semibold transition ${mode === "signup" ? "bg-white text-forest shadow-sm" : "text-muted"}`}>Create account</button>
            </div>

            <form onSubmit={submit} className="tile space-y-4 p-5 sm:p-6" noValidate>
              {error && <Banner tone="bad">{error}</Banner>}
              {mode === "signup" && <>
                <div><label htmlFor="shopName" className="mb-1.5 block text-sm font-semibold">Shop / business name</label><input id="shopName" className="input" autoComplete="organization" value={shopName} onChange={e => setShopName(e.target.value)} required minLength={2} placeholder="e.g. Sharma General Stores"/></div>
                <div><label htmlFor="ownerName" className="mb-1.5 block text-sm font-semibold">Owner name</label><input id="ownerName" className="input" autoComplete="name" value={ownerName} onChange={e => setOwnerName(e.target.value)} required minLength={2} placeholder="Your full name"/></div>
              </>}
              <div><label htmlFor="email" className="mb-1.5 block text-sm font-semibold">{t("email")}</label><input id="email" className="input" type="email" autoComplete="username" value={email} onChange={e => setEmail(e.target.value)} required placeholder="you@example.com"/></div>
              <div>
                <label htmlFor="password" className="mb-1.5 block text-sm font-semibold">{t("password")}</label>
                <div className="relative"><input id="password" className="input pr-12" type={showPassword ? "text" : "password"} autoComplete={mode === "signup" ? "new-password" : "current-password"} value={password} onChange={e => setPassword(e.target.value)} required minLength={mode === "signup" ? 10 : 1} placeholder={mode === "signup" ? "At least 10 characters" : "Enter your password"}/><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(v => !v)} className="absolute right-2 top-1/2 grid h-10 w-10 -translate-y-1/2 place-items-center rounded-lg text-muted hover:bg-paper">{showPassword ? <EyeOff className="h-5 w-5"/> : <Eye className="h-5 w-5"/>}</button></div>
              </div>
              {mode === "signup" && <div className="flex gap-2 rounded-xl bg-forest-soft p-3 text-xs leading-relaxed text-forest"><ShieldCheck className="mt-0.5 h-4 w-4 shrink-0"/>Public registration creates a retailer account only. Order desk access is invitation-only. Credit is assigned separately by the distributor.</div>}
              <button className="btn btn-primary w-full !min-h-[52px]" disabled={busy || !email || !password || (mode === "signup" && (!shopName.trim() || !ownerName.trim() || password.length < 10))}>{busy ? (mode === "signin" ? t("signingIn") : "Creating account…") : <>{mode === "signin" ? t("signIn") : "Create retailer account"} <ArrowRight className="h-4 w-4"/></>}</button>
            </form>

            {mode === "signin" && SHOW_DEMOS && <div className="mt-6">
              <div className="mb-3 flex items-center justify-between"><p className="text-sm font-semibold text-ink">Reviewer demo access</p><span className="text-[11px] text-muted">Sample accounts</span></div>
              <div className="space-y-2">
                {DEMOS.map(d => <button key={d.email} type="button" className="flex min-h-[58px] w-full items-center gap-3 rounded-xl border border-line bg-white px-4 text-left transition hover:border-forest/40 hover:bg-forest-soft/40 disabled:opacity-50" disabled={busy} onClick={() => submit(undefined, d)}>
                  <span className="grid h-9 w-9 place-items-center rounded-lg bg-forest-soft text-forest">{d.role === "Order desk" ? <ShieldCheck className="h-5 w-5"/> : <Store className="h-5 w-5"/>}</span>
                  <span className="min-w-0 flex-1"><span className="block text-sm font-semibold text-ink">{d.label}</span><span className="block text-xs text-muted">{d.role}</span></span><ArrowRight className="h-4 w-4 text-muted"/>
                </button>)}
              </div>
            </div>}
            <p className="mt-6 text-center text-xs text-muted">Company A · Jabalpur <span className="mx-1">·</span> Demo ordering platform</p>
          </div>
        </section>
      </div>
    </main>
  );
}
