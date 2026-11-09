import { Boxes } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Banner } from "../components/ui";
import { errorMessage } from "../lib/api";
import { useAuth } from "../lib/auth";
import { useI18n } from "../lib/i18n";

const DEMOS = [
  { label: "Retailer 1 (Sharma)", email: "retailer1@demo.test", password: "Retailer@123" },
  { label: "Retailer 2 (tight credit)", email: "retailer2@demo.test", password: "Retailer@123" },
  { label: "Order desk", email: "desk@demo.test", password: "Desk@12345" },
];
const SHOW_DEMOS = import.meta.env.VITE_SHOW_DEMO_LOGINS === "true";

export default function Login() {
  const { t, lang, setLang } = useI18n();
  const { login } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e?: FormEvent, creds?: { email: string; password: string }) {
    e?.preventDefault();
    setBusy(true); setError(null);
    try {
      const u = await login(creds?.email ?? email, creds?.password ?? password);
      nav(u.role === "desk" ? "/desk" : "/", { replace: true });
    } catch (err) { setError(errorMessage(err)); } finally { setBusy(false); }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-10">
      <div className="mb-8 flex items-center gap-3">
        <span className="grid h-12 w-12 place-items-center rounded-2xl border-2 border-ink bg-indigo text-white shadow-brut"><Boxes className="h-6 w-6" /></span>
        <h1 className="text-2xl font-bold leading-tight">{t("appName")}</h1>
        <button type="button" className="btn btn-ghost ml-auto" onClick={() => setLang(lang === "en" ? "hi" : "en")}>{t("language")}</button>
      </div>
      <form onSubmit={submit} className="tile space-y-4 p-6" noValidate>
        {error && <Banner tone="bad">{error}</Banner>}
        <div>
          <label htmlFor="email" className="mb-1 block font-medium">{t("email")}</label>
          <input id="email" className="input" type="email" autoComplete="username" value={email} onChange={(e) => setEmail(e.target.value)} required />
        </div>
        <div>
          <label htmlFor="password" className="mb-1 block font-medium">{t("password")}</label>
          <input id="password" className="input" type="password" autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        </div>
        <button className="btn btn-primary w-full" disabled={busy || !email || !password}>{busy ? t("signingIn") : t("signIn")}</button>
      </form>
      {SHOW_DEMOS && (
        <div className="mt-6">
          <p className="mb-2 text-sm text-muted">{t("demoLogins")}</p>
          <div className="flex flex-wrap gap-2">
            {DEMOS.map((d) => <button key={d.email} type="button" className="btn btn-secondary !min-h-[44px] text-sm" disabled={busy} onClick={() => submit(undefined, d)}>{d.label}</button>)}
          </div>
        </div>
      )}
    </main>
  );
}
