from __future__ import annotations

from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st
import pytest

from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.models import decimal_to_json_string


@given(
    st.decimals(
        min_value=Decimal("0"),
        max_value=Decimal("3000"),
        allow_nan=False,
        allow_infinity=False,
        places=8,
    )
)
def test_decimal_json_roundtrip(value: Decimal) -> None:
    serialized = decimal_to_json_string(value)

    assert Decimal(serialized) == value


def test_ensure_utc_aware_rejects_naive_datetime() -> None:
    with pytest.raises(ValueError, match="UTC aware"):
        ensure_utc_aware("created_at", "2026-06-21T04:00:00")
