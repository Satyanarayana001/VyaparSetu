import csv
import io

from sqlalchemy import select

from app import models
from conftest import BS, DT, SAMPLE, TE, place


def stock(db, sku):
    db.expire_all()
    return db.scalar(select(models.Product.stock_cases).where(models.Product.sku == sku))


def ai_order(client, headers, message, key):
    p = client.post("/api/ai/parse", json={"message": message}, headers=headers).json()
    ok = [l for l in p["lines"] if l["validation_status"] == "ok"]
    body = {"items": [{"sku": l["sku"], "quantity_cases": l["quantity"], "ai_line_id": l["line_id"]} for l in ok],
            "source": "ai", "ai_parse_id": p["parse_id"], "idempotency_key": key}
    r = client.post("/api/orders", json=body, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["order"]


def test_queue_search_and_detail(client, r1, r2, desk):
    o1 = place(client, r1, [(BS, 1)]).json()["order"]
    place(client, r2, [(DT, 1)])
    q = client.get("/api/desk/orders", headers=desk).json()
    assert q["counts"]["placed"] == 2 and q["counts"]["dispatched"] == 2           # 2 new + 2 seeded history orders
    assert len(q["orders"]) == 4
    placed = client.get("/api/desk/orders", params={"status": "placed"}, headers=desk).json()["orders"]
    assert len(placed) == 2
    assert [o["retailer"]["code"] for o in client.get("/api/desk/orders", params={"q": "narmada"}, headers=desk).json()["orders"]] == ["R002", "R002"]
    d = client.get(f"/api/desk/orders/{o1['id']}", headers=desk).json()
    assert d["retailer_detail"]["code"] == "R001" and "credit" in d["retailer_detail"]


def test_status_workflow_and_invalid_transitions(client, db, r1, desk):
    oid = place(client, r1, [(BS, 2)]).json()["order"]["id"]
    s = lambda status, reason=None: client.post(f"/api/desk/orders/{oid}/status", json={"status": status, "reason": reason}, headers=desk)
    assert s("dispatched").status_code == 409                       # can't skip confirmation
    assert s("confirmed").json()["status"] == "confirmed"
    assert s("placed").status_code == 409 and s("placed").json()["error"]["code"] == "INVALID_TRANSITION"
    assert s("dispatched").json()["status"] == "dispatched"
    assert s("rejected", "changed mind").status_code == 409         # terminal


def test_rejecting_returns_stock_and_requires_reason(client, db, r1, desk):
    oid = place(client, r1, [(BS, 10)]).json()["order"]["id"]
    assert stock(db, BS) == 329
    assert client.post(f"/api/desk/orders/{oid}/status", json={"status": "rejected"}, headers=desk).json()["error"]["code"] == "REASON_REQUIRED"
    r = client.post(f"/api/desk/orders/{oid}/status", json={"status": "rejected", "reason": "Out of credit"}, headers=desk).json()
    assert r["status"] == "rejected" and r["rejection_reason"] == "Out of credit"
    assert stock(db, BS) == 340
    # retailer can see the rejection and the reason
    assert client.get(f"/api/orders/{oid}", headers=r1).json()["rejection_reason"] == "Out of credit"


def test_correcting_ai_mapping_recalculates_and_saves_retailer_alias(client, db, r1, r2, desk):
    o = ai_order(client, r1, "5 peti chhota biscuit", "desk-correct-0001")
    item = o["items"][0]
    assert item["sku"] == BS and stock(db, BS) == 335
    r = client.patch(f"/api/desk/orders/{o['id']}/items/{item['id']}", json={"sku": DT}, headers=desk)
    assert r.status_code == 200, r.text
    fixed = r.json()
    li = fixed["items"][0]
    assert li["sku"] == DT and li["was_corrected"] is True and li["ai_matched_sku"] == BS
    assert (li["quantity_cases"], li["discount_paise"], li["line_total_paise"]) == (5, 30_450, 984_550)   # 3% scheme now applies
    assert fixed["total_paise"] == 984_550
    assert stock(db, BS) == 340 and stock(db, DT) == 80                                                   # stock moved with the line
    rid = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R001"))
    aliases = client.get(f"/api/desk/retailers/{rid}/aliases", headers=desk).json()
    assert [(a["alias_text"], a["sku"]) for a in aliases] == [("chhota biscuit", DT)]
    # future orders from this retailer use the alias; other retailers are unaffected
    assert client.post("/api/ai/parse", json={"message": "1 peti chhota biscuit"}, headers=r1).json()["lines"][0]["sku"] == DT
    assert client.post("/api/ai/parse", json={"message": "1 peti chhota biscuit"}, headers=r2).json()["lines"][0]["sku"] == BS


def test_correction_can_skip_alias_and_change_quantity(client, db, r1, desk):
    o = ai_order(client, r1, "2 peti biscuit", "desk-correct-0002")
    it = o["items"][0]
    r = client.patch(f"/api/desk/orders/{o['id']}/items/{it['id']}", json={"quantity_cases": 10}, headers=desk).json()
    assert r["items"][0]["quantity_cases"] == 10 and r["items"][0]["free_cases"] == 1 and stock(db, BS) == 340 - 11
    r = client.patch(f"/api/desk/orders/{o['id']}/items/{it['id']}", json={"sku": TE, "save_alias": False}, headers=desk)
    assert r.status_code == 422 and r.json()["error"]["code"] == "OUT_OF_STOCK"
    assert stock(db, BS) == 340 - 11 and stock(db, TE) == 0                                              # failed correction changed nothing
    assert client.get(f"/api/desk/orders/{o['id']}", headers=desk).json()["items"][0]["sku"] == BS


def test_correction_rules(client, r1, desk):
    o = place(client, r1, [(BS, 2), (DT, 1)]).json()["order"]
    a, b = o["items"]
    url = lambda i: f"/api/desk/orders/{o['id']}/items/{i['id']}"
    assert client.patch(url(a), json={"sku": DT}, headers=desk).json()["error"]["code"] == "DUPLICATE_LINE"
    assert client.patch(url(a), json={"quantity_cases": 0}, headers=desk).status_code == 422
    assert client.patch(url(a), json={"sku": "NOPE"}, headers=desk).json()["error"]["code"] == "UNKNOWN_PRODUCT"
    client.post(f"/api/desk/orders/{o['id']}/status", json={"status": "confirmed"}, headers=desk)
    assert client.patch(url(a), json={"quantity_cases": 3}, headers=desk).json()["error"]["code"] == "ORDER_LOCKED"


def test_alias_management(client, db, desk, r1):
    rid = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R001"))
    a = client.post(f"/api/desk/retailers/{rid}/aliases", json={"alias_text": "  Hari  Patti ", "sku": TE}, headers=desk).json()
    assert a["alias_text"] == "hari patti"
    again = client.post(f"/api/desk/retailers/{rid}/aliases", json={"alias_text": "hari patti", "sku": DT}, headers=desk).json()
    assert again["id"] == a["id"] and again["sku"] == DT                                                 # upsert, not duplicate
    assert client.post(f"/api/desk/retailers/{rid}/aliases", json={"alias_text": "  ", "sku": DT}, headers=desk).json()["error"]["code"] == "INVALID_ALIAS"
    assert client.get(f"/api/desk/retailers/{rid}/aliases", headers=r1).status_code == 403
    assert client.delete(f"/api/desk/retailers/{rid}/aliases/{a['id']}", headers=desk).status_code == 204
    assert client.get(f"/api/desk/retailers/{rid}/aliases", headers=desk).json() == []


def test_csv_export_contains_only_confirmed_orders_with_required_columns(client, r1, r2, desk):
    o1 = place(client, r1, [(BS, 10), (DT, 5)]).json()["order"]
    o2 = place(client, r2, [(DT, 1)]).json()["order"]
    place(client, r1, [(BS, 1)])                                                                          # stays "placed"
    assert client.post("/api/desk/export/tally", json={}, headers=desk).json()["error"]["code"] == "NOTHING_TO_EXPORT"
    client.post(f"/api/desk/orders/{o1['id']}/status", json={"status": "confirmed"}, headers=desk)
    client.post(f"/api/desk/orders/{o2['id']}/status", json={"status": "rejected", "reason": "No stock"}, headers=desk)
    r = client.post("/api/desk/export/tally", json={}, headers=desk)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"] and r.headers["x-exported-orders"] == "1"
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert {"Order ID", "Retailer", "SKU", "Product Name", "Quantity (Cases)", "Free Quantity (Cases)",
            "Price per Case (INR)", "Discount (INR)", "Total (INR)", "Order Status"} <= set(rows[0])
    assert len(rows) == 2 and {r["Order ID"] for r in rows} == {o1["order_number"]}
    bs = next(x for x in rows if x["SKU"] == BS)
    assert (bs["Quantity (Cases)"], bs["Free Quantity (Cases)"], bs["Price per Case (INR)"], bs["Discount (INR)"], bs["Total (INR)"], bs["Order Status"]) == ("10", "1", "777.60", "0.00", "7776.00", "confirmed")
    dt = next(x for x in rows if x["SKU"] == DT)
    assert (dt["Discount (INR)"], dt["Total (INR)"], dt["Retailer"]) == ("304.50", "9845.50", "Sharma Kirana Store (demo)")


def test_export_marks_orders_and_supports_selection(client, r1, desk):
    ids = [place(client, r1, [(BS, 1)]).json()["order"]["id"] for _ in range(2)]
    for i in ids:
        client.post(f"/api/desk/orders/{i}/status", json={"status": "confirmed"}, headers=desk)
    assert client.post("/api/desk/export/tally", json={"order_ids": [ids[0]]}, headers=desk).headers["x-exported-orders"] == "1"
    listed = {o["id"]: o["exported_at"] for o in client.get("/api/desk/orders", headers=desk).json()["orders"]}
    assert listed[ids[0]] and listed[ids[1]] is None
    assert client.post("/api/desk/export/tally", json={}, headers=desk).headers["x-exported-orders"] == "1"          # only the not-yet-exported one
    assert client.post("/api/desk/export/tally", json={}, headers=desk).status_code == 422
    assert client.post("/api/desk/export/tally", json={"include_exported": True}, headers=desk).headers["x-exported-orders"] == "2"
    assert client.post("/api/desk/export/tally", json={"order_ids": [ids[0], 99999]}, headers=desk).status_code == 422


def test_export_refuses_unconfirmed_orders_and_neutralises_formulas(client, db, r1, desk):
    oid = place(client, r1, [(BS, 1)]).json()["order"]["id"]
    assert client.post("/api/desk/export/tally", json={"order_ids": [oid]}, headers=desk).json()["error"]["code"] == "NOT_EXPORTABLE"
    client.post(f"/api/desk/orders/{oid}/status", json={"status": "confirmed"}, headers=desk)
    db.query(models.Retailer).filter_by(code="R001").update({"name": "=HYPERLINK(\"http://evil\")"})
    db.commit()
    text = client.post("/api/desk/export/tally", json={}, headers=desk).content.decode("utf-8-sig")
    row = list(csv.DictReader(io.StringIO(text)))[0]
    assert row["Retailer"].startswith("'=")
