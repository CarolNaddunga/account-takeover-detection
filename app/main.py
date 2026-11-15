from datetime import timezone

from fastapi import FastAPI

from .schemas import (
    EventIngestResponse,
    HealthResponse,
    LoginEvent,
    LoginInput,
    PredictionResponse,
)
from .scoring import MODEL_VERSION, RiskScorer
from .state import feature_store

WATERMARK_SECONDS = 5.0

app = FastAPI(
    title="Real-Time Account Takeover Detection",
    description="Educational prototype for scoring student-portal login risk.",
    version="0.1.0",
)
scorer = RiskScorer(feature_store)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        scorer_ready=scorer.ready,
        model_version=MODEL_VERSION,
        processor_ready=True,
        feature_store="in-memory (demo only)",
    )


@app.post("/predict", response_model=PredictionResponse)
def predict(login: LoginInput) -> PredictionResponse:
    """Score before the portal completes sign-in; this does not record the event."""
    return scorer.score(login)


@app.post("/events/login", response_model=EventIngestResponse)
def ingest_login(event: LoginEvent) -> EventIngestResponse:
    """Record an outcome for future scores, simulating a broker/stream processor."""
    delay_seconds = max(
        0.0,
        (event.received_at.astimezone(timezone.utc) - event.event_time.astimezone(timezone.utc)).total_seconds(),
    )

    if not feature_store.mark_seen(event.event_id):
        return EventIngestResponse(
            event_id=event.event_id,
            status="duplicate_ignored",
            delay_seconds=round(delay_seconds, 3),
            message="Duplicate event ID; it was not processed again.",
        )

    if delay_seconds > WATERMARK_SECONDS:
        feature_store.note_late_event(event, delay_seconds)
        return EventIngestResponse(
            event_id=event.event_id,
            status="late_for_review",
            delay_seconds=round(delay_seconds, 3),
            message="Event exceeded the five-second delay allowance and was routed for review.",
        )

    feature_store.record(event)
    return EventIngestResponse(
        event_id=event.event_id,
        status="processed",
        delay_seconds=round(delay_seconds, 3),
        message="Event added to recent account activity.",
    )
