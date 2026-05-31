from __future__ import annotations

from dataclasses import dataclass

GENERIC_PROVIDER_CODES = {
    "provider_missing_key",
    "provider_rate_limited",
    "provider_auth_failed",
    "provider_model_not_found",
    "provider_timeout",
    "provider_unavailable",
    "provider_bad_response",
    "provider_unknown_error",
}

OPENROUTER_LEGACY_BY_GENERIC = {
    "provider_missing_key": "openrouter_missing_key",
    "provider_rate_limited": "openrouter_rate_limited",
    "provider_auth_failed": "openrouter_auth_failed",
    "provider_model_not_found": "openrouter_model_not_found",
    "provider_timeout": "openrouter_timeout",
    "provider_unavailable": "openrouter_unavailable",
    "provider_bad_response": "openrouter_bad_response",
    "provider_unknown_error": "openrouter_unknown_error",
}

OPENROUTER_GENERIC_BY_LEGACY = {
    legacy: generic for generic, legacy in OPENROUTER_LEGACY_BY_GENERIC.items()
}


@dataclass
class ProviderError(ValueError):
    provider: str
    code: str
    message: str
    status_code: int | None = None
    retryable: bool = False
    raw_detail: str | None = None
    legacy_code: str | None = None

    def __str__(self) -> str:
        return self.message

    def to_public_payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "detail": self.message,
            "code": self.code,
            "provider": self.provider,
            "retryable": self.retryable,
        }
        if self.legacy_code:
            payload["legacy_code"] = self.legacy_code
        return payload


def get_openrouter_legacy_code(generic_code: str) -> str | None:
    return OPENROUTER_LEGACY_BY_GENERIC.get(generic_code)


def get_generic_provider_code(code: str) -> str:
    if code in GENERIC_PROVIDER_CODES:
        return code
    return OPENROUTER_GENERIC_BY_LEGACY.get(code, "provider_unknown_error")

