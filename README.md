# Real-Time Account Takeover Detection

A small educational prototype of a university login risk service. It accepts login events, keeps a short event-time history per account, detects duplicate or late events, and returns a risk score with a suggested action.

> This is a learning prototype, not a production security control. Its rule-based score is not a calibrated probability and must not be used to automatically deny real users.

## Architecture

```text
Student browser
      |
      v
Login service / gateway (producer)
      |                    \
      | POST /predict       \ POST /events/login
      v                      v
Risk-scoring API        Local broker/stream-processor demo
      |                  - deduplicate event_id
      |                  - keep recent event-time features
      |                  - route late events for review
      v                      |
Allow / verify / hold       In-memory feature store + audit summary
      |
      v
Security alert dashboard (sink; represented by API response)
```

The prototype uses a simple rules engine in place of a trained model and in-memory components in place of a durable broker and feature store. The code keeps the boundaries visible so these can be replaced later. The rules engine loads with the application at startup; model training is outside the service.

## Run locally

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` for the interactive API page.

## API overview

- `POST /predict` scores the login before the portal decides whether to finish sign-in.
- `POST /events/login` records a login event after the decision so it can inform later scores.
- `GET /health` reports whether the API, scoring engine, processor, and in-memory feature store are ready.

Example scoring request:

```json
{
  "event_id": "evt-84721",
  "account_id": "acct-1905",
  "event_time": "2026-10-25T09:14:32Z",
  "result": "failure",
  "ip_address": "203.0.113.24",
  "device_id": "dev-5f20"
}
```

Example response:

```json
{
  "event_id": "evt-84721",
  "risk_score": 0.55,
  "model_version": "rules-v0.1.0",
  "decision": "verify",
  "reasons": ["new device", "new network address", "failed login"]
}
```

`risk_score` is a rule-based risk indicator between 0 and 1, not a probability. Thresholds are illustrative and need evaluation on representative data before any real deployment.

## Event handling choices

- Login history is grouped by account and evaluated over the previous ten minutes using event time.
- The demo accepts up to five seconds of event delay. Events arriving later are marked for review and do not hold up the login response. This is a simplified delay policy, not a complete distributed-stream watermark implementation.
- Repeated `event_id` values are ignored to prevent processing the same event twice.
- State is held in process memory and disappears when the app stops. A production version needs a durable broker, persistent feature store, access controls, encryption, retention limits, and checkpoints.
- The demo avoids writing IP addresses, device IDs, passwords, or tokens to application logs.

## Next steps

1. Replace the in-memory event path with a durable broker and checkpointed stream processor.
2. Replace the illustrative rules with a trained and evaluated model.
3. Add authentication and authorization for the API and dashboard.
4. Add durable storage with retention and privacy controls.
5. Pin dependency and container image versions for a reproducible release.
