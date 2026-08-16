"""Structured failure provenance for Volcengine last-mile adapters.

These exceptions describe *where a request failed*, not what a model can or
cannot do. AstrBot/user owns routing and retry policy; this plugin only makes
the local-vs-upstream distinction explicit and machine-readable.
"""

from __future__ import annotations

from typing import Any


class AdapterInputTransportError(ValueError):
    """Current-request media failed before a valid Ark request reached upstream.

    This is evidence about the transport path only. It must never be persisted
    as a negative model capability fact or promoted into a routing instruction.
    """

    code = "volcengine_input_transport_error"
    failure_domain = "input_transport"
    reached_model = False
    capability_observed = None
    evidence_lifetime = "current_request"

    def __init__(self, message: str, *, media_type: str, stage: str) -> None:
        super().__init__(message)
        self.media_type = media_type
        self.stage = stage

    def to_feedback(self) -> dict[str, Any]:
        """Return non-secret provenance without routing advice."""

        return {
            "code": self.code,
            "failure_domain": self.failure_domain,
            "media_type": self.media_type,
            "stage": self.stage,
            "reached_model": self.reached_model,
            "capability_observed": self.capability_observed,
            "evidence_lifetime": self.evidence_lifetime,
        }
