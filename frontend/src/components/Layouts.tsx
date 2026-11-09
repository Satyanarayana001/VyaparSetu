import { FileDown, Home, Languages, LogOut, MessageSquareText, ReceiptText, ShoppingBag, ShoppingCart, Tags, ClipboardList, WifiOff } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/auth";
import { useCart } from "../lib/cart";
import { useI18n } from "../lib/i18n";

function useOnline() {
  const [on, setOn] = useState(() => navigator.onLine);
  useEffect(() => {
    const u = () => setOn(true), d = () => setOn(false);
    window.addEventListener("online", u); window.addEventListener("offline", d);
    return () => { window.removeEventListener("online", u); window.removeEventListener("offline", d); };
  }, []);
  return on;
}

function TopBar({ subtitle, children }: { subtitle?: string; children?: React.ReactNode }) {
  const { t, lang, setLang } = useI18n();
  const { logout } = useAuth();
  const nav = useNavigate();
  return (
    <header className="glass sticky top-0 z-30 border-b border-line pt-[env(safe-area-inset-top)]">
      <div className="mx-auto flex max-w-6xl items-center gap-2 px-4 h-14">
        <div className="mr-auto min-w-0">
          <p className="font-bold leading-tight truncate">{t("appName")}</p>
          {subtitle && <p className="text-sm text-muted leading-tight truncate">{subtitle}</p>}
        </div>
        {children}
        <button className="btn btn-ghost !px-3" onClick={() => setLang(lang === "en" ? "hi" : "en")} aria-label="Change language">
          <Languages className="h-5 w-5" /> <span>{t("language")}</span>
        </button>
        <button className="btn btn-ghost !px-3" onClick={() => { logout(); nav("/login"); }} aria-label={t("signOut")}>
          <LogOut className="h-5 w-5" /><span className="hidden sm:inline">{t("signOut")}</span>
        </button>
      </div>
    </header>
  );
}

function OfflineNote() {
  const online = useOnline();
  const { t } = useI18n();
  if (online) return null;
  return <div role="status" className="bg-warn-soft text-warn text-center text-sm py-2 flex items-center justify-center gap-2"><WifiOff className="h-4 w-4" />{t("offline")}</div>;
}

export function RetailerLayout() {
  const { t } = useI18n();
  const { user } = useAuth();
  const { count } = useCart();
  const items = [
    { to: "/", icon: Home, label: t("navHome"), end: true }, { to: "/shop", icon: ShoppingBag, label: t("navShop") },
    { to: "/message", icon: MessageSquareText, label: t("navMessage") }, { to: "/cart", icon: ShoppingCart, label: t("navCart"), badge: count },
    { to: "/orders", icon: ReceiptText, label: t("navOrders") },
  ];
  return (
    <div className="min-h-screen pb-24">
      <TopBar subtitle={user?.retailer?.name} />
      <OfflineNote />
      <main className="mx-auto max-w-6xl px-4 py-5"><Outlet /></main>
      <nav aria-label="Main" className="glass fixed bottom-0 inset-x-0 z-30 border-t border-line pb-[env(safe-area-inset-bottom)]">
        <ul className="mx-auto grid max-w-xl grid-cols-5">
          {items.map(({ to, icon: Icon, label, end, badge }) => (
            <li key={to}>
              <NavLink to={to} end={end} className={({ isActive }) => `relative flex min-h-[60px] flex-col items-center justify-center gap-0.5 text-xs font-semibold ${isActive ? "text-indigo" : "text-muted"}`}>
                {({ isActive }) => (<>
                  <span className={`grid h-8 w-12 place-items-center rounded-full ${isActive ? "bg-indigo-soft" : ""}`}><Icon className="h-5 w-5" /></span>
                  {label}
                  {!!badge && <span className="absolute top-1.5 left-1/2 ml-2 grid h-5 min-w-5 place-items-center rounded-full bg-ink px-1 text-[11px] text-white">{badge}</span>}
                </>)}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}

export function DeskLayout() {
  const { t } = useI18n();
  const { user } = useAuth();
  const tabs = [{ to: "/desk", icon: ClipboardList, label: t("deskOrders"), end: true }, { to: "/desk/export", icon: FileDown, label: t("deskExport") }, { to: "/desk/aliases", icon: Tags, label: t("deskAliases") }];
  return (
    <div className="min-h-screen">
      <TopBar subtitle={user?.name} />
      <OfflineNote />
      <div className="border-b border-line bg-white">
        <nav aria-label="Order desk" className="mx-auto flex max-w-6xl gap-1 overflow-x-auto px-3">
          {tabs.map(({ to, icon: Icon, label, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `flex min-h-[48px] items-center gap-2 border-b-[3px] px-3 font-semibold whitespace-nowrap ${isActive ? "border-indigo text-indigo" : "border-transparent text-muted"}`}>
              <Icon className="h-5 w-5" />{label}
            </NavLink>
          ))}
        </nav>
      </div>
      <main className="mx-auto max-w-6xl px-4 py-5"><Outlet /></main>
    </div>
  );
}
