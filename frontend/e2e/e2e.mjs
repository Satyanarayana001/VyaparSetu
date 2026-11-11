// Browser end-to-end test of the core build (real Chromium, real backend, real SQLite).
//
//   1. cd backend && python -m app.seed --reset && uvicorn app.main:app --port 8000    (backend serves the built UI)
//   2. cd frontend && npm run build
//   3. CHROME_PATH="/path/to/chrome" npm run e2e            (E2E_BASE defaults to http://localhost:8000)
//
// The run MUTATES the demo database (places/confirms/rejects orders): reset the seed afterwards.
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import puppeteer from "puppeteer-core";

const BASE = process.env.E2E_BASE || "http://localhost:8000";
let chromePath = process.env.CHROME_PATH, chromeArgs = (process.env.CHROME_ARGS || "--no-sandbox").split(" ");
if (!chromePath) {                                           // optional convenience for CI/sandboxes without Chrome
  try { const c = (await import("@sparticuz/chromium")).default; chromePath = await c.executablePath(); chromeArgs = [...c.args, "--no-sandbox"]; }
  catch { console.error("Set CHROME_PATH to a Chrome/Chromium binary."); process.exit(2); }
}
const browser = await puppeteer.launch({ executablePath: chromePath, args: chromeArgs, headless: "shell" });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let passed = 0; const failures = [];
async function step(name, fn) {
  try { await fn(); passed++; console.log(`  PASS  ${name}`); }
  catch (e) { failures.push(name); console.log(`  FAIL  ${name}\n        ${String(e.message).split("\n")[0]}`); }
}
const ok = (c, msg) => { if (!c) throw new Error(msg); };

async function newPage(w = 375, h = 800) {
  const p = await browser.newPage();
  await p.setViewport({ width: w, height: h, isMobile: w < 600, hasTouch: w < 600 });
  p.on("pageerror", (e) => failures.push("PAGEERROR " + e.message));
  return p;
}
const body = (p) => p.evaluate(() => document.body.innerText);
async function waitText(p, text, timeout = 8000) {
  try { await p.waitForFunction((t) => document.body.innerText.includes(t), { timeout }, text); }
  catch { throw new Error(`text not found: "${text}"\n--- page text ---\n${(await body(p)).slice(0, 400)}`); }
}
async function gone(p, text, timeout = 8000) { await p.waitForFunction((t) => !document.body.innerText.includes(t), { timeout }, text); }
async function click(p, text, sel = "button, a") {
  const found = await p.evaluate((text, sel) => {
    const el = [...document.querySelectorAll(sel)].find((e) => ((e.getAttribute("aria-label") || "") + " " + e.textContent).includes(text) && !e.disabled);
    if (!el) return false; el.scrollIntoView({ block: "center" }); el.click(); return true;
  }, text, sel);
  if (!found) throw new Error(`no enabled element: "${text}"`);
  await sleep(350);
}
async function clickExact(p, text) {
  const found = await p.evaluate((text) => { const el = [...document.querySelectorAll("button")].find((e) => e.textContent.trim() === text && !e.disabled); if (!el) return false; el.scrollIntoView({ block: "center" }); el.click(); return true; }, text);
  if (!found) throw new Error(`no enabled button exactly: "${text}"`); await sleep(350);
}
const isDisabled = (p, text) => p.evaluate((text) => { const el = [...document.querySelectorAll("button")].find((e) => e.textContent.includes(text)); return el ? el.disabled : null; }, text);
async function fill(p, sel, text) {            // select existing text via the DOM (triple-click is unreliable in headless), then type
  await p.click(sel); await p.$eval(sel, (el) => el.select()); if (text === "") await p.keyboard.press("Backspace"); else await p.keyboard.type(text); await sleep(200);
}
async function setQty(p, labelStart, n) { await fill(p, `input[aria-label^="${labelStart}"]`, String(n)); }
async function login(p, email, pw) {
  await p.goto(BASE + "/login", { waitUntil: "networkidle0" });
  await p.type("#email", email); await p.type("#password", pw);
  await p.click("form button"); await sleep(900);
}
async function api(p, method, url, data) {
  return p.evaluate(async (method, url, data) => {
    const r = await fetch("/api" + url, { method, headers: { "Content-Type": "application/json", Authorization: "Bearer " + sessionStorage.getItem("token") }, body: data ? JSON.stringify(data) : undefined });
    return { status: r.status, json: await r.json().catch(() => null) };
  }, method, url, data);
}
const SAMPLE = "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti";

