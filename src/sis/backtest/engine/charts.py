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
