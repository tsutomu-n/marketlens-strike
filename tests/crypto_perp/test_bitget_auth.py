from __future__ import annotations

import base64
import hashlib
import hmac
import json

import pytest

from sis.crypto_perp.bitget.auth import (
    BitgetCredentials,
    bitget_credentials_from_env,
    build_bitget_auth_headers,
    missing_bitget_credential_env,
    redact_auth_headers,
    sign_bitget_request,
)


def test_bitget_signature_matches_hmac_sha256_base64_shape() -> None:
    timestamp = "16273667805456"
    method = "POST"
    request_path = "/api/v2/mix/order/place-order"
    body = (
        '{"productType":"usdt-futures","symbol":"BTCUSDT","size":"8",'
        '"marginMode":"crossed","side":"buy","orderType":"limit",'
        '"clientOid":"channel#123456"}'
    )
    expected = base64.b64encode(
        hmac.new(
            b"secret",
            f"{timestamp}{method}{request_path}{body}".encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("ascii")

    assert (
        sign_bitget_request(
            api_secret="secret",
            timestamp=timestamp,
            method=method,
            request_path=request_path,
            body=body,
        )
        == expected
    )


def test_bitget_auth_headers_redact_secrets() -> None:
    credentials = BitgetCredentials(
        api_key="key-value",
        api_secret="secret-value",
        passphrase="passphrase-value",
    )
    headers = build_bitget_auth_headers(
        credentials=credentials,
        timestamp="16273667805456",
        method="GET",
        request_path="/api/v2/mix/account/accounts",
        query_string="productType=USDT-FUTURES",
    )
    redacted = redact_auth_headers(headers)
    redacted_text = json.dumps(redacted, sort_keys=True)

    assert headers["ACCESS-KEY"] == "key-value"
    assert headers["ACCESS-PASSPHRASE"] == "passphrase-value"
    assert redacted["ACCESS-KEY"] == "[REDACTED]"
    assert redacted["ACCESS-SIGN"] == "[REDACTED]"
    assert redacted["ACCESS-PASSPHRASE"] == "[REDACTED]"
    assert "secret-value" not in redacted_text
    assert "passphrase-value" not in redacted_text
    assert "key-value" not in redacted_text


def test_bitget_credentials_are_loaded_from_env_and_fail_closed() -> None:
    env = {
        "BITGET_API_KEY": "key",
        "BITGET_API_SECRET": "secret",
        "BITGET_PASSPHRASE": "passphrase",
    }

    assert missing_bitget_credential_env(env) == []
    assert bitget_credentials_from_env(env).api_key == "key"

    with pytest.raises(ValueError, match="missing Bitget credential env"):
        bitget_credentials_from_env({"BITGET_API_KEY": "key"})
