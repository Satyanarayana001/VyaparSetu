from types import SimpleNamespace as S

import pytest

from app.services import pricing

FREE = S(type="free_goods", description="Buy 10 cases, get 1 free", buy_qty=10, free_qty=1, min_cases=0, percent_bp=0)
PCT = S(type="percent_discount", description="3% discount on 5 or more cases", buy_qty=0, free_qty=0, min_cases=5, percent_bp=300)


@pytest.mark.parametrize("qty,free", [(1, 0), (9, 0), (10, 1), (11, 1), (19, 1), (20, 2), (35, 3), (100, 10)])
def test_biscuit_free_cases_use_completed_groups_only(qty, free):
    c = pricing.calculate_line(810, 96, [FREE], qty)
    assert c.free_cases == free
    assert c.discount_paise == 0
    assert c.line_total_paise == 77760 * qty        # free cases are not charged, and not discounted from the price


@pytest.mark.parametrize("qty,disc", [(1, 0), (4, 0), (5, 30450), (6, 36540), (10, 60900)])
def test_detergent_discount_applies_from_five_cases(qty, disc):
    c = pricing.calculate_line(10150, 20, [PCT], qty)
    assert c.discount_paise == disc                  # 3% of qty x 2030.00, in paise
    assert c.line_total_paise == 203000 * qty - disc
    assert c.free_cases == 0


def test_no_scheme_for_tea():
    c = pricing.calculate_line(11800, 40, [], 3)
    assert (c.free_cases, c.discount_paise, c.line_total_paise) == (0, 0, 472000 * 3)
    assert c.scheme_applied is None


def test_percent_rounding_is_half_up_in_integer_paise():
    assert pricing.percent_of(50, 300) == 2     # 1.5 -> 2
    assert pricing.percent_of(49, 300) == 1     # 1.47 -> 1
    assert pricing.percent_of(0, 300) == 0


@pytest.mark.parametrize("bad", [0, -1, -100, 10_001, 1.5, True, "5", None])
def test_invalid_quantities_are_refused(bad):
    with pytest.raises(ValueError):
        pricing.calculate_line(810, 96, [FREE], bad)


def test_catalogue_matches_supplied_data(client, r1):
    body = client.get("/api/catalogue", headers=r1).json()
    p = {x["sku"]: x for x in body["products"]}
    assert set(p) == {"SKU-BS-075", "SKU-DT-1KG", "SKU-TE-250"}
    b, d, t = p["SKU-BS-075"], p["SKU-DT-1KG"], p["SKU-TE-250"]
    assert (b["name"], b["packaging_label"], b["unit_price_paise"], b["stock_cases"]) == ("Glucose biscuit 75 g", "Case of 96", 810, 340)
    assert (d["name"], d["packaging_label"], d["unit_price_paise"], d["stock_cases"]) == ("Detergent powder 1 kg", "Case of 20", 10150, 85)
    assert (t["name"], t["packaging_label"], t["unit_price_paise"], t["stock_cases"]) == ("Tea leaf 250 g", "Case of 40", 11800, 0)
    assert (b["case_price_paise"], d["case_price_paise"], t["case_price_paise"]) == (77760, 203000, 472000)
    assert b["scheme"]["description"] == "Buy 10 cases, get 1 free"
    assert d["scheme"]["percent_bp"] == 300 and t["scheme"] is None
    assert t["stock_status"] == "out_of_stock" and b["stock_status"] == "in_stock"


def test_catalogue_gst_is_flagged_as_unspecified(client, r1):
    body = client.get("/api/catalogue", headers=r1).json()
    assert body["gst_status"] == "unspecified" and "not specified" in body["gst_note"]


def test_catalogue_search(client, r1):
    names = lambda q: [p["name"] for p in client.get("/api/catalogue", params={"q": q}, headers=r1).json()["products"]]
    assert names("tea") == ["Tea leaf 250 g"]
    assert names("SKU-DT") == ["Detergent powder 1 kg"]
    assert names("बिस्कुट") == ["Glucose biscuit 75 g"]
    assert names("zzz") == []
    assert len(names("")) == 3
    assert names("%") == []                              # wildcard characters are escaped, not interpreted