// ------------------------------------------------------------------ retailer 1
console.log("\nRetailer: sign-in, catalogue, cart, schemes");
const r1 = await newPage();
await step("wrong password shows an error and stays on login", async () => {
  await login(r1, "retailer1@demo.test", "wrong-password"); await waitText(r1, "Email or password is incorrect"); ok(r1.url().includes("/login"), "left login");
});
await step("retailer signs in; home shows demo credit ₹56,500.00", async () => {
  await fill(r1, "#password", "Retailer@123"); await r1.click("form button"); await sleep(900);
  await waitText(r1, "₹56,500.00"); await waitText(r1, "Demo data"); await waitText(r1, "ORD-000001");
});
await step("catalogue shows 3 products with exact case prices, stock and schemes", async () => {
  await r1.goto(BASE + "/shop", { waitUntil: "networkidle0" });
  for (const t of ["Glucose biscuit 75 g", "₹777.60", "340 cases", "Buy 10, get 1 free", "Detergent powder 1 kg", "₹2,030.00", "85 cases", "3% off on 5+ cases", "Tea leaf 250 g", "₹4,720.00"]) await waitText(r1, t);
  await waitText(r1, "GST: not specified");
});
await step("tea is clearly out of stock and cannot be added", async () => {
  await waitText(r1, "Out of stock");
  const adds = await r1.$$eval("button[aria-label^='Add']", (b) => b.map((x) => x.getAttribute("aria-label")));
  ok(adds.length === 2 && !adds.some((a) => a.includes("Tea")), "tea has an Add button: " + adds.join("|"));
});
await step("search narrows the catalogue; empty search shows an empty state", async () => {
  await fill(r1, "input[type=search]", "tea"); await sleep(900); await gone(r1, "Detergent powder 1 kg");
  await fill(r1, "input[type=search]", "zzz"); await sleep(900); await waitText(r1, "No products match");
  await fill(r1, "input[type=search]", ""); await sleep(900); await waitText(r1, "Glucose biscuit 75 g");
});
await step("biscuit x10 + detergent x5: backend applies 1 free case and 3% discount", async () => {
  await setQty(r1, "Quantity – Glucose", 10); await click(r1, "Add to cart – Glucose");
  await setQty(r1, "Quantity – Detergent", 5); await click(r1, "Add to cart – Detergent");
  await waitText(r1, "₹17,621.50");                     // sticky cart bar total is the server's
  await click(r1, "View cart", "a"); await waitText(r1, "Your cart");
  for (const t of ["+ 1 cases free", "₹304.50", "₹9,845.50", "₹7,776.00", "₹17,621.50"]) await waitText(r1, t).catch(async () => { if (t.startsWith("+ 1")) await waitText(r1, "1 cases free"); else throw new Error("missing " + t); });
});
await step("place order: confirmation shown, stock reserved, credit reduced", async () => {
  await click(r1, "Place order"); await waitText(r1, "Order placed"); await waitText(r1, "Waiting for review"); await waitText(r1, "₹17,621.50");
  const cat = (await api(r1, "GET", "/catalogue")).json.products;
  ok(cat.find((p) => p.sku === "SKU-BS-075").stock_cases === 329 && cat.find((p) => p.sku === "SKU-DT-1KG").stock_cases === 80, "stock not reserved");
  await r1.goto(BASE + "/", { waitUntil: "networkidle0" }); await waitText(r1, "₹38,878.50");
});
await step("repeat last order: tea is flagged out of stock and blocks placing until removed", async () => {
  await click(r1, "Repeat last order"); await waitText(r1, "Your cart"); await waitText(r1, "Loaded from your order"); await waitText(r1, "out of stock");
  ok(await isDisabled(r1, "Place order"), "Place order should be disabled");
  await click(r1, "Remove Tea"); await sleep(900); ok(!(await isDisabled(r1, "Place order")), "Place order should be enabled after removing tea");
  await click(r1, "Clear cart");
});

