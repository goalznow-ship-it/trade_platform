"""Thread-safe provider health and circuit-breaker registry."""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from threading import Lock
import time
from typing import Optional


@dataclass
class ProviderState:
    configured: bool = True
    consecutive_failures: int = 0
    circuit_open_until: float = 0.0
    last_success_at: Optional[str] = None
    last_failure_at: Optional[str] = None
    last_error: Optional[str] = None


class ProviderHealthRegistry:
    def __init__(self, failure_threshold: int = 3, recovery_seconds: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._states: dict[str, ProviderState] = {}
        self._lock = Lock()

    def configure(self, provider: str, configured: bool) -> None:
        with self._lock:
            self._states.setdefault(provider, ProviderState()).configured = configured

    def allow_request(self, provider: str) -> bool:
        with self._lock:
            state = self._states.setdefault(provider, ProviderState())
            return state.configured and time.monotonic() >= state.circuit_open_until

    def success(self, provider: str) -> None:
        with self._lock:
            state = self._states.setdefault(provider, ProviderState())
            state.consecutive_failures = 0
            state.circuit_open_until = 0
            state.last_success_at = datetime.now(timezone.utc).isoformat()
            state.last_error = None

    def failure(self, provider: str, error: Exception | str) -> None:
        with self._lock:
            state = self._states.setdefault(provider, ProviderState())
            state.consecutive_failures += 1
            state.last_failure_at = datetime.now(timezone.utc).isoformat()
            state.last_error = str(error)[:500]
            if state.consecutive_failures >= self.failure_threshold:
                state.circuit_open_until = time.monotonic() + self.recovery_seconds

    def snapshot(self) -> dict[str, dict]:
        now = time.monotonic()
        with self._lock:
            result = {}
            for name, state in self._states.items():
                item = asdict(state)
                item.pop("circuit_open_until")
                item["circuit_open"] = now < state.circuit_open_until
                item["status"] = (
                    "not_configured" if not state.configured
                    else "circuit_open" if item["circuit_open"]
                    else "degraded" if state.consecutive_failures
                    else "healthy" if state.last_success_at
                    else "unknown"
                )
                result[name] = item
            return result


provider_health = ProviderHealthRegistry()
