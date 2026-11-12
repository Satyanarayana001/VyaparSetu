import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { User } from "../types";
import { get, post, setUnauthorizedHandler, tokenStore } from "./api";

interface Auth {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (details: { shop_name: string; owner_name: string; email: string; password: string }) => Promise<User>;
  logout: () => void;
}
const Ctx = createContext<Auth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => !!tokenStore.get());
  const qc = useQueryClient();

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    qc.clear();                       // never leave one user's prices/orders in cache for the next
    try { sessionStorage.removeItem("cart"); } catch { /* ignore */ }
    window.dispatchEvent(new Event("app:logout"));   // CartProvider listens and empties in-memory state too
  }, [qc]);

  useEffect(() => { setUnauthorizedHandler(logout); }, [logout]);
  useEffect(() => {
    if (!tokenStore.get()) return;
    get<User>("/auth/me").then(setUser).catch(() => tokenStore.clear()).finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await post<{ access_token: string; user: User }>("/auth/login", { email, password });
    qc.clear();
    tokenStore.set(res.access_token);
    setUser(res.user);
    return res.user;
  }, [qc]);

  const register = useCallback(async (details: { shop_name: string; owner_name: string; email: string; password: string }) => {
    const res = await post<{ access_token: string; user: User }>("/auth/register", details);
    qc.clear();
    tokenStore.set(res.access_token);
    setUser(res.user);
    return res.user;
  }, [qc]);

  const value = useMemo(() => ({ user, loading, login, register, logout }), [user, loading, login, register, logout]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAuth(): Auth {
  const c = useContext(Ctx);
  if (!c) throw new Error("useAuth must be used inside AuthProvider");
  return c;
}
