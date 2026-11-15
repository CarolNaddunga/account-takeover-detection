from .schemas import LoginInput, PredictionResponse
from .state import InMemoryFeatureStore

MODEL_VERSION = "rules-v0.1.0"


class RiskScorer:
    """Transparent starter rules; this is not a trained or calibrated model."""

    def __init__(self, store: InMemoryFeatureStore) -> None:
        self.store = store
        self.ready = True

    def score(self, login: LoginInput) -> PredictionResponse:
        history = self.store.recent(login.account_id, login.event_time)
        score = 0.05
        reasons: list[str] = []

        failures = sum(event.result == "failure" for event in history)
        if failures >= 5:
            score += 0.50
            reasons.append("five or more recent failed logins")
        elif failures >= 3:
            score += 0.35
            reasons.append("several recent failed logins")

        known_devices = {event.device_id for event in history}
        known_ips = {event.ip_address for event in history}
        if history and login.device_id not in known_devices:
            score += 0.25
            reasons.append("new device for this account")
        if history and login.ip_address not in known_ips:
            score += 0.15
            reasons.append("new network address for this account")
        if login.result == "failure":
            score += 0.10
            reasons.append("current login failed")
        if login.event_time.hour < 5:
            score += 0.10
            reasons.append("login occurred during an unusual overnight period")

        score = min(round(score, 2), 1.0)
        if score >= 0.70:
            decision = "hold_for_review"
        elif score >= 0.35:
            decision = "verify"
        else:
            decision = "allow"

        return PredictionResponse(
            event_id=login.event_id,
            risk_score=score,
            model_version=MODEL_VERSION,
            decision=decision,
            reasons=reasons or ["no configured risk signals detected"],
        )
