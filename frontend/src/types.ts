export type Role = "retailer" | "desk" | "salesman";
export interface RetailerBrief { id: number; code: string; name: string; city: string }
export interface User { id: number; email: string; name: string; role: Role; retailer: RetailerBrief | null }
export interface Scheme { type: "free_goods" | "percent_discount"; description: string; buy_qty: number; free_qty: number; min_cases: number; percent_bp: number }
export interface Product {
  sku: string; name: string; name_hi: string | null; packaging_label: string; case_size: number;
  unit_price_paise: number; case_price_paise: number; stock_cases: number; stock_status: "in_stock" | "out_of_stock"; scheme: Scheme | null;
}
export interface Catalogue { products: Product[]; price_basis: string; gst_status: "unspecified"; gst_note: string }
export interface Credit { credit_limit_paise: number; outstanding_paise: number; open_orders_paise: number; available_paise: number; is_demo_data: boolean }
export interface Issue { code: string; message: string }
export interface QuoteLine {
  sku: string; product_name: string | null; quantity_cases: number; free_cases: number; case_price_paise: number | null;
  gross_paise: number | null; discount_paise: number | null; line_total_paise: number | null; scheme_applied: string | null; issues: Issue[];
}
export interface Quote {
  lines: QuoteLine[]; subtotal_paise: number; discount_paise: number; total_paise: number; free_cases: number;
  can_order: boolean; credit: Credit; credit_ok: boolean;
}
export type OrderStatus = "placed" | "confirmed" | "dispatched" | "rejected";
export type OrderSource = "manual" | "ai" | "repeat";
export interface OrderItem {
  id: number; sku: string; product_name: string; packaging_label: string; case_size: number; unit_price_paise: number;
  case_price_paise: number; quantity_cases: number; free_cases: number; gross_paise: number; discount_paise: number;
  line_total_paise: number; scheme_applied: string | null; original_phrase: string | null; ai_confidence: number | null;
  ai_matched_sku: string | null; ai_alternatives: { sku: string; name: string }[] | null; was_corrected: boolean;
}
export interface Order {
  id: number; order_number: string; status: OrderStatus; source: OrderSource; retailer: RetailerBrief; created_at: string;
  updated_at: string; subtotal_paise: number; discount_paise: number; total_paise: number; original_message: string | null;
  rejection_reason: string | null; exported_at: string | null; repeat_of_order_id: number | null; items: OrderItem[];
}
export interface DeskOrder extends Order {
  retailer_detail: RetailerBrief & { credit: Credit };
  ai: { mode: "llm" | "fallback"; fallback_reason: string | null; model: string | null } | null;
}
export interface OrderSummary {
  id: number; order_number: string; status: OrderStatus; source: OrderSource; retailer: RetailerBrief; created_at: string;
  total_paise: number; item_count: number; exported_at: string | null;
}
export interface OrderCreated { order: Order; duplicate: boolean }
export interface Repeat { order_id: number; order_number: string; created_at: string; items: { sku: string; quantity_cases: number }[] }
export type LineStatus = "ok" | "needs_clarification" | "out_of_stock" | "insufficient_stock" | "invalid_quantity";
export interface ParsedLine {
  line_id: string; original_phrase: string; sku: string | null; product_name: string | null; quantity: number | null;
  raw_quantity: number | null; unit: "case" | "piece" | "unknown"; packaging: string | null; confidence: number;
  match_source: string; alternatives: { sku: string; name: string }[]; validation_status: LineStatus;
  clarification: "product" | "unit" | "quantity" | null; messages: string[]; stock_cases: number | null;
  free_cases: number | null; line_total_paise: number | null;
}
export interface ParseResult { parse_id: number; mode: "llm" | "fallback"; fallback_reason: string | null; model: string | null; original_message: string; lines: ParsedLine[] }
export interface AiStatus { mode: "llm" | "fallback"; model: string | null; reason: string | null }
export interface Alias { id: number; alias_text: string; sku: string; product_name: string; created_at: string }
export interface DeskRetailer extends RetailerBrief { credit: Credit }
