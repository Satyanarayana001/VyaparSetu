from sqlalchemy import select

from app import models
from conftest import BS, DT, TE, place


def stock(db, sku):
    db.expire_all()
    return db.scalar(select(models.Product.stock_cases).where(models.Product.sku == sku))


def test_quote_is_computed_by_backend(client, r1):
    q = client.post("/api/orders/quote", headers=r1,
                    json={"items": [{"sku": BS, "quantity_cases": 10}, {"sku": DT, "quantity_cases": 5}]}).json()
    by = {l["sku"]: l for l in q["lines"]}
    assert by[BS]["free_cases"] == 1 and by[BS]["line_total_paise"] == 777_600
    assert by[DT]["discount_paise"] == 30_450 and by[DT]["line_total_paise"] == 984_550
    assert q["subtotal_paise"] == 777_600 + 1_015_000 and q["discount_paise"] == 30_450
    assert q["total_paise"] == 777_600 + 984_550 and q["can_order"] is True


def test_quote_reports_issues_without_failing(client, r1):
    q = client.post("/api/orders/quote", headers=r1, json={"items": [{"sku": TE, "quantity_cases": 1}, {"sku": "NOPE", "quantity_cases": 1}]}).json()
    codes = {l["sku"]: l["issues"][0]["code"] for l in q["lines"]}
    assert codes == {TE: "OUT_OF_STOCK", "NOPE": "UNKNOWN_PRODUCT"} and q["can_order"] is False


def test_create_order_persists_snapshots_and_reserves_stock(client, db, r1):
    r = place(client, r1, [(BS, 10), (DT, 5)])
    assert r.status_code == 201
    o = r.json()["order"]
    assert o["status"] == "placed" and o["order_number"].startswith("ORD-")
    bs = next(i for i in o["items"] if i["sku"] == BS)
    assert (bs["quantity_cases"], bs["free_cases"], bs["unit_price_paise"], bs["case_price_paise"], bs["line_total_paise"]) == (10, 1, 810, 77760, 777_600)
    assert "Buy 10 cases" in bs["scheme_applied"]
    dt = next(i for i in o["items"] if i["sku"] == DT)
    assert dt["discount_paise"] == 30_450 and dt["scheme_applied"].startswith("3%")
    assert o["total_paise"] == sum(i["line_total_paise"] for i in o["items"]) == 777_600 + 984_550
    assert stock(db, BS) == 340 - 11 and stock(db, DT) == 85 - 5          # free case also leaves the warehouse


def test_client_supplied_prices_and_totals_are_ignored(client, r1):
    body = {"items": [{"sku": BS, "quantity_cases": 1, "price": 1, "unit_price_paise": 1, "line_total_paise": 1}],
            "total_paise": 1, "idempotency_key": "tamper-test-0001"}
    o = client.post("/api/orders", json=body, headers=r1).json()["order"]
    assert o["total_paise"] == 77_760


def test_duplicate_confirmation_is_idempotent(client, db, r1):
    body = {"items": [{"sku": BS, "quantity_cases": 2}], "idempotency_key": "double-click-0001"}
    a = client.post("/api/orders", json=body, headers=r1)
    b = client.post("/api/orders", json=body, headers=r1)
    assert a.status_code == 201 and b.status_code == 200
    assert a.json()["order"]["id"] == b.json()["order"]["id"] and b.json()["duplicate"] is True
    assert stock(db, BS) == 338                                      # reserved once
    assert len([o for o in client.get("/api/orders", headers=r1).json() if o["source"] == "manual" and o["total_paise"] == 155_520]) == 1


def test_out_of_stock_and_unknown_products_cannot_be_ordered(client, r1):
    r = place(client, r1, [(TE, 1)])
    assert r.status_code == 422 and r.json()["error"]["details"][0]["code"] == "OUT_OF_STOCK"
    assert place(client, r1, [("SKU-NOPE", 1)]).json()["error"]["details"][0]["code"] == "UNKNOWN_PRODUCT"


