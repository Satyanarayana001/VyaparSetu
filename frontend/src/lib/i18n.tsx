import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";

export type Lang = "en" | "hi";

const en = {
  appName: "Company A Orders", signIn: "Sign in", signOut: "Sign out", email: "Email", password: "Password",
  signingIn: "Signing in…", demoLogins: "Demo accounts (local only)", language: "हिंदी",
  navHome: "Home", navShop: "Shop", navMessage: "Message", navCart: "Cart", navOrders: "Orders",
  hello: "Hello", availableCredit: "Available credit", creditLimit: "Credit limit", outstanding: "Outstanding", openOrders: "Open orders",
  demoData: "Demo data", orderByMessage: "Order by message", orderByMessageSub: "Type or paste your order. We'll read it for you to check.",
  repeatLast: "Repeat last order", repeatLastSub: "Start from your previous order and change anything.", noPrevious: "No confirmed order to repeat yet.",
  browse: "Browse catalogue", browseSub: "Prices, stock and schemes.", recentOrders: "Recent orders", noOrders: "No orders yet",
  noOrdersSub: "Your orders will show here once you place one.", startShopping: "Browse catalogue", viewAll: "See all",
  searchPlaceholder: "Search products or SKU", caseOf: "per case", packsAt: "packs ×", inStock: "in stock", cases: "cases", case1: "case",
  outOfStock: "Out of stock", outOfStockHelp: "Not available to order right now.", addToCart: "Add to cart", updateCart: "Update cart", inCart: "In cart",
  scheme: "Scheme", free: "free", noProducts: "No products match your search", noProductsSub: "Try a different word or SKU.",
  qty: "Quantity", decrease: "Decrease quantity", increase: "Increase quantity", remove: "Remove",
  cartTitle: "Your cart", cartEmpty: "Your cart is empty", cartEmptySub: "Add products from the catalogue, or order by message.",
  subtotal: "Subtotal", discount: "Discount", total: "Total", freeCases: "Free cases", placeOrder: "Place order", placing: "Placing order…",
  fixCart: "Fix the highlighted items to place your order.", overCredit: "This order is above your available credit.",
  loadedFrom: "Loaded from your order", reviewQty: "Check the quantities, then place the order.", clearCart: "Clear cart",
  priceNote: "Prices are per case. Free cases are taken from stock.", gst: "GST",
  orderPlaced: "Order placed", orderPlacedSub: "The order desk will review it. You can track it here.", status_placed: "Waiting for review",
  status_confirmed: "Confirmed", status_dispatched: "Dispatched", status_rejected: "Rejected", reason: "Reason",
  orderHistory: "Your orders", items: "items", item1: "item", orderDetail: "Order", yourMessage: "Your message", placedVia_ai: "Placed from a message", placedVia_repeat: "Repeat order", placedVia_manual: "Placed from catalogue",
  aiTitle: "Order by message", aiSub: "Write your order the way you'd tell your salesman. Hindi, Hinglish or English all work.",
  aiPlaceholder: "e.g. 5 peti biscuit chhota, 2 peti washing powder 1 kilo", readOrder: "Read my order", reading: "Reading…", examples: "Try an example",
  modeFallback: "Basic reader (no AI model connected)", modeFallbackHelp: "It understands common Hindi and English product words and can make mistakes. Check every line before you confirm.",
  modeLlm: "AI model", reviewLines: "Check your order", nothingFound: "We couldn't find any products in that message.",
  youWrote: "You wrote", matched: "Matched to", confidence: "Confidence", high: "High", medium: "Medium", low: "Low", viaAlias: "Your saved word",
  notRight: "Not right? Choose the product", chooseProduct: "Choose product", casesLabel: "Cases", useCases: "Use {n} cases", needsAttention: "{n} need your attention",
  removeLine: "Remove line", confirmOrder: "Confirm order", allChecked: "Everything checked. Confirm to place the order.", clarifyFirst: "Resolve or remove the flagged lines to continue.",
  readAgain: "Start over", st_ok: "Ready", st_needs_clarification: "Needs a check", st_out_of_stock: "Out of stock", st_insufficient_stock: "Not enough stock", st_invalid_quantity: "Invalid quantity",
  stockLeft: "{n} cases in stock",
  deskOrders: "Orders", deskExport: "Tally export", deskAliases: "Retailer words", search: "Search order or retailer", all: "All",
  noDeskOrders: "No orders here", noDeskOrdersSub: "New orders appear automatically.", selectOrder: "Select an order to review it.",
  retailer: "Retailer", created: "Created", original: "Original message", aiReading: "How it was read", mode_llm: "AI model", mode_fallback: "Basic reader",
  line: "Line", product: "Product", unitPrice: "Price/case", save: "Save change", saving: "Saving…", saveAlias: "Remember these words for this retailer", corrected: "Corrected",
  confirm: "Confirm order", reject: "Reject", markDispatched: "Mark dispatched", rejectReason: "Reason for rejecting", confirmReject: "Reject order", cancel: "Cancel",
  exportTitle: "Tally export", exportSub: "Download confirmed orders as a Tally-compatible CSV. This is a file export, not a live Tally connection.",
  includeExported: "Include orders already exported", selectAll: "Select all", downloadCsv: "Download CSV", exported: "Exported", noExportable: "No confirmed orders to export",
  noExportableSub: "Confirm orders in the queue first.", downloaded: "Downloaded {n} order(s).", columns: "CSV columns",
  aliasesTitle: "Retailer words", aliasesSub: "Words a retailer uses for a product. They apply to that retailer only.", aliasPhrase: "Words the retailer uses", addAlias: "Save words",
  noAliases: "No saved words yet", noAliasesSub: "Correct an AI line on an order, or add words here.", delete: "Delete",
  loading: "Loading…", retry: "Try again", errorTitle: "Couldn't load this", back: "Back", dismiss: "Dismiss",
  offline: "You're offline. Ordering needs a connection.", notAuthorised: "You don't have access to this page.",
  gstUnspecified: "GST: not specified in the client brief. No GST is added.",
  add: "Add", update: "Update", viewCart: "View cart", changeProduct: "Change product", correct: "Correct", toReview: "To review", perCase: "/ case", packs: "packs", pricesPerCase: "Prices are per case",
} as const;

