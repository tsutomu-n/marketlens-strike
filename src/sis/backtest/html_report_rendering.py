from __future__ import annotations

from html import escape
import json
from typing import Any


def _html_json(payload: dict[str, Any]) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return text.replace("&", "\\u0026").replace("<", "\\u003c").replace(">", "\\u003e")


def _object(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def render_strategy_backtest_html(view_model: dict[str, Any]) -> str:
    title = "Strategy Backtest Visual Report"
    data_json = _html_json(view_model)
    summary = _object(view_model.get("summary"))
    label = _object(view_model.get("result_label"))
    return f"""<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <style>
    :root {{
      color-scheme: light;
      --canvas: #eef3f1;
      --ink: #17201d;
      --muted: #5b6762;
      --line: #c4d0cc;
      --panel: #fbfdfc;
      --accent: #0f766e;
      --warn: #b4452d;
      --good: #1f6f49;
      --shadow: 0 12px 32px rgba(20, 38, 33, 0.12);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        linear-gradient(90deg, rgba(0,0,0,0.035) 1px, transparent 1px),
        linear-gradient(0deg, rgba(0,0,0,0.025) 1px, transparent 1px),
        var(--canvas);
      background-size: 28px 28px;
      color: var(--ink);
      font-family: "Hiragino Sans", "Yu Gothic", "Noto Sans JP", system-ui, sans-serif;
      line-height: 1.6;
    }}
    header {{
      padding: 28px clamp(18px, 5vw, 56px) 18px;
      border-bottom: 1px solid var(--line);
      background: rgba(251, 253, 252, 0.9);
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(12px);
    }}
    h1 {{
      margin: 0 0 8px;
      font-family: Georgia, "Times New Roman", serif;
      font-size: clamp(30px, 5vw, 58px);
      line-height: 0.98;
      font-weight: 700;
      letter-spacing: 0;
    }}
    h2 {{
      margin: 0 0 14px;
      font-size: 18px;
      letter-spacing: 0;
    }}
    main {{
      width: min(1260px, 100%);
      margin: 0 auto;
      padding: 22px clamp(14px, 4vw, 36px) 54px;
    }}
    .subtle {{ color: var(--muted); font-size: 14px; }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(0, 1.15fr) minmax(300px, 0.85fr);
      gap: 18px;
      align-items: start;
    }}
    section, .panel {{
      background: rgba(251, 253, 252, 0.94);
      border: 1px solid var(--line);
      box-shadow: var(--shadow);
      padding: 18px;
    }}
    .kpis {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
      margin: 16px 0 18px;
    }}
    .kpi {{
      border: 1px solid var(--line);
      background: #ffffff;
      padding: 12px;
      min-height: 88px;
    }}
    .kpi span {{ display: block; color: var(--muted); font-size: 12px; }}
    .kpi strong {{ display: block; margin-top: 6px; font-size: 22px; overflow-wrap: anywhere; }}
    .label {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 6px 10px;
      border: 1px solid var(--line);
      background: #e5efec;
      font-weight: 700;
    }}
    .label.paper_observation_candidate {{ color: var(--good); }}
    .label.insufficient_evidence, .label.needs_more_validation, .label.weak {{ color: var(--warn); }}
    .chart {{
      width: 100%;
      min-height: 260px;
      border: 1px solid var(--line);
      background: #ffffff;
      margin: 8px 0 18px;
    }}
    .chart svg {{ display: block; width: 100%; height: 260px; }}
    .filters {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: end;
      margin: 10px 0 14px;
    }}
    label {{ display: grid; gap: 4px; color: var(--muted); font-size: 13px; }}
    input, button {{
      border: 1px solid var(--line);
      background: #ffffff;
      color: var(--ink);
      padding: 8px 10px;
      font: inherit;
    }}
    button {{ cursor: pointer; font-weight: 700; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      background: #ffffff;
      font-size: 13px;
    }}
    th, td {{
      border-bottom: 1px solid var(--line);
      padding: 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{ color: var(--muted); font-weight: 700; }}
    .stack {{ display: grid; gap: 18px; }}
    .list {{ margin: 0; padding-left: 18px; }}
    .mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    @media (max-width: 860px) {{
      header {{ position: static; }}
      .layout, .kpis {{ grid-template-columns: 1fr; }}
      .chart svg {{ height: 220px; }}
      table {{ font-size: 12px; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="label {escape(str(label.get("code") or ""))}">{escape(str(label.get("label") or "未判定"))}</div>
    <h1>Strategy Backtest Visual Report</h1>
    <div class="subtle">戦略: <span class="mono">{escape(str(summary.get("strategy_id") or "unknown"))}</span> / generated: <span class="mono">{escape(str(view_model.get("created_at") or ""))}</span></div>
  </header>
  <main>
    <div class="kpis" id="kpis"></div>
    <div class="layout">
      <div class="stack">
        <section>
          <h2>累積損益</h2>
          <p class="subtle">各 signal return を順番に積み上げた概算です。注文送信や live 接続は行っていません。</p>
          <div class="chart" id="equity-chart"></div>
        </section>
        <section>
          <h2>Benchmark 比較</h2>
          <p class="subtle">strategy と benchmark の累積 return を同じ目盛りで表示します。artifact がない場合は空になります。</p>
          <div class="chart" id="benchmark-chart"></div>
        </section>
        <section>
          <h2>期間で絞る</h2>
          <div class="filters">
            <label>開始日<input type="date" id="start-date"></label>
            <label>終了日<input type="date" id="end-date"></label>
            <button type="button" id="reset-filter">全期間</button>
          </div>
          <div class="subtle" id="filter-summary"></div>
          <div style="overflow-x:auto">
            <table>
              <thead>
                <tr>
                  <th>時刻</th><th>symbol</th><th>side</th><th>return</th><th>cost bps</th><th>signal id</th>
                </tr>
              </thead>
              <tbody id="trade-rows"></tbody>
            </table>
          </div>
        </section>
      </div>
      <aside class="stack">
        <section>
          <h2>読み方</h2>
          <p>{escape(str(label.get("description") or ""))}</p>
          <h3>理由</h3>
          <ul class="list" id="reason-list"></ul>
          <h3>次に見るもの</h3>
          <ul class="list" id="next-list"></ul>
        </section>
        <section>
          <h2>期間別</h2>
          <div id="periods"></div>
        </section>
        <section>
          <h2>Stress</h2>
          <div id="stress"></div>
        </section>
        <section>
          <h2>Diagnostics</h2>
          <div id="diagnostics"></div>
        </section>
        <section>
          <h2>境界</h2>
          <p class="subtle">このHTMLは既存 artifact を読むだけです。paper / live 実行許可ではありません。</p>
          <ul class="list">
            <li>paper_only=true</li>
            <li>permits_live_order=false</li>
            <li>wallet_used=false</li>
            <li>exchange_write_used=false</li>
          </ul>
        </section>
      </aside>
    </div>
  </main>
  <script type="application/json" id="report-data">{data_json}</script>
  <script>
    const data = JSON.parse(document.getElementById("report-data").textContent);
    const fmtPct = (v) => Number.isFinite(v) ? (v * 100).toFixed(2) + "%" : "n/a";
    const fmtMoney = (v) => Number.isFinite(v) ? "$" + v.toLocaleString(undefined, {{maximumFractionDigits: 2}}) : "n/a";
    const el = (id) => document.getElementById(id);
    const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (ch) => ({{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}}[ch]));

    function kpi(label, value) {{
      return `<div class="kpi"><span>${{escapeHtml(label)}}</span><strong>${{escapeHtml(value)}}</strong></div>`;
    }}

    function renderKpis() {{
      const s = data.summary;
      el("kpis").innerHTML = [
        kpi("total return", fmtPct(s.total_return)),
        kpi("net PnL", fmtMoney(s.net_pnl_usd)),
        kpi("trade count", s.trade_count ?? "n/a"),
        kpi("max drawdown", fmtPct(s.max_drawdown))
      ].join("");
    }}

    function chartDomain(rows, specs) {{
      const values = specs.flatMap((spec) => rows.map((r) => Number(r[spec.key])).filter((v) => Number.isFinite(v)));
      const min = Math.min(...values, 0);
      const max = Math.max(...values, 0);
      return [min, Math.max(max - min, 0.000001)];
    }}

    function pathFor(rows, key, width, height, domain) {{
      const [min, span] = domain;
      return rows.map((r, i) => {{
        const x = rows.length === 1 ? width / 2 : (i / (rows.length - 1)) * width;
        const value = Number(r[key]);
        const y = Number.isFinite(value) ? height - ((value - min) / span) * height : height;
        return `${{i === 0 ? "M" : "L"}}${{x.toFixed(2)}} ${{y.toFixed(2)}}`;
      }}).join(" ");
    }}

    function renderLineChart(target, rows, specs) {{
      const width = 760;
      const height = 230;
      if (!rows.length) {{
        el(target).innerHTML = '<p class="subtle" style="padding:14px">表示できる series がありません。</p>';
        return;
      }}
      const domain = chartDomain(rows, specs);
      const lines = specs.map((spec) => {{
        const d = pathFor(rows, spec.key, width, height, domain);
        return `<path d="${{d}}" fill="none" stroke="${{spec.color}}" stroke-width="3" stroke-linecap="round"></path>`;
      }}).join("");
      const legend = specs.map((spec) => `<span style="color:${{spec.color}}">${{escapeHtml(spec.label)}}</span>`).join(" / ");
      el(target).innerHTML = `<svg viewBox="0 0 ${{width}} ${{height}}" role="img" aria-label="${{escapeHtml(target)}} line chart"><line x1="0" y1="${{height}}" x2="${{width}}" y2="${{height}}" stroke="#c4d0cc"></line>${{lines}}</svg><div class="subtle" style="padding:0 10px 10px">${{legend}}</div>`;
    }}

    function selectedTrades() {{
      const start = el("start-date").value;
      const end = el("end-date").value;
      return data.visual_data.trades.filter((row) => {{
        if (start && row.date < start) return false;
        if (end && row.date > end) return false;
        return true;
      }});
    }}

    function renderTrades() {{
      const rows = selectedTrades();
      const total = rows.reduce((acc, row) => (1 + acc) * (1 + Number(row.signal_return)) - 1, 0);
      el("filter-summary").textContent = `${{rows.length}} trades / filtered return ${{fmtPct(total)}}`;
      el("trade-rows").innerHTML = rows.map((row) => `<tr><td>${{escapeHtml(row.ts_signal)}}</td><td>${{escapeHtml(row.canonical_symbol)}}</td><td>${{escapeHtml(row.side)}}</td><td>${{fmtPct(Number(row.signal_return))}}</td><td>${{escapeHtml(row.cost_drag_bps)}}</td><td class="mono">${{escapeHtml(row.signal_id)}}</td></tr>`).join("");
    }}

    function renderLists() {{
      el("reason-list").innerHTML = data.result_label.reasons.map((x) => `<li>${{escapeHtml(x)}}</li>`).join("");
      el("next-list").innerHTML = data.result_label.next_checks.map((x) => `<li>${{escapeHtml(x)}}</li>`).join("");
      el("periods").innerHTML = data.visual_data.periods.map((row) => `<p><strong>${{escapeHtml(row.period)}}</strong><br><span class="subtle">${{escapeHtml(row.trade_count)}} trades / ${{fmtPct(Number(row.total_return))}}</span></p>`).join("");
      el("stress").innerHTML = data.visual_data.stress_scenarios.map((row) => `<p><strong>${{escapeHtml(row.scenario_id)}}</strong><br><span class="subtle">${{fmtPct(Number(row.stressed_total_return))}} / add ${{escapeHtml(row.total_additional_bps_per_trade ?? "n/a")}} bps</span></p>`).join("");
      const compact = (v) => (Array.isArray(v) || (v && typeof v === "object")) ? JSON.stringify(v).slice(0, 180) : v;
      const facts = (obj) => Object.entries(obj ?? {{}}).slice(0, 6).map(([k, v]) => `${{escapeHtml(k)}}=${{escapeHtml(compact(v))}}`).join("<br>") || "n/a";
      el("diagnostics").innerHTML = `<p><strong>Rolling stability</strong><br><span class="subtle">${{facts(data.visual_data.rolling_stability_summary)}}</span></p><p><strong>Regime split</strong><br><span class="subtle">${{facts(data.visual_data.regime_split_summary)}}</span></p><p><strong>Comparison</strong><br><span class="subtle">${{facts(data.visual_data.comparison_diagnostics)}}</span></p>`;
    }}

    function initFilters() {{
      const dates = data.visual_data.trades.map((row) => row.date).filter(Boolean).sort();
      if (dates.length) {{
        el("start-date").value = dates[0];
        el("end-date").value = dates[dates.length - 1];
      }}
      el("start-date").addEventListener("change", renderTrades);
      el("end-date").addEventListener("change", renderTrades);
      el("reset-filter").addEventListener("click", () => {{
        if (dates.length) {{
          el("start-date").value = dates[0];
          el("end-date").value = dates[dates.length - 1];
        }}
        renderTrades();
      }});
    }}

    renderKpis();
    renderLineChart("equity-chart", data.visual_data.equity_curve, [
      {{key: "cumulative_return", color: "#0f766e", label: "cumulative return"}},
      {{key: "drawdown", color: "#b4452d", label: "drawdown"}}
    ]);
    renderLineChart("benchmark-chart", data.visual_data.benchmark_curve, [
      {{key: "strategy_return", color: "#0f766e", label: "strategy"}},
      {{key: "benchmark_return", color: "#5465a9", label: "benchmark"}},
      {{key: "active_return", color: "#b4452d", label: "active"}}
    ]);
    renderLists();
    initFilters();
    renderTrades();
  </script>
</body>
</html>
"""
