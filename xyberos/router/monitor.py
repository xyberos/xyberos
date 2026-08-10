"""Per-tier dashboards and tuning loop (RFC-0017, M14 wiring)."""

from __future__ import annotations

import threading
from typing import Any, cast

from ..contracts.experience import ExperienceStore
from ..events import EventBus
from ..events.names import ESCALATED, RESPONDER_HIT
from .tuner import CHEAP_TIERS, EscalationTuner


class TierMonitor:
    """Track per-tier hit/escalation counts and drive gate tuning.

    Subscribes to the router's ``brain.responder_hit`` / ``brain.escalated``
    events to build a per-tier dashboard (hit counts, escalation counts, hit
    rates) and to forward hits to an :class:`EscalationTuner` for warm-up
    auto-detach (RFC-0017).
    """

    def __init__(
        self,
        events: EventBus | None = None,
        tuner: EscalationTuner | None = None,
        *,
        window: int = 100,
    ) -> None:
        if window <= 0:
            raise ValueError("window must be a positive integer")
        self._events = events
        self._tuner = tuner
        self._window = window
        self._hits: dict[str, int] = {}
        self._escalations: dict[str, int] = {}
        self._recent: list[str] = []
        if events is not None:
            events.subscribe(RESPONDER_HIT, self._on_hit)
            events.subscribe(ESCALATED, self._on_escalated)

    @property
    def tuner(self) -> EscalationTuner | None:
        """The attached tuner, if any."""
        return self._tuner

    def hit_count(self, tier: str) -> int:
        """Total times ``tier`` answered."""
        return self._hits.get(tier, 0)

    def escalation_count(self, tier: str) -> int:
        """Total times ``tier`` escalated."""
        return self._escalations.get(tier, 0)

    def total_hits(self) -> int:
        """Total requests answered by any tier."""
        return sum(self._hits.values())

    def hit_rate(self, tier: str) -> float:
        """Share of recent requests answered by ``tier`` (0.0 if none)."""
        if not self._recent:
            return 0.0
        return sum(1 for name in self._recent if name == tier) / len(self._recent)

    def cheap_hit_rate(self) -> float:
        """Share of recent requests answered by LLM-free tiers."""
        if not self._recent:
            return 0.0
        return sum(1 for name in self._recent if name in CHEAP_TIERS) / len(self._recent)

    def summary(self) -> dict[str, dict[str, Any]]:
        """Per-tier dashboard: hits, escalations, and hit rate."""
        result: dict[str, dict[str, Any]] = {}
        for tier in sorted(set(self._hits) | set(self._escalations)):
            result[tier] = {
                "hits": self.hit_count(tier),
                "escalations": self.escalation_count(tier),
                "hit_rate": self.hit_rate(tier),
            }
        result["_total"] = {"hits": self.total_hits(), "cheap_hit_rate": self.cheap_hit_rate()}
        return result

    def tune(self, experience: ExperienceStore | None = None, *, limit: int = 50) -> int:
        """Tune router gates from an experience store via the attached tuner."""
        if self._tuner is None or experience is None:
            return 0
        return self._tuner.tune_from_experience(experience, limit=limit)

    # ------------------------------------------------------------------ #
    # internals
    # ------------------------------------------------------------------ #

    def _on_hit(self, event: Any) -> None:
        data = cast(dict[str, Any], getattr(event, "data", None) or {})
        tier = data.get("tier")
        if not isinstance(tier, str) or not tier:
            return
        self._hits[tier] = self._hits.get(tier, 0) + 1
        self._recent.append(tier)
        if len(self._recent) > self._window:
            self._recent.pop(0)
        if self._tuner is not None:
            self._tuner.record_hit(tier)

    def _on_escalated(self, event: Any) -> None:
        data = cast(dict[str, Any], getattr(event, "data", None) or {})
        tier = data.get("tier")
        if isinstance(tier, str) and tier:
            self._escalations[tier] = self._escalations.get(tier, 0) + 1


class TuningLoop:
    """Periodically tune router gates from experience in a background thread.

    ``start()`` spawns a daemon thread that calls ``monitor.tune(experience)``
    every ``interval`` seconds; ``stop()`` halts it. ``step()`` runs one
    iteration synchronously (handy for tests and batch jobs).
    """

    def __init__(
        self,
        monitor: TierMonitor,
        experience: ExperienceStore,
        *,
        interval: float = 30.0,
    ) -> None:
        if interval <= 0:
            raise ValueError("interval must be positive")
        self._monitor = monitor
        self._experience = experience
        self._interval = interval
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background tuning loop."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the background tuning loop."""
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1.0)
            self._thread = None

    def step(self) -> int:
        """Run one tuning iteration synchronously; return adjustments made."""
        return self._monitor.tune(self._experience)

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                self._monitor.tune(self._experience)
            except Exception:
                pass  # a tuning failure must not crash the loop
