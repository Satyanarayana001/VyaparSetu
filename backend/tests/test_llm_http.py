"""Exercises the REAL HTTP client code (httpx, headers, JSON schema request, timeouts, error mapping) against a local
mock server that speaks the OpenAI-compatible and Anthropic wire formats. This is NOT a live LLM: it proves the integration
mechanics, not model quality."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.config import Settings
from app.services import ai_capture, llm
from conftest import BS, DT, SAMPLE, TE

GOOD = {"lines": [
    {"original_phrase": "5 peti biscuit chhota", "quantity": 5, "unit": "case", "sku": BS, "confidence": 0.94, "alternative_skus": [DT, TE]},
    {"original_phrase": "2 peti washing powder 1 kilo", "quantity": 2, "unit": "case", "sku": DT, "confidence": 0.93, "alternative_skus": [BS, TE]},
    {"original_phrase": "chai patti 250 wala 1 peti", "quantity": 1, "unit": "case", "sku": TE, "confidence": 0.9, "alternative_skus": [BS, DT]}]}


class Mock:
    def __init__(self):
        self.mode, self.requests = "ok", []
        outer = self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):  # silence
                pass

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append({"path": self.path, "headers": dict(self.headers), "body": body})
                if outer.mode == "slow":
                    time.sleep(1.2)
                status, payload = {"ok": (200, None), "slow": (200, None), "429": (429, {"error": "rate"}), "500": (500, {"error": "boom"}),
                                   "401": (401, {"error": "bad key"}), "garbage": (200, {"choices": [{"message": {"content": "sorry, I can't"}}]})}[outer.mode]
                if payload is None:
                    payload = ({"choices": [{"message": {"content": json.dumps(GOOD)}}]} if self.path.endswith("/chat/completions")
                               else {"content": [{"type": "tool_use", "name": "record_order_lines", "input": GOOD}]})
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), H)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture()
def mock():
    m = Mock()
    yield m
    m.server.shutdown()


def configure(provider, url, timeout=5.0):
    s = Settings(llm_provider=provider, llm_api_key="sk-test-123", llm_model="test-model", llm_base_url=url, llm_timeout_seconds=timeout)
    ai_capture.provider_factory = lambda: llm.build_provider(s)


def parse(client, headers, msg=SAMPLE):
    r = client.post("/api/ai/parse", json={"message": msg}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def test_openai_compatible_end_to_end(client, r1, mock):
    configure("openai", mock.url + "/v1")
    out = parse(client, r1)
    assert out["mode"] == "llm" and out["model"] == "test-model" and out["fallback_reason"] is None
    assert [(l["sku"], l["quantity"], l["validation_status"]) for l in out["lines"]] == [(BS, 5, "ok"), (DT, 2, "ok"), (TE, 1, "out_of_stock")]
    req = mock.requests[0]
    assert req["path"] == "/v1/chat/completions" and req["headers"]["Authorization"] == "Bearer sk-test-123"
    body = req["body"]
    assert body["model"] == "test-model" and body["response_format"]["type"] == "json_schema" and body["response_format"]["json_schema"]["strict"] is True
    prompt = json.dumps(body["messages"])
    assert SAMPLE in prompt and "SKU-BS-075" in prompt and "SKU-TE-250" in prompt and "untrusted" in prompt
    assert "sk-test-123" not in prompt                                   # the key is only ever in the auth header
    assert "dealer" not in prompt.lower() and "price" not in prompt.lower().replace("pricing", "")  # no prices/credit sent to the model


def test_anthropic_wire_format_end_to_end(client, r1, mock):
    configure("anthropic", mock.url)
    out = parse(client, r1)
    assert out["mode"] == "llm" and [l["sku"] for l in out["lines"]] == [BS, DT, TE]
    req = mock.requests[0]
    assert req["path"] == "/v1/messages" and req["headers"]["x-api-key"] == "sk-test-123" and "anthropic-version" in req["headers"]
    assert req["body"]["tool_choice"] == {"type": "tool", "name": "record_order_lines"}


@pytest.mark.parametrize("mode,reason", [("429", "rate limit"), ("500", "unavailable"), ("401", "unavailable"), ("garbage", "invalid output")])
def test_provider_errors_fall_back_and_still_capture_the_order(client, r1, mock, mode, reason):
    mock.mode = mode
    configure("openai", mock.url + "/v1")
    out = parse(client, r1)
    assert out["mode"] == "fallback" and reason in out["fallback_reason"]
    assert [l["sku"] for l in out["lines"]] == [BS, DT, TE]


def test_timeout_falls_back(client, r1, mock):
    mock.mode = "slow"
    configure("openai", mock.url + "/v1", timeout=0.3)
    t0 = time.time()
    out = parse(client, r1)
    assert out["mode"] == "fallback" and "timed out" in out["fallback_reason"] and time.time() - t0 < 1.1


def test_unreachable_provider_falls_back(client, r1):
    configure("openai", "http://127.0.0.1:9/v1", timeout=1)      # nothing listens on port 9
    out = parse(client, r1)
    assert out["mode"] == "fallback" and out["fallback_reason"]
