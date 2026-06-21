from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass(frozen=True)
class LLMExtractionResult:
    payload: dict[str, Any]
    provider: str
    model_name: str | None
    input_hash: str
    prompt_version: str
    schema_version: str


class LLMAdapter:
    """Thin adapter boundary for future model providers.

    The first development milestone keeps the adapter explicit and disabled by default.
    Real providers can be added behind this interface without changing parser callers.
    """

    def extract_profile(
        self,
        text: str,
        schema: dict[str, Any],
        prompt_version: str = "profile_extract_v1",
    ) -> LLMExtractionResult:
        if settings.LLM_PROVIDER == "disabled":
            raise RuntimeError("LLM provider is disabled. Set LLM_PROVIDER to enable it.")

        input_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
        raise NotImplementedError(
            "LLM provider integration is intentionally deferred to the parser milestone. "
            f"input_hash={input_hash}, schema_keys={list(schema.keys())}"
        )

