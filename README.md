# Heimdall

Heimdall is a webhook verification and relay proxy. It sits between an external webhook source and internal services, verifies the request is authentic, and forwards it.

## Name

Heimdall guards the Bifrost, the bridge between two worlds, in Norse mythology and sees anything approaching before it gets there. That's what this does. Sits at the boundary, checks what's coming in, only lets verified stuff through.

## Flow

1. Webhook comes in
2. Verify HMAC-SHA256 signature (raw bytes, constant-time compare)
3. Check timestamp is within tolerance, reject if the signature's already been seen
4. Log it
5. Respond 202 immediately
6. Forward to destination in the background, retry with backoff on failure

## Why these specific decisions

- Signature is computed on the raw request body, not the parsed/re-serialized JSON. Parsing first changes the bytes and breaks the signature check.
- Comparison uses `hmac.compare_digest`, not `==`, so it doesn't leak timing info.
- Timestamp is signed together with the payload, not compared separately. Otherwise someone could resend an old request with a new timestamp attached.
- Replay check is a `UNIQUE` constraint on signature in the DB, not a check-then-insert in application code. Two identical requests arriving at the same time could both pass a plain in-memory check before either gets recorded.
- Secret comes from an environment variable, not hardcoded. Confirmed by gitleaks in CI.

## Retry

Forwarding runs as a background task so the sender doesn't wait on it. If the destination fails or times out, retries at 2s, 4s, 8s, 16s, 32s. After that it's marked failed instead of retried forever or silently dropped.

## Docker

Multi-stage build, non-root user, docker-compose for running the proxy and a test destination together.

## CI/CD

On every push: tests, Bandit (SAST), pip-audit (dependency scan), gitleaks (secret scan), build the image, Trivy (image scan), push to GHCR tagged with the commit SHA. The image only gets built and pushed if tests and scans pass first.

## Known limitations

- Retries are in-memory. If the process restarts mid-retry, that task is gone. A row stuck on `retrying` after a restart means it got interrupted, not that it failed.
- No sweep job yet to catch and requeue those stuck rows.
- SQLite works fine for one instance. Multiple instances would need a shared DB.

## Run it

```
docker compose up --build
```

Proxy on `:8000`, test destination on `:9000`.
