from sqlalchemy import select

from app import models
from app.security import hash_password
from conftest import BS, DT, SAMPLE, _login, place


def test_login_success_and_me(client, r1):
    me = client.get("/api/auth/me", headers=r1).json()
    assert me["role"] == "retailer" and me["retailer"]["code"] == "R001"


def test_wrong_password_and_unknown_user_look_identical(client):
    a = client.post("/api/auth/login", json={"email": "retailer1@demo.test", "password": "nope"})
    b = client.post("/api/auth/login", json={"email": "ghost@demo.test", "password": "nope"})
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json()


def test_password_is_hashed_not_stored_in_plain_text(db):
    u = db.scalar(select(models.User).where(models.User.email == "desk@demo.test"))
    assert u.password_hash.startswith("$2") and "Desk@12345" not in u.password_hash


def test_login_throttle_after_repeated_failures(client):
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": "desk@demo.test", "password": "bad"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "desk@demo.test", "password": "Desk@12345"}).status_code == 429


def test_requests_without_or_with_bad_token_are_rejected(client):
    assert client.get("/api/catalogue").status_code == 401
    assert client.get("/api/catalogue", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_role_separation(client, r1, desk, salesman):
    assert client.get("/api/desk/orders", headers=r1).status_code == 403
    assert client.get("/api/desk/retailers", headers=r1).status_code == 403
    assert client.post("/api/desk/export/tally", json={}, headers=r1).status_code == 403
    assert client.get("/api/catalogue", headers=desk).status_code == 403
    assert client.get("/api/desk/orders", headers=salesman).status_code == 403
    assert client.post("/api/orders/quote", json={"items": []}, headers=desk).status_code == 403


def test_retailer_cannot_read_another_retailers_order(client, r1, r2):
    oid = place(client, r1, [(BS, 1)]).json()["order"]["id"]
    assert client.get(f"/api/orders/{oid}", headers=r1).status_code == 200
    assert client.get(f"/api/orders/{oid}", headers=r2).status_code == 404
    assert all(o["retailer"]["code"] == "R002" for o in client.get("/api/orders", headers=r2).json())
    assert oid not in [o["id"] for o in client.get("/api/orders", headers=r2).json()]


def test_retailer_prices_and_credit_are_isolated(client, db, r1, r2):
    r1_id = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R001"))
    bs = db.scalar(select(models.Product).where(models.Product.sku == BS))
    db.add(models.RetailerPrice(retailer_id=r1_id, product_id=bs.id, unit_price_paise=700))   # special price for R1 only
    db.commit()
    p1 = {p["sku"]: p for p in client.get("/api/catalogue", headers=r1).json()["products"]}
    p2 = {p["sku"]: p for p in client.get("/api/catalogue", headers=r2).json()["products"]}
    assert p1[BS]["unit_price_paise"] == 700 and p2[BS]["unit_price_paise"] == 810
    assert client.get("/api/retailer/me", headers=r1).json()["credit"]["credit_limit_paise"] == 75_000_00
    assert client.get("/api/retailer/me", headers=r2).json()["credit"]["credit_limit_paise"] == 30_000_00


def test_retailer_cannot_use_retailer_scoped_catalogue_of_another(client, db, r1, r2):
    r1_id = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R001"))
    r2_id = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R002"))
    assert client.get(f"/api/retailers/{r1_id}/catalogue", headers=r1).status_code == 200
    assert client.get(f"/api/retailers/{r1_id}/catalogue", headers=r2).status_code == 404
    assert client.get(f"/api/retailers/{r2_id}/catalogue", headers=r1).status_code == 404


def test_salesman_only_sees_assigned_retailers(client, db, salesman, desk):
    other = models.Retailer(code="R999", name="Unassigned Store (demo)", credit_limit_paise=1000)
    db.add(other)
    db.commit()
    mine = client.get("/api/salesman/retailers", headers=salesman).json()
    assert {r["code"] for r in mine} == {"R001", "R002"}
    assert client.get(f"/api/retailers/{other.id}/catalogue", headers=salesman).status_code == 404
    assert client.get(f"/api/retailers/{other.id}/catalogue", headers=desk).status_code == 200  # desk may access
    assert client.get(f"/api/retailers/{mine[0]['id']}/catalogue", headers=salesman).status_code == 200


def test_aliases_are_per_retailer(client, db, r1, r2, desk):
    r1_id = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R001"))
    assert client.post(f"/api/desk/retailers/{r1_id}/aliases", json={"alias_text": "mithi goli", "sku": BS}, headers=desk).status_code == 201
    a = client.post("/api/ai/parse", json={"message": "2 peti mithi goli"}, headers=r1).json()["lines"][0]
    b = client.post("/api/ai/parse", json={"message": "2 peti mithi goli"}, headers=r2).json()["lines"][0]
    assert a["sku"] == BS and a["match_source"] == "alias"
    assert b["sku"] is None                                      # R2 never learns R1's alias


def test_ai_review_of_one_retailer_cannot_be_used_by_another(client, r1, r2):
    pid = client.post("/api/ai/parse", json={"message": SAMPLE}, headers=r1).json()["parse_id"]
    r = place(client, r2, [(BS, 1)], source="ai", ai_parse_id=pid)
    assert r.status_code == 422 and r.json()["error"]["code"] == "INVALID_AI_PARSE"


def test_repeat_reference_to_other_retailers_order_is_rejected(client, r1, r2):
    oid = place(client, r1, [(BS, 1)]).json()["order"]["id"]
    r = place(client, r2, [(BS, 1)], source="repeat", repeat_of_order_id=oid)
    assert r.status_code == 422
