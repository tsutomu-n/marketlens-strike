from __future__ import annotations

import base64
import hashlib
import hmac
import os
from collections.abc import Mapping
from dataclasses import dataclass


BITGET_CREDENTIAL_ENV: tuple[str, ...] = (
    "BITGET_API_KEY",
    "BITGET_API_SECRET",
    "BITGET_PASSPHRASE",
)
SENSITIVE_AUTH_HEADERS = frozenset({"ACCESS-KEY", "ACCESS-SIGN", "ACCESS-PASSPHRASE"})


@dataclass(frozen=True)
class BitgetCredentials:
    api_key: str
    api_secret: str
    passphrase: str

    def __post_init__(self) -> None:
        if not self.api_key.strip() or not self.api_secret.strip() or not self.passphrase.strip():
            raise ValueError("Bitget credentials must not be empty")


def missing_bitget_credential_env(env: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if env is None else env
    return [key for key in BITGET_CREDENTIAL_ENV if not source.get(key, "").strip()]


def bitget_credentials_from_env(env: Mapping[str, str] | None = None) -> BitgetCredentials:
    source = os.environ if env is None else env
    missing = missing_bitget_credential_env(source)
    if missing:
        raise ValueError(f"missing Bitget credential env: {','.join(missing)}")
    return BitgetCredentials(
        api_key=source["BITGET_API_KEY"].strip(),
        api_secret=source["BITGET_API_SECRET"].strip(),
        passphrase=source["BITGET_PASSPHRASE"].strip(),
    )


def sign_bitget_request(
    *,
    api_secret: str,
    timestamp: str,
    method: str,
    request_path: str,
    query_string: str = "",
    body: str = "",
) -> str:
    normalized_method = method.upper()
    path = f"{request_path}?{query_string}" if query_string else request_path
    pre_hash = f"{timestamp}{normalized_method}{path}{body}"
    digest = hmac.new(api_secret.encode("utf-8"), pre_hash.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(digest).decode("ascii")


def build_bitget_auth_headers(
    *,
    credentials: BitgetCredentials,
    timestamp: str,
    method: str,
    request_path: str,
    query_string: str = "",
    body: str = "",
) -> dict[str, str]:
    return {
        "ACCESS-KEY": credentials.api_key,
        "ACCESS-SIGN": sign_bitget_request(
            api_secret=credentials.api_secret,
            timestamp=timestamp,
            method=method,
            request_path=request_path,
            query_string=query_string,
            body=body,
        ),
        "ACCESS-TIMESTAMP": timestamp,
        "ACCESS-PASSPHRASE": credentials.passphrase,
        "Content-Type": "application/json",
    }


def redact_auth_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: "[REDACTED]" if key.upper() in SENSITIVE_AUTH_HEADERS else value
        for key, value in headers.items()
    }
