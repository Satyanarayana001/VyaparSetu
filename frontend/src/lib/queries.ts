import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { AiStatus, Catalogue, Credit, Quote, RetailerBrief } from "../types";
import { get, post } from "./api";

export const useProfile = () =>
  useQuery({ queryKey: ["profile"], queryFn: () => get<{ retailer: RetailerBrief; credit: Credit }>("/retailer/me") });

export const useCatalogue = (q = "") =>
  useQuery({ queryKey: ["catalogue", q], queryFn: () => get<Catalogue>(`/catalogue?q=${encodeURIComponent(q)}`), placeholderData: keepPreviousData });

export const useAiStatus = () => useQuery({ queryKey: ["ai-status"], queryFn: () => get<AiStatus>("/ai/status"), staleTime: 60_000 });

export interface QuoteItem { sku: string; quantity_cases: number }
/** Pricing always comes from the server; the UI never calculates schemes, discounts or totals. */
export const useQuote = (items: QuoteItem[]) =>
  useQuery({
    queryKey: ["quote", items],
    queryFn: () => post<Quote>("/orders/quote", { items }),
    enabled: items.length > 0,
    placeholderData: keepPreviousData,
  });