def test_cannot_order_more_than_stock_including_free_cases(client, db, r1):
    assert place(client, r1, [(DT, 86)]).json()["error"]["details"][0]["code"] == "INSUFFICIENT_STOCK"
    # 310 + 31 free = 341 > 340 in stock, but the same order of 309 (+30 free = 339) is fine
    assert place(client, r1, [(BS, 310)]).status_code == 422
    # credit would block this one, so check stock rules through the quote endpoint instead
    q = client.post("/api/orders/quote", headers=r1, json={"items": [{"sku": BS, "quantity_cases": 309}]}).json()
    assert q["lines"][0]["issues"] == [] and q["lines"][0]["free_cases"] == 30
    q = client.post("/api/orders/quote", headers=r1, json={"items": [{"sku": BS, "quantity_cases": 310}]}).json()
    assert q["lines"][0]["issues"][0]["code"] == "INSUFFICIENT_STOCK"


def test_invalid_quantities_are_rejected(client, r1):
    for bad in (0, -5, 10_001, 2.5, "3", None):
        body = {"items": [{"sku": BS, "quantity_cases": bad}], "idempotency_key": "bad-qty-key-01"}
        assert client.post("/api/orders", json=body, headers=r1).status_code == 422, bad
    assert client.post("/api/orders", json={"items": [], "idempotency_key": "empty-order-01"}, headers=r1).status_code == 422


def test_same_sku_on_two_lines_is_combined_for_schemes(client, r1):
    o = place(client, r1, [(BS, 6), (BS, 4)]).json()["order"]
    assert len(o["items"]) == 1 and o["items"][0]["quantity_cases"] == 10 and o["items"][0]["free_cases"] == 1


def test_credit_hold_is_enforced_by_backend(client, r2):
    # R2: limit 30,000 - outstanding 24,000 = 6,000 available. 3 cases of detergent = 6,090.
    r = place(client, r2, [(DT, 3)])
    assert r.status_code == 422 and r.json()["error"]["code"] == "CREDIT_LIMIT_EXCEEDED"
    assert place(client, r2, [(DT, 2)]).status_code == 201                     # 4,060 fits
    credit = client.get("/api/retailer/me", headers=r2).json()["credit"]
    assert credit["open_orders_paise"] == 406_000 and credit["available_paise"] == 600_000 - 406_000
    assert place(client, r2, [(DT, 1)]).status_code == 422                     # 2,030 > 1,940 left


def test_repeat_last_order_flow(client, r1):
    rep = client.get("/api/orders/last-repeatable", headers=r1).json()
    assert {(i["sku"], i["quantity_cases"]) for i in rep["items"]} == {(BS, 10), (DT, 5), (TE, 2)}
    q = client.post("/api/orders/quote", headers=r1, json={"items": rep["items"]}).json()
    assert q["can_order"] is False                                              # tea is out of stock now
    items = [(i["sku"], i["quantity_cases"] + (1 if i["sku"] == DT else 0)) for i in rep["items"] if i["sku"] != TE]
    r = place(client, r1, items, source="repeat", repeat_of_order_id=rep["order_id"])
    assert r.status_code == 201 and r.json()["order"]["source"] == "repeat"
    assert {i["sku"]: i["quantity_cases"] for i in r.json()["order"]["items"]} == {BS: 10, DT: 6}


def test_repeat_without_history_is_a_clear_404(client, db, r2):
    db.query(models.OrderItem).delete()
    db.query(models.Order).delete()
    db.commit()
    r = client.get("/api/orders/last-repeatable", headers=r2)
    assert r.status_code == 404 and r.json()["error"]["code"] == "NO_PREVIOUS_ORDER"


def test_errors_never_leak_internals(client, r1):
    r = client.post("/api/orders", json={"items": "oops"}, headers=r1)
    assert r.status_code == 422 and "Traceback" not in r.text and r.json()["error"]["code"] == "VALIDATION_ERROR"
