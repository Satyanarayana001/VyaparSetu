import httpx
import pytest
from sqlalchemy import func, select

from app import models
from app.services import ai_capture, llm
from conftest import BS, DT, SAMPLE, TE, place


def parse(client, headers, msg):
    r = client.post("/api/ai/parse", json={"message": msg}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_supplied_example_message(client, r1):
    out = parse(client, r1, SAMPLE)
    assert out["mode"] == "fallback" and "No LLM" in out["fallback_reason"]          # honestly labelled
    biscuit, detergent, tea = out["lines"]
    assert (biscuit["sku"], biscuit["quantity"], biscuit["unit"], biscuit["validation_status"]) == (BS, 5, "case", "ok")
    assert (detergent["sku"], detergent["quantity"], detergent["validation_status"]) == (DT, 2, "ok")
    assert (tea["sku"], tea["quantity"], tea["validation_status"]) == (TE, 1, "out_of_stock")
    assert tea["stock_cases"] == 0 and "Out of stock" in tea["messages"][0]
    assert biscuit["original_phrase"] == "5 peti biscuit chhota" and biscuit["packaging"] == "Case of 96"
    assert biscuit["confidence"] >= 0.7 and len(biscuit["alternatives"]) == 2
    assert {a["sku"] for a in biscuit["alternatives"]} == {DT, TE}


@pytest.mark.parametrize("msg,expected", [
    ("5 peti biscuit, 2 peti surf, 1 peti chai", {BS: 5, DT: 2, TE: 1}),
    ("५ पेटी बिस्कुट, २ पेटी वॉशिंग पाउडर", {BS: 5, DT: 2}),
    ("teen peti detergent aur do peti glucose biscuit", {DT: 3, BS: 2}),
    ("5 peti biscuit 2 peti washing powder 1 kilo", {BS: 5, DT: 2}),                    # no commas
    ("tea 250 g 3 cases and biscuits 75g 4 cases", {TE: 3, BS: 4}),
    ("bhej do 4 peti surf", {DT: 4}),
])
def test_general_parsing_not_just_the_example(client, r1, msg, expected):
    lines = parse(client, r1, msg)["lines"]
    assert {l["sku"]: l["quantity"] for l in lines} == expected


def test_quantity_without_unit_is_not_assumed_to_be_cases(client, r1):
    l = parse(client, r1, "biscuit 5")["lines"][0]
    assert l["validation_status"] == "needs_clarification" and l["clarification"] == "unit"
    assert l["quantity"] is None and l["raw_quantity"] == 5 and l["unit"] == "unknown"
    assert "cases or packs" in l["messages"][0]


def test_quantity_in_packs_is_not_converted_silently(client, r1):
    l = parse(client, r1, "5 packet biscuit")["lines"][0]
    assert l["validation_status"] == "needs_clarification" and l["clarification"] == "unit" and l["quantity"] is None
    assert "96 packs per case" in l["messages"][0]


def test_ambiguous_product_asks_for_clarification_with_alternatives(client, r1):
    l = parse(client, r1, "2 peti powder")["lines"][0]
    assert l["validation_status"] == "needs_clarification" and l["clarification"] == "product"
    assert l["confidence"] < 0.7 and len(l["alternatives"]) == 2 and l["original_phrase"] == "2 peti powder"
    l = parse(client, r1, "1 kg 2 peti")["lines"][0]
    assert l["validation_status"] == "needs_clarification" and l["confidence"] < 0.7


def test_unknown_product_is_flagged_not_guessed(client, r1):
    l = parse(client, r1, "3 peti mithai")["lines"][0]
    assert l["sku"] is None and l["validation_status"] == "needs_clarification" and len(l["alternatives"]) == 3


def test_invalid_quantities_in_text(client, r1):
    assert parse(client, r1, "-3 peti biscuit")["lines"][0]["validation_status"] == "invalid_quantity"
    assert parse(client, r1, "1.5 peti biscuit")["lines"][0]["validation_status"] == "invalid_quantity"


def test_insufficient_stock_is_flagged(client, r1):
    l = parse(client, r1, "86 peti detergent")["lines"][0]
    assert l["validation_status"] == "insufficient_stock" and "Only 85" in l["messages"][0]


def test_parsing_never_places_an_order(client, db, r1):
    parse(client, r1, SAMPLE)
    db.expire_all()
    assert db.scalar(select(func.count()).select_from(models.Order).where(models.Order.is_historical_seed.is_(False))) == 0
    assert db.scalar(select(models.Product.stock_cases).where(models.Product.sku == BS)) == 340


def test_ai_order_requires_confirmation_and_stores_the_interpretation(client, db, r1):
    p = parse(client, r1, SAMPLE)
    ok = [l for l in p["lines"] if l["validation_status"] == "ok"]
    body = {"items": [{"sku": l["sku"], "quantity_cases": l["quantity"], "ai_line_id": l["line_id"]} for l in ok],
            "source": "ai", "ai_parse_id": p["parse_id"], "idempotency_key": "ai-order-audit-01"}
    o = client.post("/api/orders", json=body, headers=r1).json()["order"]
    assert o["source"] == "ai" and o["original_message"] == SAMPLE
    first = o["items"][0]
    assert first["original_phrase"] == "5 peti biscuit chhota" and first["ai_confidence"] >= 0.7 and first["ai_matched_sku"] == BS
    assert first["was_corrected"] is False and len(first["ai_alternatives"]) == 2


def test_out_of_stock_ai_line_blocks_confirmation(client, r1):
    p = parse(client, r1, SAMPLE)
    body = {"items": [{"sku": l["sku"], "quantity_cases": l["quantity"], "ai_line_id": l["line_id"]} for l in p["lines"]],
            "source": "ai", "ai_parse_id": p["parse_id"], "idempotency_key": "ai-block-oos-001"}
    r = client.post("/api/orders", json=body, headers=r1)
    assert r.status_code == 422 and r.json()["error"]["details"][0]["code"] == "OUT_OF_STOCK"


def test_ai_order_with_forged_message_or_line_reference_is_refused(client, r1):
    p = parse(client, r1, "2 peti biscuit")
    body = {"items": [{"sku": BS, "quantity_cases": 2, "ai_line_id": "l99"}], "source": "ai", "ai_parse_id": p["parse_id"],
            "idempotency_key": "ai-forged-line-01"}
    assert client.post("/api/orders", json=body, headers=r1).json()["error"]["code"] == "INVALID_AI_LINE"
    assert client.post("/api/orders", json={**body, "ai_parse_id": 9999, "idempotency_key": "ai-forged-parse-1"}, headers=r1).status_code == 422


def test_saved_alias_is_used_for_future_matching(client, db, r1, desk):
    rid = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R001"))
    assert parse(client, r1, "2 peti nashta packet")["lines"][0]["sku"] is None
    client.post(f"/api/desk/retailers/{rid}/aliases", json={"alias_text": "Nashta Packet", "sku": BS}, headers=desk)
    l = parse(client, r1, "2 peti nashta packet")["lines"][0]
    assert (l["sku"], l["match_source"], l["confidence"], l["validation_status"]) == (BS, "alias", 0.98, "ok")
    assert parse(client, r1, "peti 3 packet nashta")["lines"][0]["sku"] == BS             # order-insensitive


# ---------------------------------------------------------------- LLM path (with a fake provider; no network)
class FakeProvider:
    name, model = "fake", "fake-model-1"

    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    def extract(self, system, user):
        if self.error:
            raise self.error
        return self.result


def use(provider):
    ai_capture.provider_factory = lambda: provider


def test_llm_mode_uses_model_output_but_validates_it(client, r1):
    use(FakeProvider({"lines": [
        {"original_phrase": "5 peti biscuit chhota", "quantity": 5, "unit": "case", "sku": BS, "confidence": 0.93, "alternative_skus": [DT]},
        {"original_phrase": "1 peti chai patti", "quantity": 1, "unit": "case", "sku": TE, "confidence": 0.9, "alternative_skus": []},
        {"original_phrase": "something", "quantity": 2, "unit": "case", "sku": "SKU-INVENTED", "confidence": 0.99, "alternative_skus": []},
    ]}))
    out = parse(client, r1, SAMPLE)
    assert out["mode"] == "llm" and out["model"] == "fake-model-1" and out["fallback_reason"] is None
    a, b, c = out["lines"]
    assert (a["sku"], a["validation_status"], len(a["alternatives"])) == (BS, "ok", 2)
    assert b["validation_status"] == "out_of_stock"                                  # stock is still checked by the backend
    assert c["sku"] is None and c["validation_status"] == "needs_clarification"      # invented SKU rejected


def test_llm_low_confidence_or_unknown_unit_still_needs_human(client, r1):
    use(FakeProvider({"lines": [{"original_phrase": "biscuit 5", "quantity": 5, "unit": "unknown", "sku": BS, "confidence": 0.9, "alternative_skus": []},
                                {"original_phrase": "maybe tea", "quantity": 1, "unit": "case", "sku": TE, "confidence": 0.4, "alternative_skus": []}]}))
    a, b = parse(client, r1, "x")["lines"]
    assert a["validation_status"] == "needs_clarification" and a["clarification"] == "unit"
    assert b["validation_status"] == "needs_clarification" and b["clarification"] == "product"


@pytest.mark.parametrize("error,reason", [
    (llm.LLMTimeout(), "timed out"), (llm.LLMRateLimited(), "rate limit"),
    (llm.LLMUnavailable(), "unavailable"), (llm.LLMInvalidOutput(), "invalid output"), (RuntimeError("boom"), "LLM error")])
def test_llm_failures_fall_back_and_say_so(client, r1, error, reason):
    use(FakeProvider(error=error))
    out = parse(client, r1, SAMPLE)
    assert out["mode"] == "fallback" and reason in out["fallback_reason"]
    assert [l["sku"] for l in out["lines"]] == [BS, DT, TE]                           # the order is still captured


def test_llm_schema_violation_falls_back(client, r1):
    use(FakeProvider({"lines": [{"original_phrase": "x", "quantity": 1, "unit": "crate", "sku": BS, "confidence": 7}]}))
    assert parse(client, r1, SAMPLE)["mode"] == "fallback"
    use(FakeProvider({"nope": 1}))
    assert parse(client, r1, SAMPLE)["mode"] == "fallback"


def test_retailer_alias_overrides_model_guess(client, db, r1, desk):
    rid = db.scalar(select(models.Retailer.id).where(models.Retailer.code == "R001"))
    client.post(f"/api/desk/retailers/{rid}/aliases", json={"alias_text": "chhota biscuit", "sku": DT}, headers=desk)
    use(FakeProvider({"lines": [{"original_phrase": "2 peti chhota biscuit", "quantity": 2, "unit": "case", "sku": BS, "confidence": 0.9, "alternative_skus": []}]}))
    l = parse(client, r1, "x")["lines"][0]
    assert l["sku"] == DT and l["match_source"] == "alias"


def test_ai_status_endpoint_reports_mode(client, r1):
    assert client.get("/api/ai/status", headers=r1).json()["mode"] == "fallback"
    use(FakeProvider({"lines": []}))
    assert client.get("/api/ai/status", headers=r1).json() == {"mode": "llm", "model": "fake-model-1", "reason": None}


def test_message_length_is_limited(client, r1):
    assert client.post("/api/ai/parse", json={"message": "x" * 1001}, headers=r1).status_code == 422
    assert client.post("/api/ai/parse", json={"message": ""}, headers=r1).status_code == 422


# ---------------------------------------------------------------- HTTP-level provider behaviour (httpx stubbed)
def _resp(status, payload=None):
    return httpx.Response(status, json=payload or {}, request=httpx.Request("POST", "http://x"))


@pytest.mark.parametrize("status,exc", [(429, llm.LLMRateLimited), (503, llm.LLMUnavailable), (401, llm.LLMUnavailable)])
def test_provider_http_errors_map_to_domain_errors(monkeypatch, status, exc):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _resp(status))
    for prov in (llm.OpenAICompatibleProvider("k", "m", None, 1), llm.AnthropicProvider("k", "m", None, 1)):
        with pytest.raises(exc):
            prov.extract("s", "u")


