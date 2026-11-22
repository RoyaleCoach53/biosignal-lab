"""Self-contained, safe-to-open HTML and machine-readable analysis summaries."""
from __future__ import annotations
import html
import json
from datetime import datetime, timezone
from .models import AnalysisResults
from ._version import __version__


def json_report(result: AnalysisResults) -> str:
    return json.dumps(result.summary(), indent=2, ensure_ascii=False, allow_nan=False)


def html_report(result: AnalysisResults) -> str:
    summary = result.summary()
    safe = lambda value: html.escape(str(value), quote=True)
    def table(rows):
        if not rows:
            return "<p>No results for this section.</p>"
        keys = list(rows[0].keys())
        head = "".join(f"<th>{safe(k)}</th>" for k in keys)
        body = "".join("<tr>" + "".join(f"<td>{safe(r.get(k, ''))}</td>" for k in keys)
                       + "</tr>" for r in rows)
        return f"<div class='scroll'><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>"
    warning = "".join(f"<li>{safe(item)}</li>" for item in result.warnings)
    return f"""<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">
<title>BioSignal Lab — Analysis Report</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font-family:system-ui,Arial,sans-serif;max-width:1100px;margin:auto;padding:30px;color:#182438;background:#f7f9fd}}
h1{{color:#3b2684}}h2{{margin-top:32px}}.meta{{background:#eee9ff;padding:16px;border-radius:8px}}
table{{border-collapse:collapse;background:#fff;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #e5e7eb;padding:9px;text-align:left}}th{{background:#ece7fc}}
.scroll{{overflow-x:auto}}.notice{{border-left:4px solid #d97706;padding:12px;background:#fff9ed}}</style></head><body>
<h1>BioSignal Lab</h1><p>Research signal analysis report • {safe(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))}</p>
<div class="notice"><strong>Not for clinical use.</strong> This software does not diagnose, screen for, or predict medical conditions. Verify every result independently.</div>
<h2>Recording</h2><div class="meta">Source: {safe(summary['source'])}<br>Type: {safe(summary['modality'])}<br>Channels: {summary['n_channels']}<br>Sampling rate: {summary['sfreq_hz']} Hz<br>Duration: {summary['duration_s']} s</div>
<h2>Channel quality metrics</h2>{table(result.channel_metrics)}
<h2>Raw channel metrics (before filtering)</h2>{table(result.raw_channel_metrics)}
<h2>EEG band powers</h2>{table(result.band_powers)}
<h2>Artifact review candidates</h2>{table(result.artifact_intervals)}
<h2>Warnings</h2><ul>{warning or '<li>None</li>'}</ul>
<h2>Reproducibility settings</h2><pre>{safe(json.dumps(summary['config'], indent=2))}</pre>
<p>Generated locally by BioSignal Lab v{safe(__version__)}. No recording data is embedded in this report.</p></body></html>"""
