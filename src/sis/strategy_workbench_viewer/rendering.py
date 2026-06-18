from __future__ import annotations

from html import escape

from sis.strategy_workbench_viewer.models import StrategyWorkbenchViewerManifest


def _badge_class(status: str | None, boundary_violations: list[str]) -> str:
    if boundary_violations:
        return "bad"
    if status is None:
        return "neutral"
    upper = status.upper()
    if "READY" in upper or upper in {"PASS", "OK"}:
        return "good"
    if "NEEDS" in upper or "HOLD" in upper or "PENDING" in upper:
        return "warn"
    if "BLOCK" in upper or "FAIL" in upper or "REJECT" in upper or "RETIRE" in upper:
        return "bad"
    return "neutral"


def render_strategy_workbench_viewer_html(
    manifest: StrategyWorkbenchViewerManifest,
) -> str:
    rows: list[str] = []
    detail_sections: list[str] = []
    for artifact in manifest.source_artifacts:
        status = artifact.status or "n/a"
        badge_class = _badge_class(artifact.status, artifact.boundary_violations)
        summary = "<br>".join(
            f'<span class="mono">{escape(str(key))}</span>: {escape(str(value))}'
            for key, value in artifact.summary.items()
        )
        violations = "".join(
            f"<li>{escape(violation)}</li>" for violation in artifact.boundary_violations
        )
        rows.append(
            "<tr>"
            f"<td>{escape(artifact.title)}</td>"
            f'<td class="mono">{escape(artifact.schema_version or artifact.artifact_format.value)}</td>'
            f'<td><span class="badge {badge_class}">{escape(status)}</span></td>'
            f'<td class="mono path">{escape(artifact.path)}</td>'
            f'<td class="mono">{escape(artifact.sha256[:19])}...</td>'
            "</tr>"
        )
        detail_sections.append(
            f"""
            <section class="artifact" data-search="{escape((artifact.title + " " + artifact.path + " " + status).lower())}">
              <h2>{escape(artifact.title)}</h2>
              <p class="meta"><span class="mono">{escape(artifact.path)}</span></p>
              <p><span class="badge {badge_class}">{escape(status)}</span> <span class="subtle">{escape(artifact.schema_version or artifact.artifact_format.value)}</span></p>
              <div class="summary">{summary or '<span class="subtle">summaryなし</span>'}</div>
              {"<h3>Boundary Violations</h3><ul>" + violations + "</ul>" if violations else ""}
              {f"<h3>Preview</h3><pre>{escape(artifact.preview)}</pre>" if artifact.preview else ""}
            </section>
            """
        )
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Strategy Workbench Viewer</title>
  <style>
    :root {{ color-scheme: light; --ink:#18211f; --muted:#66736f; --line:#d8e0dd; --paper:#f7faf8; --panel:#ffffff; --good:#0d6b45; --warn:#8a5b00; --bad:#a12a2a; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; color:var(--ink); background:var(--paper); }}
    header {{ padding:28px clamp(18px, 4vw, 52px) 18px; border-bottom:1px solid var(--line); background:#ffffff; }}
    main {{ padding:20px clamp(18px, 4vw, 52px) 44px; }}
    h1 {{ margin:0 0 8px; font-size:clamp(24px, 3vw, 38px); letter-spacing:0; }}
    h2 {{ margin:0 0 10px; font-size:20px; letter-spacing:0; }}
    h3 {{ margin:18px 0 8px; font-size:14px; letter-spacing:0; }}
    .subtle, .meta {{ color:var(--muted); }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size:.9em; }}
    .toolbar {{ display:flex; gap:12px; align-items:center; flex-wrap:wrap; margin-top:18px; }}
    input {{ min-width:min(100%, 360px); padding:10px 12px; border:1px solid var(--line); border-radius:6px; font:inherit; background:#fff; }}
    .stats {{ display:flex; gap:10px; flex-wrap:wrap; margin:18px 0; }}
    .stat {{ border:1px solid var(--line); background:#fff; border-radius:6px; padding:10px 12px; min-width:150px; }}
    .stat strong {{ display:block; font-size:22px; }}
    table {{ width:100%; border-collapse:collapse; background:#fff; border:1px solid var(--line); border-radius:6px; overflow:hidden; }}
    th, td {{ padding:10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
    th {{ font-size:12px; color:var(--muted); background:#eef4f1; }}
    .path {{ word-break:break-all; }}
    .badge {{ display:inline-block; padding:3px 7px; border-radius:999px; font-size:12px; border:1px solid currentColor; }}
    .badge.good {{ color:var(--good); }}
    .badge.warn {{ color:var(--warn); }}
    .badge.bad {{ color:var(--bad); }}
    .badge.neutral {{ color:var(--muted); }}
    .artifact {{ margin-top:18px; padding:16px; border:1px solid var(--line); border-radius:6px; background:var(--panel); }}
    .summary {{ line-height:1.7; }}
    pre {{ overflow:auto; max-height:420px; padding:12px; background:#111917; color:#e6f0ec; border-radius:6px; white-space:pre-wrap; word-break:break-word; }}
    footer {{ margin-top:24px; color:var(--muted); font-size:13px; }}
  </style>
</head>
<body>
  <header>
    <h1>Strategy Workbench Viewer</h1>
    <p class="subtle">既存 artifact を読むだけの static viewer です。paper / live 実行許可ではありません。</p>
    <div class="toolbar">
      <label for="filter" class="subtle">Filter</label>
      <input id="filter" type="search" placeholder="schema, status, path で絞る" />
    </div>
  </header>
  <main>
    <div class="stats">
      <div class="stat"><span class="subtle">Artifacts</span><strong>{manifest.artifact_count}</strong></div>
      <div class="stat"><span class="subtle">Boundary violations</span><strong>{manifest.boundary_violation_count}</strong></div>
      <div class="stat"><span class="subtle">Generated</span><strong class="mono">{escape(manifest.created_at.isoformat())}</strong></div>
    </div>
    <table aria-label="artifact summary">
      <thead><tr><th>Artifact</th><th>Schema</th><th>Status</th><th>Path</th><th>Hash</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
    {"".join(detail_sections)}
    <footer>viewer_id: <span class="mono">{escape(manifest.viewer_id)}</span> / html hash は manifest に記録されます。</footer>
  </main>
  <script>
    const filter = document.getElementById("filter");
    const sections = Array.from(document.querySelectorAll(".artifact"));
    filter.addEventListener("input", () => {{
      const query = filter.value.trim().toLowerCase();
      for (const section of sections) {{
        section.hidden = query && !section.dataset.search.includes(query);
      }}
    }});
  </script>
</body>
</html>
"""
