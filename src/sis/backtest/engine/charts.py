from __future__ import annotations


def render_line_svg(*, title: str, values: list[float]) -> str:
    if not values:
        return render_placeholder_svg(title=title)
    left = 40
    top = 40
    plot_width = 560
    plot_height = 160
    low = min(values)
    high = max(values)
    span = high - low or 1.0
    points: list[str] = []
    for index, value in enumerate(values):
        x = left + (plot_width * index / max(len(values) - 1, 1))
        y = top + plot_height - ((value - low) / span * plot_height)
        points.append(f"{x:.2f},{y:.2f}")
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="240" '
        'viewBox="0 0 640 240">'
        '<rect width="640" height="240" fill="white"/>'
        f'<text x="24" y="28" font-family="sans-serif" font-size="18">{title}</text>'
        f'<polyline fill="none" stroke="#1f77b4" stroke-width="2" points="{" ".join(points)}"/>'
        "</svg>\n"
    )


def render_placeholder_svg(*, title: str) -> str:
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="240" '
        'viewBox="0 0 640 240">'
        '<rect width="640" height="240" fill="white"/>'
        f'<text x="24" y="48" font-family="sans-serif" font-size="20">{title}</text>'
        "</svg>\n"
    )


def render_bar_svg(*, title: str, values: dict[str, float]) -> str:
    if not values:
        return render_placeholder_svg(title=title)
    height = 240
    left = 40
    top = 52
    bar_height = 24
    gap = 10
    max_value = max(values.values()) or 1.0
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="640" height="240" viewBox="0 0 640 240">',
        '<rect width="640" height="240" fill="white"/>',
        f'<text x="24" y="28" font-family="sans-serif" font-size="18">{title}</text>',
    ]
    for index, (label, value) in enumerate(sorted(values.items())):
        y = top + index * (bar_height + gap)
        if y > height - 30:
            break
        bar_width = 520 * value / max_value
        parts.append(
            f'<text x="24" y="{y + 17}" font-family="sans-serif" font-size="12">{label}</text>'
        )
        parts.append(
            f'<rect x="{left + 140}" y="{y}" width="{bar_width:.2f}" '
            f'height="{bar_height}" fill="#1f77b4"/>'
        )
        parts.append(
            f'<text x="{left + 146 + bar_width:.2f}" y="{y + 17}" '
            f'font-family="sans-serif" font-size="12">{value:g}</text>'
        )
    parts.append("</svg>\n")
    return "".join(parts)