def test_provider_timeout_and_garbage(monkeypatch):
    def boom(*a, **k):
        raise httpx.ReadTimeout("slow")
    monkeypatch.setattr(llm.httpx, "post", boom)
    with pytest.raises(llm.LLMTimeout):
        llm.OpenAICompatibleProvider("k", "m", None, 1).extract("s", "u")
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _resp(200, {"choices": [{"message": {"content": "not json"}}]}))
    with pytest.raises(llm.LLMInvalidOutput):
        llm.OpenAICompatibleProvider("k", "m", None, 1).extract("s", "u")
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _resp(200, {"content": [{"type": "text", "text": "hi"}]}))
    with pytest.raises(llm.LLMInvalidOutput):
        llm.AnthropicProvider("k", "m", None, 1).extract("s", "u")


def test_provider_happy_path_parsing(monkeypatch):
    good = {"lines": [{"original_phrase": "a", "quantity": 1, "unit": "case", "sku": BS, "confidence": 0.9, "alternative_skus": []}]}
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _resp(200, {"choices": [{"message": {"content": __import__("json").dumps(good)}}]}))
    assert llm.extract_lines(llm.OpenAICompatibleProvider("k", "m", None, 1), "msg", "cat")[0].sku == BS
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: _resp(200, {"content": [{"type": "tool_use", "input": good}]}))
    assert llm.extract_lines(llm.AnthropicProvider("k", "m", None, 1), "msg", "cat")[0].sku == BS


def test_no_provider_without_key():
    from app.config import Settings
    assert llm.build_provider(Settings(llm_provider="openai", llm_api_key=None, llm_model="m")) is None
    assert llm.build_provider(Settings(llm_provider="none", llm_api_key="k", llm_model="m")) is None
    assert llm.build_provider(Settings(llm_provider="openai", llm_api_key="k", llm_model="m")).name == "openai"
