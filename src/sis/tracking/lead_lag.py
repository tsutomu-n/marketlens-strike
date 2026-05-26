from __future__ import annotations


def best_lag_correlation(
    real_prices: list[float],
    venue_prices: list[float],
    *,
    max_lag: int = 3,
) -> tuple[int, float | None]:
    if len(real_prices) != len(venue_prices) or len(real_prices) < 3:
        return 0, None

    def corr(xs: list[float], ys: list[float]) -> float | None:
        if len(xs) < 2:
            return None
        x_mean = sum(xs) / len(xs)
        y_mean = sum(ys) / len(ys)
        num = sum((x - x_mean) * (y - y_mean) for x, y in zip(xs, ys, strict=False))
        x_var = sum((x - x_mean) ** 2 for x in xs)
        y_var = sum((y - y_mean) ** 2 for y in ys)
        if x_var <= 0 or y_var <= 0:
            return None
        return num / ((x_var * y_var) ** 0.5)

    best_lag = 0
    best_corr: float | None = None
    for lag in range(-max_lag, max_lag + 1):
        if lag < 0:
            xs = real_prices[-lag:]
            ys = venue_prices[: len(xs)]
        elif lag > 0:
            ys = venue_prices[lag:]
            xs = real_prices[: len(ys)]
        else:
            xs = real_prices
            ys = venue_prices
        score = corr(xs, ys)
        if score is None:
            continue
        if best_corr is None or abs(score) > abs(best_corr):
            best_corr = score
            best_lag = lag
    return best_lag, best_corr