console.log("\nRetailer: AI text order capture (sample message from the brief)");
await step("sample message: 3 lines, original words, tea flagged, confirm blocked", async () => {
  await r1.goto(BASE + "/message", { waitUntil: "networkidle0" });
  await waitText(r1, "Basic reader (no AI model connected)");
  await r1.type("textarea", SAMPLE); await click(r1, "Read my order"); await waitText(r1, "Check your order");
  for (const t of ["5 peti biscuit chhota", "2 peti washing powder 1 kilo", "chai patti 250 wala 1 peti", "Glucose biscuit 75 g", "Detergent powder 1 kg", "Tea leaf 250 g", "Confidence"]) await waitText(r1, t);
  await waitText(r1, "Tea leaf 250 g is out of stock"); ok(await isDisabled(r1, "Confirm order"), "confirm should be blocked");
});
await step("removing the out-of-stock line unlocks confirmation; total excludes tea (₹7,948.00)", async () => {
  const removeBtns = await r1.$$("button"); // third 'Remove line'
  const idx = await r1.evaluate(() => [...document.querySelectorAll("button")].filter((b) => b.textContent.includes("Remove line")).length);
  ok(idx === 3, "expected 3 remove buttons, got " + idx);
  await r1.evaluate(() => [...document.querySelectorAll("button")].filter((b) => b.textContent.includes("Remove line"))[2].click()); await sleep(900);
  ok(!(await isDisabled(r1, "Confirm order")), "confirm should be enabled"); await waitText(r1, "₹7,948.00");
});
await step("human confirms: AI order is placed with the original message stored", async () => {
  await click(r1, "Confirm order"); await waitText(r1, "Order placed"); await waitText(r1, "Placed from a message"); await waitText(r1, "bhaiya 5 peti biscuit chhota");
  await waitText(r1, "₹7,948.00");
});
await step("unclear units are asked about, not guessed", async () => {
  await r1.goto(BASE + "/message", { waitUntil: "networkidle0" });
  await r1.type("textarea", "biscuit 5, 2 peti powder, 3 packet chai"); await click(r1, "Read my order"); await waitText(r1, "Check your order");
  await waitText(r1, "Is 5 cases or packs?"); await waitText(r1, "Use 5 cases"); await waitText(r1, "packs. Orders are placed in whole cases");
  ok(await isDisabled(r1, "Confirm order"), "confirm must stay blocked while units/products are unclear");
  await click(r1, "Use 5 cases"); await waitText(r1, "needs your attention").catch(() => {}); ok(await isDisabled(r1, "Confirm order"), "other lines still unresolved");
});
await step("uncertain product: person must choose (alternatives shown)", async () => {
  await waitText(r1, "Not sure about this match"); await waitText(r1, "Choose the product").catch(() => {});
  const choices = await r1.evaluate(() => [...document.querySelectorAll("button[aria-pressed]")].length); ok(choices >= 3, "alternatives not shown: " + choices);
});
await step("language toggle switches the interface to Hindi and back", async () => {
  await click(r1, "हिंदी"); await waitText(r1, "होम"); await waitText(r1, "कार्ट"); await click(r1, "English"); await waitText(r1, "Home");
});

// ------------------------------------------------------------------ retailer 2 (credit)
console.log("\nCredit hold and access control");
const r2 = await newPage();
await step("retailer 2: order above available credit is blocked (backend rule shown in UI)", async () => {
  await login(r2, "retailer2@demo.test", "Retailer@123"); await waitText(r2, "₹6,000.00");
  await r2.goto(BASE + "/shop", { waitUntil: "networkidle0" }); await setQty(r2, "Quantity – Detergent", 3); await click(r2, "Add to cart – Detergent");
  await r2.goto(BASE + "/cart", { waitUntil: "networkidle0" }); await waitText(r2, "above your available credit"); ok(await isDisabled(r2, "Place order"), "should be disabled");
  const direct = await api(r2, "POST", "/orders", { items: [{ sku: "SKU-DT-1KG", quantity_cases: 3 }], idempotency_key: "e2e-credit-0001" });
  ok(direct.status === 422 && direct.json.error.code === "CREDIT_LIMIT_EXCEEDED", "backend must refuse too: " + direct.status);
});
await step("retailers cannot see each other's orders or reach the desk", async () => {
  const mine = (await api(r2, "GET", "/orders")).json; ok(mine.every((o) => o.retailer.code === "R002"), "foreign orders visible");
  ok((await api(r2, "GET", "/orders/3")).status === 404, "retailer 2 could read retailer 1's order");
  ok((await api(r2, "GET", "/desk/orders")).status === 403, "retailer reached desk API");
  await r2.goto(BASE + "/desk", { waitUntil: "networkidle0" }); ok(!r2.url().includes("/desk"), "desk page reachable by retailer");
});

