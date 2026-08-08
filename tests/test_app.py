import hmac
import hashlib
import time
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
SECRET = b"weekend_key"

def sign(payload: bytes, timestamp: str) -> str:
    signed = timestamp.encode() + b"." + payload
    return hmac.new(SECRET, signed, hashlib.sha256).hexdigest()

def test_valid_signature_accepted():
    payload = b'{"event":"test1"}'
    ts = str(int(time.time()))
    resp = client.post(
        "/v1/intake/test-client",
        content=payload,
        headers={"x-webhook-timestamp": ts, "x-webhook-signature": sign(payload, ts)},
    )
    assert resp.status_code == 202

def test_invalid_signature_rejected():
    payload = b'{"event":"test2"}'
    ts = str(int(time.time()))
    resp = client.post(
        "/v1/intake/test-client",
        content=payload,
        headers={"x-webhook-timestamp": ts, "x-webhook-signature": "wrong"},
    )
    assert resp.status_code == 401

def test_missing_signature_rejected():
    resp = client.post("/v1/intake/test-client", content=b'{"event":"test3"}')
    assert resp.status_code == 401