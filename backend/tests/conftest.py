import os
import tempfile

# Must be set before the app is imported.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["JWT_SECRET"] = "test-secret-not-for-production-0123456789abcdef"
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["SEED_DEMO_DATA"] = "false"
os.environ["LLM_PROVIDER"] = "none"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import seed as seed_mod  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.security import login_throttle  # noqa: E402
from app.services import ai_capture  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        seed_mod.seed(db)
    login_throttle._fails.clear()
    ai_capture.provider_factory = lambda: None     # default: no LLM configured
    yield


@pytest.fixture()
def db():
    with SessionLocal() as s:
        yield s


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def r1(client):
    return _login(client, "retailer1@demo.test", seed_mod.DEMO_RETAILER_PASSWORD)


@pytest.fixture()
def r2(client):
    return _login(client, "retailer2@demo.test", seed_mod.DEMO_RETAILER_PASSWORD)


@pytest.fixture()
def desk(client):
    return _login(client, "desk@demo.test", seed_mod.DEMO_DESK_PASSWORD)


@pytest.fixture()
def salesman(client):
    return _login(client, "salesman@demo.test", seed_mod.DEMO_SALESMAN_PASSWORD)


_n = {"i": 0}


def place(client, headers, items, **extra):
    _n["i"] += 1
    body = {"items": [{"sku": s, "quantity_cases": q} for s, q in items], "idempotency_key": f"test-key-{_n['i']:06d}", **extra}
    return client.post("/api/orders", json=body, headers=headers)


SAMPLE = "bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo, chai patti 250 wala 1 peti"
BS, DT, TE = "SKU-BS-075", "SKU-DT-1KG", "SKU-TE-250"