// ------------------------------------------------------------------ order desk
console.log("\nOrder desk: review, correct, alias, status, Tally export");
await step("retailer sends an unknown phrase and picks the product themselves", async () => {
  await r1.goto(BASE + "/message", { waitUntil: "networkidle0" });
  await r1.type("textarea", "2 peti mithai"); await click(r1, "Read my order"); await waitText(r1, "Check your order");
  await click(r1, "Glucose biscuit 75 g", "button[aria-pressed]"); await sleep(900); await click(r1, "Confirm order"); await waitText(r1, "Order placed");
});
const desk = await newPage(1280, 900);
await step("desk signs in; queue shows incoming orders with counts", async () => {
  await login(desk, "desk@demo.test", "Desk@12345"); await waitText(desk, "To review"); await waitText(desk, "Sharma Kirana Store (demo)");
  const n = await desk.evaluate(() => [...document.querySelectorAll("a[href^='/desk/orders/']")].length); ok(n === 3, "expected 3 placed orders, got " + n);
});
await step("desk opens the AI order: original message, retailer, credit visible", async () => {
  await desk.goto(BASE + "/desk/orders/5", { waitUntil: "networkidle0" });
  for (const t of ["ORD-000005", "Sharma Kirana Store (demo)", "Available credit", "2 peti mithai", "Basic reader", "Glucose biscuit 75 g"]) await waitText(desk, t);
});
await step("desk corrects the product mapping and saves a retailer-specific alias", async () => {
  await click(desk, "Correct"); await desk.select("select", "SKU-DT-1KG"); await waitText(desk, "Remember these words for this retailer");
  await click(desk, "Save change"); await waitText(desk, "Detergent powder 1 kg"); await waitText(desk, "₹4,060.00");
  await desk.goto(BASE + "/desk/aliases", { waitUntil: "networkidle0" }); await sleep(500); await desk.select("select", "1"); await sleep(700); await waitText(desk, "“mithai”"); await waitText(desk, "Detergent powder 1 kg");
});
await step("saved alias is used for that retailer's next message (and not for retailer 2)", async () => {
  await r1.goto(BASE + "/message", { waitUntil: "networkidle0" }); await r1.type("textarea", "1 peti mithai"); await click(r1, "Read my order");
  await waitText(r1, "Your saved word"); await waitText(r1, "Detergent powder 1 kg");
  const other = await api(r2, "POST", "/ai/parse", { message: "1 peti mithai" }); ok(other.json.lines[0].sku === null, "alias leaked to another retailer");
});
await step("desk confirms two orders and rejects one with a reason (stock returned)", async () => {
  await desk.goto(BASE + "/desk/orders/3", { waitUntil: "networkidle0" }); await click(desk, "Confirm order"); await waitText(desk, "Confirmed");
  await desk.goto(BASE + "/desk/orders/4", { waitUntil: "networkidle0" }); await click(desk, "Confirm order"); await waitText(desk, "Confirmed");
  await desk.goto(BASE + "/desk/orders/5", { waitUntil: "networkidle0" }); await clickExact(desk, "Reject");
  ok(await isDisabled(desk, "Reject order"), "reject needs a reason"); await desk.type("#reason", "Customer asked to cancel"); await click(desk, "Reject order"); await waitText(desk, "Rejected");
  const cat = (await api(r1, "GET", "/catalogue")).json.products; ok(cat.find((p) => p.sku === "SKU-DT-1KG").stock_cases === 80 - 2, "rejected stock not returned (detergent)");
});
await step("Tally export: confirmed orders pre-selected, CSV downloads with correct data", async () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "e2e-dl-"));
  await (await desk.createCDPSession()).send("Browser.setDownloadBehavior", { behavior: "allow", downloadPath: dir });
  await desk.goto(BASE + "/desk/export", { waitUntil: "networkidle0" }); await waitText(desk, "ORD-000003"); await waitText(desk, "ORD-000004");
  ok(!(await body(desk)).includes("ORD-000005"), "rejected order listed for export");
  await click(desk, "Download CSV"); await waitText(desk, "Downloaded 2 order(s)");
  await sleep(800); const f = fs.readdirSync(dir).find((n) => n.endsWith(".csv")); ok(f, "no CSV file downloaded");
  const csv = fs.readFileSync(path.join(dir, f), "utf8").replace(/^\uFEFF/, "");
  const lines = csv.trim().split(/\r?\n/);
  ok(lines[0].startsWith("Order ID,Order Date,Retailer Code,Retailer,SKU,Product Name,Quantity (Cases),Free Quantity (Cases)"), "bad header");
  ok(lines.some((l) => l.includes("ORD-000003") && l.includes("SKU-BS-075") && l.includes(",10,1,96,8.10,777.60,0.00,7776.00,confirmed")), "biscuit row wrong:\n" + csv);
  ok(lines.some((l) => l.includes("ORD-000003") && l.includes("SKU-DT-1KG") && l.includes(",5,0,20,101.50,2030.00,304.50,9845.50,confirmed")), "detergent row wrong:\n" + csv);
  ok(lines.length === 1 + 2 + 2, "expected 4 data rows, got " + (lines.length - 1));
  await waitText(desk, "No confirmed orders to export");
});
await step("desk status flow: confirmed order can be dispatched", async () => {
  await desk.goto(BASE + "/desk/orders/3", { waitUntil: "networkidle0" }); await click(desk, "Mark dispatched"); await waitText(desk, "Dispatched");
});

await browser.close();
console.log(`\n${passed} passed, ${failures.length} failed`);
if (failures.length) { console.log("FAILED: " + failures.join("; ")); process.exit(1); }