const hi: Record<keyof typeof en, string> = {
  appName: "कंपनी A ऑर्डर", signIn: "साइन इन", signOut: "साइन आउट", email: "ईमेल", password: "पासवर्ड",
  signingIn: "साइन इन हो रहा है…", demoLogins: "डेमो खाते (सिर्फ़ लोकल)", language: "English",
  navHome: "होम", navShop: "दुकान", navMessage: "मैसेज", navCart: "कार्ट", navOrders: "ऑर्डर",
  hello: "नमस्ते", availableCredit: "उपलब्ध क्रेडिट", creditLimit: "क्रेडिट सीमा", outstanding: "बकाया", openOrders: "खुले ऑर्डर",
  demoData: "डेमो डेटा", orderByMessage: "मैसेज से ऑर्डर", orderByMessageSub: "अपना ऑर्डर लिखें या पेस्ट करें। हम उसे पढ़कर आपको जाँचने के लिए दिखाएँगे।",
  repeatLast: "पिछला ऑर्डर दोहराएँ", repeatLastSub: "पिछले ऑर्डर से शुरू करें और जो चाहें बदलें।", noPrevious: "दोहराने के लिए अभी कोई पक्का ऑर्डर नहीं है।",
  browse: "कैटलॉग देखें", browseSub: "भाव, स्टॉक और स्कीम।", recentOrders: "हाल के ऑर्डर", noOrders: "अभी कोई ऑर्डर नहीं",
  noOrdersSub: "ऑर्डर देते ही वह यहाँ दिखेगा।", startShopping: "कैटलॉग देखें", viewAll: "सभी देखें",
  searchPlaceholder: "प्रोडक्ट या SKU खोजें", caseOf: "प्रति पेटी", packsAt: "पैक ×", inStock: "स्टॉक में", cases: "पेटी", case1: "पेटी",
  outOfStock: "स्टॉक खत्म", outOfStockHelp: "अभी ऑर्डर के लिए उपलब्ध नहीं।", addToCart: "कार्ट में जोड़ें", updateCart: "कार्ट अपडेट करें", inCart: "कार्ट में",
  scheme: "स्कीम", free: "फ्री", noProducts: "कोई प्रोडक्ट नहीं मिला", noProductsSub: "कोई दूसरा शब्द या SKU आज़माएँ।",
  qty: "मात्रा", decrease: "मात्रा घटाएँ", increase: "मात्रा बढ़ाएँ", remove: "हटाएँ",
  cartTitle: "आपका कार्ट", cartEmpty: "कार्ट खाली है", cartEmptySub: "कैटलॉग से प्रोडक्ट जोड़ें, या मैसेज से ऑर्डर करें।",
  subtotal: "उप-योग", discount: "छूट", total: "कुल", freeCases: "फ्री पेटी", placeOrder: "ऑर्डर दें", placing: "ऑर्डर हो रहा है…",
  fixCart: "ऑर्डर देने के लिए लाल निशान वाले आइटम ठीक करें।", overCredit: "यह ऑर्डर आपके उपलब्ध क्रेडिट से ज़्यादा है।",
  loadedFrom: "इस ऑर्डर से लिया गया", reviewQty: "मात्रा जाँचें, फिर ऑर्डर दें।", clearCart: "कार्ट खाली करें",
  priceNote: "भाव प्रति पेटी हैं। फ्री पेटी स्टॉक से जाती है।", gst: "GST",
  orderPlaced: "ऑर्डर हो गया", orderPlacedSub: "ऑर्डर डेस्क इसे जाँचेगा। आप यहाँ स्थिति देख सकते हैं।", status_placed: "जाँच का इंतज़ार",
  status_confirmed: "पक्का", status_dispatched: "भेज दिया", status_rejected: "अस्वीकृत", reason: "कारण",
  orderHistory: "आपके ऑर्डर", items: "आइटम", item1: "आइटम", orderDetail: "ऑर्डर", yourMessage: "आपका मैसेज", placedVia_ai: "मैसेज से दिया", placedVia_repeat: "दोहराया ऑर्डर", placedVia_manual: "कैटलॉग से दिया",
  aiTitle: "मैसेज से ऑर्डर", aiSub: "ऑर्डर वैसे ही लिखें जैसे सेल्समैन को बताते हैं। हिंदी, हिंग्लिश या अंग्रेज़ी, सब चलेगा।",
  aiPlaceholder: "जैसे: 5 पेटी बिस्कुट छोटा, 2 पेटी वॉशिंग पाउडर 1 किलो", readOrder: "मेरा ऑर्डर पढ़ें", reading: "पढ़ रहे हैं…", examples: "उदाहरण आज़माएँ",
  modeFallback: "सामान्य रीडर (AI मॉडल जुड़ा नहीं है)", modeFallbackHelp: "यह आम हिंदी और अंग्रेज़ी शब्द समझता है, पर गलती कर सकता है। पक्का करने से पहले हर लाइन जाँचें।",
  modeLlm: "AI मॉडल", reviewLines: "अपना ऑर्डर जाँचें", nothingFound: "इस मैसेज में कोई प्रोडक्ट नहीं मिला।",
  youWrote: "आपने लिखा", matched: "मिलान", confidence: "भरोसा", high: "ज़्यादा", medium: "मध्यम", low: "कम", viaAlias: "आपका सेव किया शब्द",
  notRight: "गलत है? सही प्रोडक्ट चुनें", chooseProduct: "प्रोडक्ट चुनें", casesLabel: "पेटी", useCases: "{n} पेटी लें", needsAttention: "{n} लाइन जाँचनी हैं",
  removeLine: "लाइन हटाएँ", confirmOrder: "ऑर्डर पक्का करें", allChecked: "सब जाँच लिया। ऑर्डर देने के लिए पक्का करें।", clarifyFirst: "आगे बढ़ने के लिए चिह्नित लाइनें ठीक करें या हटाएँ।",
  readAgain: "फिर से शुरू करें", st_ok: "तैयार", st_needs_clarification: "जाँच चाहिए", st_out_of_stock: "स्टॉक खत्म", st_insufficient_stock: "स्टॉक कम है", st_invalid_quantity: "गलत मात्रा",
  stockLeft: "स्टॉक में {n} पेटी",
  deskOrders: "ऑर्डर", deskExport: "Tally एक्सपोर्ट", deskAliases: "रिटेलर के शब्द", search: "ऑर्डर या रिटेलर खोजें", all: "सभी",
  noDeskOrders: "यहाँ कोई ऑर्डर नहीं", noDeskOrdersSub: "नए ऑर्डर अपने आप दिखेंगे।", selectOrder: "जाँचने के लिए कोई ऑर्डर चुनें।",
  retailer: "रिटेलर", created: "बनाया गया", original: "मूल मैसेज", aiReading: "कैसे पढ़ा गया", mode_llm: "AI मॉडल", mode_fallback: "सामान्य रीडर",
  line: "लाइन", product: "प्रोडक्ट", unitPrice: "भाव/पेटी", save: "बदलाव सेव करें", saving: "सेव हो रहा है…", saveAlias: "इस रिटेलर के लिए ये शब्द याद रखें", corrected: "सुधारा गया",
  confirm: "ऑर्डर पक्का करें", reject: "अस्वीकार करें", markDispatched: "भेजा गया चिह्नित करें", rejectReason: "अस्वीकार करने का कारण", confirmReject: "ऑर्डर अस्वीकार करें", cancel: "रद्द करें",
  exportTitle: "Tally एक्सपोर्ट", exportSub: "पक्के ऑर्डर Tally-संगत CSV में डाउनलोड करें। यह फ़ाइल एक्सपोर्ट है, लाइव Tally कनेक्शन नहीं।",
  includeExported: "पहले एक्सपोर्ट हुए ऑर्डर भी शामिल करें", selectAll: "सभी चुनें", downloadCsv: "CSV डाउनलोड करें", exported: "एक्सपोर्ट हुआ", noExportable: "एक्सपोर्ट के लिए कोई पक्का ऑर्डर नहीं",
  noExportableSub: "पहले कतार में ऑर्डर पक्के करें।", downloaded: "{n} ऑर्डर डाउनलोड हुए।", columns: "CSV कॉलम",
  aliasesTitle: "रिटेलर के शब्द", aliasesSub: "किसी प्रोडक्ट के लिए रिटेलर जो शब्द बोलता है। ये सिर्फ़ उसी रिटेलर पर लागू होते हैं।", aliasPhrase: "रिटेलर के शब्द", addAlias: "शब्द सेव करें",
  noAliases: "अभी कोई शब्द सेव नहीं", noAliasesSub: "ऑर्डर में AI लाइन सुधारें, या यहाँ शब्द जोड़ें।", delete: "हटाएँ",
  loading: "लोड हो रहा है…", retry: "फिर कोशिश करें", errorTitle: "यह लोड नहीं हो सका", back: "वापस", dismiss: "बंद करें",
  offline: "आप ऑफ़लाइन हैं। ऑर्डर के लिए इंटरनेट चाहिए।", notAuthorised: "आपको इस पेज की अनुमति नहीं है।",
  gstUnspecified: "GST: क्लाइंट ब्रीफ़ में नहीं बताया गया। कोई GST नहीं जोड़ा गया।",
  add: "जोड़ें", update: "अपडेट", viewCart: "कार्ट देखें", changeProduct: "प्रोडक्ट बदलें", correct: "सुधारें", toReview: "जाँच बाकी", perCase: "/ पेटी", packs: "पैक", pricesPerCase: "भाव प्रति पेटी हैं",
};

export type TKey = keyof typeof en;
const dict = { en, hi } as const;

interface I18n { lang: Lang; setLang: (l: Lang) => void; t: (k: TKey, vars?: Record<string, string | number>) => string }
const Ctx = createContext<I18n | null>(null);

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Lang }) {
  const [lang, setLangState] = useState<Lang>(() => {
    if (initial) return initial;
    try { return localStorage.getItem("lang") === "hi" ? "hi" : "en"; } catch { return "en"; }
  });
  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try { localStorage.setItem("lang", l); } catch { /* ignore */ }
    document.documentElement.lang = l;
  }, []);
  const t = useCallback((k: TKey, vars?: Record<string, string | number>) => {
    let s: string = dict[lang][k] ?? en[k];
    if (vars) for (const [name, v] of Object.entries(vars)) s = s.replace(`{${name}}`, String(v));
    return s;
  }, [lang]);
  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useI18n(): I18n {
  const c = useContext(Ctx);
  if (!c) throw new Error("useI18n must be used inside I18nProvider");
  return c;
}
