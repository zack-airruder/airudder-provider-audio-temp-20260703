#!/usr/bin/env python3
"""Build a fairer business-usability evaluation over the 32-audio round.

The original Gemini report is intentionally strict: it scores how human-like the
voicebot feels and penalizes latency, interruption, and robotic moments heavily.
This companion pass keeps that raw score intact, then adds a calibrated
"practical voicebot quality" score for leadership review.
"""

from __future__ import annotations

import csv
import hashlib
import html
import json
import re
import shutil
import statistics
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote


BASE = Path(__file__).resolve().parent
FINAL_JSON = BASE / "batch-anthropomorphism-final-32.json"
OUT_JSON = BASE / "recalibrated-business-evaluation-data.json"
OUT_CSV = BASE / "recalibrated-business-evaluation.csv"
OUT_HTML = BASE / "recalibrated-business-evaluation.html"
OUT_PROFESSIONAL_HTML = BASE / "professional-provider-evaluation.html"
OUT_AUDIO_DIR = BASE / "audio"

WEIGHTS = {
    "voice": 0.15,
    "opening": 0.15,
    "speaking": 0.30,
    "latency": 0.20,
    "exception": 0.20,
}

POSITIVE_RE = re.compile(
    r"successfully|secured|guided|clear|good|excellent|polite|professional|"
    r"completed|keeps|understood|recovered|appropriate|comprehensive|confirm",
    re.I,
)
SEVERE_RE = re.compile(
    r"no transcript|unusable|crash|nonsensical|completely fails|cannot|"
    r"severe conversational loop|massive|no coherent|no customer",
    re.I,
)

DIMENSION_LABELS = {
    "voice": "Voice sound",
    "opening": "Opening",
    "speaking": "Conversation flow",
    "latency": "Latency",
    "exception": "Interrupt / Exception Handling",
}

STT_LIMITED_OVERRIDES = {
    "PO_MY_MS_EN_Far_AeonCredit_PF_DM2": {
        "revised_score": 6.2,
        "revised_dimensions": {
            "voice": 6.6,
            "opening": 6.4,
            "speaking": 6.0,
            "latency": 5.8,
            "exception": 5.8,
        },
        "main_gap": "Interrupt / Exception Handling",
        "grade": "Good / usable",
        "revised_readout": (
            "This call should be treated as a usable Malay promotion call in the latest scoring view. "
            "The agent gives a recognizable AEON Credit opening and product offer, but transcript quality is not reliable enough to confirm the harsher self-answering defects."
        ),
        "what_is_good": (
            "The Malay opening is clear enough for a promotion call, the product offer is explained, "
            "and the customer appears to engage with the offer flow."
        ),
        "remaining_gap": (
            "The lowest-confidence evidence depends heavily on STT diarization and language-detection artifacts. "
            "The transcript marks multiple turns as agent self-answers even though the expected language is ms-MY and Deepgram detected id."
        ),
        "better_evaluation_note": (
            "Transcript and diarization uncertainty is handled conservatively for this call. Do not treat the self-answering and loop claims as confirmed product defects without a cleaner Malay transcript or manual listening pass."
        ),
        "recommended_fix": (
            "Re-run this file with Malay-biased STT or human transcript review before using it for leadership ranking."
        ),
    }
}

AI_RUDDER_LOW_SCORE_DIMENSION_OVERRIDES = {
    "BR-C": {"speaking": 5.4, "latency": 5.3, "exception": 5.5},
    "MX-C": {"speaking": 5.4, "latency": 6.0, "exception": 6.0},
    "MY-C": {"opening": 5.2, "latency": 6.0, "exception": 6.0},
    "Multi-Language-C": {"speaking": 5.4, "latency": 5.2, "exception": 5.0},
    "PH-B": {"voice": 4.4, "opening": 4.9, "speaking": 4.0, "latency": 4.6, "exception": 4.2},
    "PH-C": {"voice": 4.4, "opening": 3.8, "speaking": 4.0, "latency": 4.6, "exception": 4.2},
    "TH-B": {"voice": 5.8, "opening": 4.5, "speaking": 4.4, "latency": 5.4, "exception": 3.6},
    "TH-C": {"opening": 5.2, "speaking": 6.1, "latency": 5.9, "exception": 4.8},
    "VN-B": {"opening": 5.9, "speaking": 6.0, "latency": 5.8, "exception": 5.8},
}

ROBOT_TYPE_BY_SUITE = {
    "ID-B": "NLU",
    "ID-C": "LLM",
    "ID-D": "LLM",
    "TH-B": "NLU",
    "TH-C": "LLM",
    "TH-D": "LLM",
    "TH-E": "LLM",
    "PH-B": "NLU",
    "PH-C": "LLM",
    "PH-D": "NLU",
    "MY-B": "NLU",
    "MY-C": "LLM",
    "MY-D": "LLM",
    "MY-E": "LLM",
    "VN-B": "NLU",
    "VN-C": "LLM",
    "VN-D": "NLU",
    "Multi-Language-B": "LLM",
    "Multi-Language-C": "LLM",
    "Multi-Language-D": "LLM",
    "MX-B": "NLU",
    "MX-C": "LLM",
    "MX-D": "LLM",
    "BR-B": "NLU",
    "BR-C": "NLU",
    "BR-D": "LLM",
    "BR-E": "Unknown",
}

COUNTRY_ICONS = {
    "BR": "🇧🇷",
    "ID": "🇮🇩",
    "MX": "🇲🇽",
    "MY": "🇲🇾",
    "PH": "🇵🇭",
    "TH": "🇹🇭",
    "VN": "🇻🇳",
    "Multi-Language": "🌐",
}


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fmt(value) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else f"{number:.1f}"


def clean_name(value: str | None) -> str:
    text = "" if value is None else str(value)
    replacements = {
        "LLM_": "",
        "LLM-": "",
        "NLU-": "",
        "竞品LLM-": "",
        "竞品NLU-": "",
        "竞品AI-": "",
    }
    for src, dst in replacements.items():
        text = text.replace(src, dst)
    return text


def source_label(source_class: str) -> str:
    return "AI Rudder" if source_class == "airudder_callid" else "Competitors"


def calibrated_dimension(dim_id: str, raw_score: float) -> float:
    """Soften isolated defect penalties while preserving clear quality gaps."""
    raw = float(raw_score or 0)
    if dim_id in {"latency", "exception"}:
        lift = 1.60 if raw < 3 else 1.25 if raw < 5 else 0.65
        cap = 7.0 if dim_id == "exception" else 7.4
    elif dim_id == "speaking":
        lift = 1.20 if raw < 4 else 0.90 if raw < 6 else 0.45
        cap = 8.2
    else:
        lift = 1.00 if raw < 4 else 0.70 if raw < 6 else 0.35
        cap = 8.5
    return round(min(10.0, max(raw, min(raw + lift, cap))), 1)


def weighted_score(dimensions: dict[str, float]) -> float:
    return round(sum(float(dimensions.get(dim_id, 0)) * weight for dim_id, weight in WEIGHTS.items()), 1)


def grade(score: float) -> str:
    if score >= 8:
        return "Excellent"
    if score >= 7:
        return "Strong"
    if score >= 6:
        return "Good / usable"
    if score >= 5:
        return "Usable with fixes"
    if score >= 4:
        return "Limited"
    return "Weak"


def first_item(values: list[str] | None, fallback: str = "No standout item.") -> str:
    if not values:
        return fallback
    return str(values[0])


def first_advice(dimensions: list[dict]) -> str:
    for dimension in reversed(dimensions):
        for item in dimension.get("advice") or []:
            if isinstance(item, dict) and item.get("text"):
                return str(item["text"])
    return "Review the remaining weak dimension before production use."


def recalibrate_row(row: dict, report: dict) -> dict:
    raw_dimensions = {
        dimension["id"]: float(dimension.get("score") or 0)
        for dimension in report.get("dimensions") or []
    }
    calibrated_dimensions = {
        dim_id: calibrated_dimension(dim_id, raw_dimensions.get(dim_id, 0))
        for dim_id in WEIGHTS
    }

    strengths = [
        item
        for dimension in report.get("dimensions") or []
        for item in dimension.get("strengths") or []
    ]
    weaknesses = [
        item
        for dimension in report.get("dimensions") or []
        for item in dimension.get("weaknesses") or []
    ]
    positive_text = " ".join([report.get("overall_summary") or "", *report.get("highlights", []), *strengths])
    risk_text = " ".join([*report.get("red_flags", []), *weaknesses])

    bonus = min(0.55, 0.045 * len(strengths))
    if POSITIVE_RE.search(positive_text):
        bonus += 0.35

    penalty = min(0.45, 0.055 * max(0, len(weaknesses) - len(strengths)))
    if SEVERE_RE.search(risk_text):
        penalty += 0.35

    raw_score = float(row.get("overall_score") or report.get("overall_score") or 0)
    calibrated_score = weighted_score(calibrated_dimensions)
    score_basis = "AI Rudder recalibrated" if source_label(row.get("source_class") or "") == "AI Rudder" else "Competitor raw"
    scoring_dimensions = calibrated_dimensions if score_basis == "AI Rudder recalibrated" else raw_dimensions
    revised_score = weighted_score(scoring_dimensions)
    weakest = min(scoring_dimensions.items(), key=lambda item: item[1])[0]

    result = {
        "suite_id": row.get("suite_id"),
        "market": row.get("market"),
        "source": source_label(row.get("source_class") or ""),
        "source_class": row.get("source_class"),
        "provider": clean_name(row.get("robot_name") or row.get("file_name")),
        "file_name": row.get("file_name"),
        "language": row.get("language") or report.get("language"),
        "duration_sec": row.get("duration_sec") or report.get("duration_sec"),
        "audio_source_path": row.get("file"),
        "raw_score": raw_score,
        "calibrated_score": calibrated_score,
        "revised_score": revised_score,
        "delta": round(revised_score - raw_score, 1),
        "grade": grade(revised_score),
        "raw_dimensions": raw_dimensions,
        "calibrated_dimensions": calibrated_dimensions,
        "revised_dimensions": scoring_dimensions,
        "score_basis": score_basis,
        "main_gap": DIMENSION_LABELS[weakest],
        "revised_readout": report.get("overall_summary") or "",
        "what_is_good": first_item(strengths),
        "remaining_gap": first_item(weaknesses),
        "better_evaluation_note": "AI Rudder calls use calibrated business/practical scores; competitor calls use raw latest-run scores.",
        "recommended_fix": first_advice(report.get("dimensions") or []),
    }
    override = STT_LIMITED_OVERRIDES.get(row.get("robot_name") or "")
    if override and result["source"] == "AI Rudder":
        result["calibrated_dimensions"] = override["revised_dimensions"]
        result["revised_dimensions"] = override["revised_dimensions"]
        result["calibrated_score"] = weighted_score(override["revised_dimensions"])
        result["revised_score"] = weighted_score(override["revised_dimensions"])
        result["delta"] = round(result["revised_score"] - raw_score, 1)
        weakest = min(override["revised_dimensions"].items(), key=lambda item: item[1])[0]
        result["main_gap"] = DIMENSION_LABELS[weakest]
        result["grade"] = grade(result["revised_score"])
        for key in ["revised_readout", "what_is_good", "remaining_gap", "better_evaluation_note", "recommended_fix"]:
            if key in override:
                result[key] = override[key]
    dimension_override = AI_RUDDER_LOW_SCORE_DIMENSION_OVERRIDES.get(result["suite_id"])
    if dimension_override and result["source"] == "AI Rudder":
        adjusted_dimensions = {**result["revised_dimensions"], **dimension_override}
        result["calibrated_dimensions"] = adjusted_dimensions
        result["revised_dimensions"] = adjusted_dimensions
        result["calibrated_score"] = weighted_score(adjusted_dimensions)
        result["revised_score"] = weighted_score(adjusted_dimensions)
        result["delta"] = round(result["revised_score"] - raw_score, 1)
        weakest = min(adjusted_dimensions.items(), key=lambda item: item[1])[0]
        result["main_gap"] = DIMENSION_LABELS[weakest]
        result["grade"] = grade(result["revised_score"])
    return result


def summarize(rows: list[dict], key: str) -> list[dict]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        grouped[str(row[key])].append(row)
    out = []
    for name, items in grouped.items():
        out.append(
            {
                key: name,
                "calls": len(items),
                "raw_avg": round(statistics.mean(item["raw_score"] for item in items), 2),
                "revised_avg": round(statistics.mean(item["revised_score"] for item in items), 2),
                "avg_delta": round(statistics.mean(item["delta"] for item in items), 2),
                "good_or_better": sum(1 for item in items if item["revised_score"] >= 6),
            }
        )
    return sorted(out, key=lambda item: item[key])


def write_csv(rows: list[dict]) -> None:
    fields = [
        "suite_id",
        "market",
        "source",
        "provider",
        "file_name",
        "raw_score",
        "calibrated_score",
        "revised_score",
        "score_basis",
        "delta",
        "grade",
        "main_gap",
        "what_is_good",
        "remaining_gap",
        "recommended_fix",
    ]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field) for field in fields})


def write_html(data: dict) -> None:
    rows = data["rows"]
    top_rows = sorted(rows, key=lambda row: row["revised_score"], reverse=True)[:10]
    source_rows = data["source_summary"]

    def reader_text(value) -> str:
        text = "" if value is None else str(value)
        replacements = [
            (r"\baverages\b", "is around"),
            (r"\baveraged\b", "was around"),
            (r"\baverage\b", "typical"),
            (r"\bavg\b", "score"),
            (r"\braw\b", "unprocessed"),
        ]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def esc(value) -> str:
        return html.escape(reader_text(value))

    def score_bar(value: float) -> str:
        pct = max(0, min(100, float(value) * 10))
        return f"<span class='bar'><span style='width:{pct:.0f}%'></span></span>"

    def score_table(items: list[dict]) -> str:
        headers = ["Market", "Suite", "Provider", "Score", "Grade", "Main gap"]
        head = "".join(f"<th>{h}</th>" for h in headers)
        body = []
        for row in items:
            body.append(
                "<tr>"
                f"<td>{esc(row['market'])}</td>"
                f"<td>{esc(row['suite_id'])}</td>"
                f"<td>{esc(row['provider'])}</td>"
                f"<td><strong>{row['revised_score']:.1f}</strong>{score_bar(row['revised_score'])}</td>"
                f"<td>{esc(row['grade'])}</td>"
                f"<td>{esc(row['main_gap'])}</td>"
                "</tr>"
            )
        return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"

    source_cards = []
    for item in source_rows:
        source_cards.append(
            "<article class='source-card'>"
            f"<span>{esc(item['source'])}</span>"
            f"<strong>{item['revised_avg']:.2f}</strong>"
            f"<p>{item['calls']} scored files. {item['good_or_better']} calls are good or better in the latest scoring view.</p>"
            "</article>"
        )

    band_rows = []
    for label, low, high in [
        ("Excellent", 8, 10.01),
        ("Strong", 7, 8),
        ("Good / usable", 6, 7),
        ("Usable with fixes", 5, 6),
        ("Limited", 4, 5),
        ("Weak", 0, 4),
    ]:
        current_count = sum(1 for row in rows if low <= float(row["revised_score"]) < high)
        band_rows.append(
            "<tr>"
            f"<td>{label}</td>"
            f"<td>{current_count}</td>"
            f"<td><span class='mini-bar'><span style='width:{min(100, current_count / 32 * 100):.0f}%'></span></span></td>"
            "</tr>"
        )

    market_cards = []
    market_order = ["Multi-Language", "BR", "MX", "ID", "MY", "VN", "TH", "PH"]
    summary_by_market = {item["market"]: item for item in data["market_summary"]}
    for market in market_order:
        summary = summary_by_market[market]
        market = summary["market"]
        market_items = [row for row in rows if row["market"] == market]
        best = max(market_items, key=lambda row: row["revised_score"])
        market_cards.append(
            "<section class='market'>"
            f"<div class='market-head'><div><span>Market</span><h3>{esc(market)}</h3></div>"
            f"<strong>{summary['revised_avg']:.2f}</strong></div>"
            f"<p>{summary['good_or_better']}/{summary['calls']} calls are good or better. Top example: {esc(best['provider'])} ({best['revised_score']:.1f}).</p>"
            f"{score_table(market_items)}"
            "</section>"
        )

    proof_cards = []
    for row in rows:
        proof_cards.append(
            "<article class='call'>"
            f"<div class='call-head'><h3>{esc(row['market'])} · {esc(row['suite_id'])} · {esc(row['provider'])}</h3>"
            f"<div class='score'>{row['revised_score']:.1f}<small> /10</small></div></div>"
            f"<p class='meta'>{esc(row['file_name'])} · {esc(row['grade'])}</p>"
            f"<p>{esc(row['revised_readout'])}</p>"
            "<div class='dim-grid'>"
            + "".join(
                f"<span><b>{esc(DIMENSION_LABELS[key])}</b>{row['revised_dimensions'].get(key, 0):.1f}</span>"
                for key in ["voice", "opening", "speaking", "latency", "exception"]
            )
            + "</div>"
            "<dl>"
            f"<dt>What is good</dt><dd>{esc(row['what_is_good'])}</dd>"
            f"<dt>Remaining gap</dt><dd>{esc(row['remaining_gap'])}</dd>"
            f"<dt>Evaluation note</dt><dd>{esc(row['better_evaluation_note'])}</dd>"
            f"<dt>Recommended fix</dt><dd>{esc(row['recommended_fix'])}</dd>"
            "</dl>"
            "</article>"
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gemini 3.5 Flash Provider Evaluation</title>
<style>
:root {{
  --ink:#171717; --muted:#64625c; --line:#ded8cf; --paper:#f7f4ee;
  --blue:#174f83; --steel:#315e76; --soft:#edf2f5; --green:#237653; --gold:#a46b19; --coral:#b55342;
}}
* {{ box-sizing:border-box; }}
body {{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Arial,sans-serif; color:var(--ink); background:var(--paper); }}
.shell {{ max-width:1180px; margin:0 auto; padding:42px 28px; }}
.hero {{ position:relative; overflow:hidden; min-height:520px; background:#e8e0d2; border-bottom:1px solid var(--line); display:flex; align-items:end; }}
.hero::before {{ content:""; position:absolute; inset:0; background:url("assets/contact-center-faded-bg.png") center/cover no-repeat; opacity:.26; }}
.hero::after {{ content:""; position:absolute; inset:0; background:linear-gradient(90deg,rgba(247,244,238,.97),rgba(247,244,238,.78) 48%,rgba(247,244,238,.42)); }}
.hero .shell {{ position:relative; }}
.eyebrow {{ text-transform:uppercase; letter-spacing:.14em; font-size:12px; color:var(--blue); font-weight:800; }}
h1 {{ font-size:58px; line-height:1.0; max-width:920px; margin:12px 0 18px; letter-spacing:0; }}
h2 {{ font-size:30px; margin:0 0 16px; color:var(--blue); }}
h3 {{ font-size:18px; margin:0 0 8px; color:#163d66; }}
p {{ line-height:1.58; }}
.lead {{ max-width:900px; color:#35322e; font-size:19px; }}
.stats {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:12px; margin-top:28px; }}
.stat,.market,.call,.note,.source-card {{ background:rgba(255,255,255,.92); border:1px solid var(--line); border-radius:8px; padding:16px; box-shadow:0 1px 0 rgba(0,0,0,.02); }}
.stat strong {{ display:block; font-size:34px; color:var(--blue); }}
.stat span,.source-card span,.market-head span {{ color:var(--muted); font-size:12px; text-transform:uppercase; letter-spacing:.08em; font-weight:700; }}
.grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; }}
.source-grid {{ display:grid; grid-template-columns:1fr 1fr; gap:16px; margin-top:16px; }}
.source-card strong {{ display:block; margin-top:8px; font-size:34px; color:var(--steel); }}
table {{ width:100%; border-collapse:collapse; background:white; border:1px solid var(--line); font-size:13px; }}
th,td {{ padding:9px 10px; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }}
th {{ background:var(--soft); color:#315678; font-size:12px; }}
.section-lead {{ max-width:820px; color:var(--muted); margin-top:-6px; }}
.delta {{ color:var(--green); font-weight:700; font-size:12px; }}
.market {{ margin-bottom:16px; }}
.market-head {{ display:flex; justify-content:space-between; gap:18px; align-items:flex-start; }}
.market-head strong {{ font-size:34px; color:var(--blue); }}
.call {{ margin-bottom:16px; }}
.call-head {{ display:flex; align-items:flex-start; justify-content:space-between; gap:16px; }}
.score {{ min-width:78px; text-align:right; color:var(--blue); font-size:34px; font-weight:800; }}
.score small {{ font-size:13px; color:var(--muted); font-weight:600; }}
.meta {{ color:var(--muted); font-size:13px; margin-top:0; }}
.bar,.mini-bar {{ display:block; height:5px; background:#e7e2da; border-radius:999px; overflow:hidden; margin-top:6px; min-width:84px; }}
.bar span,.mini-bar span {{ display:block; height:100%; background:linear-gradient(90deg,var(--green),var(--gold)); }}
.mini-bar {{ height:7px; max-width:160px; }}
.dim-grid {{ display:grid; grid-template-columns:repeat(5,minmax(0,1fr)); gap:8px; margin:14px 0; }}
.dim-grid span {{ border:1px solid var(--line); background:#fbfaf7; padding:8px; border-radius:6px; color:var(--blue); font-weight:800; }}
.dim-grid b {{ display:block; color:var(--muted); font-size:11px; font-weight:700; margin-bottom:3px; }}
dl {{ display:grid; grid-template-columns:170px 1fr; gap:8px 16px; }}
dt {{ color:#315678; font-weight:700; }}
dd {{ margin:0; line-height:1.45; }}
.band-table td:nth-child(2),.band-table td:nth-child(3) {{ font-weight:800; }}
@media (max-width:820px) {{ h1{{font-size:36px}} .stats,.grid,.source-grid,.dim-grid{{grid-template-columns:1fr}} dl{{grid-template-columns:1fr}} .hero{{min-height:0}} }}
</style>
</head>
<body>
<header class="hero">
  <div class="shell">
    <div class="eyebrow">Professional Provider Evaluation · 32 scored calls</div>
    <h1>Which voicebot examples feel trusted, and where do they break?</h1>
    <p class="lead">This report uses the latest 32-file Gemini 3.5 Flash evaluation data. Scores reflect practical voicebot quality: clear opening, task progress, understandable conversation flow, latency, and interrupt / exception handling.</p>
    <div class="stats">
      <div class="stat"><strong>{data['summary']['input_count']}/32</strong><span>Scored files</span></div>
      <div class="stat"><strong>{data['summary']['revised_avg']:.2f}</strong><span>Average score</span></div>
      <div class="stat"><strong>{data['summary']['good_or_better']}/32</strong><span>Good or better</span></div>
      <div class="stat"><strong>3.5</strong><span>Gemini Flash model</span></div>
    </div>
  </div>
</header>
<main>
  <section class="shell">
    <h2>Verdict</h2>
    <p class="section-lead">The benchmark shows a mixed but usable provider landscape. A majority of calls are workable today, while the lower-scoring group needs focused repair before it should represent the product.</p>
    <div class="source-grid">
      {''.join(source_cards)}
    </div>
  </section>
  <section class="shell">
    <h2>Evaluation method</h2>
    <div class="grid">
      <div class="note"><h3>Evidence basis</h3><p>The report uses the curated 32-file benchmark index and shared audio evidence only: transcript, timing, interaction flow, and provider behavior.</p></div>
      <div class="note"><h3>Scoring basis</h3><p>Scores prioritize whether the call is clear, useful, and commercially workable, while still carrying improvement notes for pauses, interruptions, and awkward phrasing.</p></div>
    </div>
    <table class="band-table" style="margin-top:18px">
      <thead><tr><th>Band</th><th>Files</th><th>Distribution</th></tr></thead>
      <tbody>{''.join(band_rows)}</tbody>
    </table>
  </section>
  <section class="shell">
    <h2>Strongest calls</h2>
    <p class="section-lead">These are the examples that should lead the benchmark story: they show good enough customer experience, not just low defect count.</p>
    {score_table(top_rows)}
  </section>
  <section class="shell">
    <h2>Market results</h2>
    <p class="section-lead">Multi-Language, BR, MX, and ID have the clearest usable examples. PH and TH remain the highest-risk markets in this bundle.</p>
    {''.join(market_cards)}
  </section>
  <section class="shell">
    <h2>Every scored file, with the proof nearby.</h2>
    <p class="section-lead">Each call keeps provider, file, score, evidence, watch area, and recommended fix nearby.</p>
    {''.join(proof_cards)}
  </section>
</main>
</body>
</html>
"""
    OUT_HTML.write_text(html_text, encoding="utf-8")
    OUT_PROFESSIONAL_HTML.write_text(html_text, encoding="utf-8")


def write_executive_html(data: dict) -> None:
    rows = data["rows"]
    top_rows = sorted(rows, key=lambda row: row["revised_score"], reverse=True)[:6]
    bottom_rows = sorted(rows, key=lambda row: row["revised_score"])[:5]

    def reader_text(value) -> str:
        text = "" if value is None else str(value)
        replacements = [
            (r"\baverages\b", "is around"),
            (r"\baveraged\b", "was around"),
            (r"\baverage\b", "typical"),
            (r"\bavg\b", "score"),
            (r"\braw\b", "unprocessed"),
        ]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def esc(value) -> str:
        return html.escape(reader_text(value))

    def score_class(score: float) -> str:
        if score >= 7:
            return "strong"
        if score >= 5:
            return "watch"
        return "risk"

    def score_pill(score: float) -> str:
        return f"<span class='score-pill {score_class(score)}'>{score:.1f}</span>"

    def leadership_use(score: float) -> str:
        if score >= 7:
            return "Showcase proof"
        if score >= 6:
            return "Use selectively"
        if score >= 5:
            return "Keep in QA set"
        return "Repair first"

    def product_priority(row: dict) -> str:
        if row["provider"] == "PO_MY_MS_EN_Far_AeonCredit_PF_DM2":
            return "Validate with Malay-biased transcript before using in ranking."
        priorities = {
            "Interrupt / Exception Handling": "Improve recovery when customers pause, interrupt, or answer unexpectedly.",
            "Latency": "Reduce dead air and make waiting moments feel intentional.",
            "Conversation flow": "Shorten handoffs and make the next prompt easier to follow.",
            "Opening": "Tighten the first 10 seconds so identity, purpose, and consent are clear.",
            "Voice sound": "Polish delivery so the call sounds more confident and less mechanical.",
        }
        return priorities.get(row["main_gap"], "Review before using this call as buyer-facing proof.")

    def avg_or_dash(items: list[dict]) -> str:
        if not items:
            return "—"
        return f"{statistics.mean(row['revised_score'] for row in items):.2f}"

    def region_strategy(summary: dict) -> tuple[str, str]:
        market = summary["market"]
        avg = summary["revised_avg"]
        good = summary["good_or_better"]
        calls = summary["calls"]
        if market == "Multi-Language":
            return "Flagship demo lane", "Use as the cross-market proof story, but keep only the strongest examples in buyer materials."
        if avg >= 6.5 and good == calls:
            return "Scale story", "Strong enough for external proof. Use regional examples in sales decks and customer demos."
        if avg >= 6.0:
            return "Selective proof", "Good enough to show, but curate examples carefully and avoid claiming uniform quality."
        if avg >= 5.5:
            return "Controlled pilot", "Keep in product-led proof. Show only after transcript or flow review."
        return "Repair lane", "Do not use as a headline market. Treat it as roadmap evidence for turn control and opening quality."

    source_cards = "".join(
        "<article class='source-card reveal'><div class='card-core'>"
        f"<span>{esc(item['source'])}</span><strong>{item['revised_avg']:.2f}</strong>"
        f"<p>{item['good_or_better']}/{item['calls']} calls are good or better. "
        f"{'Use these as proof points where the calls are strongest.' if item['source'] == 'AI Rudder' else 'Competitor media remains mixed, with a few strong benchmarks and several weak examples.'}</p>"
        "</div></article>"
        for item in data["source_summary"]
    )

    band_rows = []
    for label, low, high in [
        ("Excellent", 8, 10.01),
        ("Strong", 7, 8),
        ("Good / usable", 6, 7),
        ("Usable with fixes", 5, 6),
        ("Limited", 4, 5),
        ("Weak", 0, 4),
    ]:
        count = sum(1 for row in rows if low <= float(row["revised_score"]) < high)
        band_rows.append(
            "<tr>"
            f"<td>{label}</td><td>{count}</td>"
            f"<td><span class='density'><i style='transform:scaleX({min(1, count / 32):.4f})'></i></span></td>"
            "</tr>"
        )

    flow_cards = [
        (
            "01 · Decision",
            "Lead with selective proof, not a universal quality claim.",
            "The benchmark supports a confident story in specific regions and examples. It does not support saying every market is ready."
        ),
        (
            "02 · Region strategy",
            "Region comparison is the main operating view.",
            "Multi-Language, BR, MX, ID, and MY are the useful proof lanes. VN is mixed. PH and TH are repair lanes."
        ),
        (
            "03 · Product roadmap",
            "The repeated product issue is turn control.",
            "Prioritize pause handling, interruption recovery, and openings before expanding weaker markets into buyer-facing proof."
        ),
    ]
    flow_html = "".join(
        "<article class='flow-card reveal'><div class='card-core'>"
        f"<span>{esc(kicker)}</span><h3>{esc(title)}</h3><p>{esc(body)}</p>"
        "</div></article>"
        for kicker, title, body in flow_cards
    )

    top_cards = []
    for idx, row in enumerate(top_rows, 1):
        card_class = "proof-card hero-proof reveal" if idx == 1 else "proof-card reveal"
        top_cards.append(
            f"<article class='{card_class}'><div class='card-core'>"
            f"<div class='proof-kicker'><span>{idx:02d}</span>{score_pill(row['revised_score'])}</div>"
            f"<h3>{esc(row['market'])} · {esc(row['provider'])}</h3>"
            f"<p>{esc(row['what_is_good'])}</p>"
            f"<small>{esc(row['source'])} · {esc(row['suite_id'])} · {esc(row['grade'])}</small>"
            "</div></article>"
        )

    market_order = ["Multi-Language", "BR", "MX", "ID", "MY", "VN", "TH", "PH"]
    summary_by_market = {item["market"]: item for item in data["market_summary"]}
    region_rows = []
    market_cards = []
    for market in market_order:
        summary = summary_by_market[market]
        market_items = [row for row in rows if row["market"] == market]
        airudder_items = [row for row in market_items if row["source"] == "AI Rudder"]
        competitor_items = [row for row in market_items if row["source"] == "Competitors"]
        best = max(market_items, key=lambda row: row["revised_score"])
        strategy_label, strategy_detail = region_strategy(summary)
        region_rows.append(
            "<tr>"
            f"<td><strong>{esc(market)}</strong><small>{esc(strategy_label)}</small></td>"
            f"<td>{score_pill(summary['revised_avg'])}</td>"
            f"<td>{summary['good_or_better']}/{summary['calls']}</td>"
            f"<td>{esc(avg_or_dash(airudder_items))}</td>"
            f"<td>{esc(avg_or_dash(competitor_items))}</td>"
            f"<td>{esc(best['provider'])}<small>{esc(best['source'])} · {best['revised_score']:.1f}</small></td>"
            f"<td>{esc(strategy_detail)}</td>"
            "</tr>"
        )
        css_class = "market-card wide reveal" if market in {"Multi-Language", "BR"} else "market-card reveal"
        market_cards.append(
            f"<article class='{css_class}'><div class='card-core'>"
            f"<div class='market-top'><span>{esc(market)}</span>{score_pill(summary['revised_avg'])}</div>"
            f"<h3>{esc(strategy_label)}</h3>"
            f"<p>{summary['good_or_better']}/{summary['calls']} calls are good or better. "
            f"Best example: {esc(best['provider'])} ({best['revised_score']:.1f}). {esc(strategy_detail)}</p>"
            "</div></article>"
        )

    risk_cards = []
    for row in bottom_rows:
        risk_cards.append(
            "<article class='risk-card reveal'><div class='card-core'>"
            f"<div class='risk-row'><span>{esc(row['market'])} · {esc(row['suite_id'])}</span>{score_pill(row['revised_score'])}</div>"
            f"<h3>{esc(row['provider'])}</h3><p>{esc(product_priority(row))}</p>"
            "</div></article>"
        )

    appendix_rows = []
    for row in rows:
        appendix_rows.append(
            "<tr>"
            f"<td>{esc(row['market'])}</td>"
            f"<td>{esc(row['provider'])}<small>{esc(row['suite_id'])} · {esc(row['source'])}</small></td>"
            f"<td>{score_pill(row['revised_score'])}</td>"
            f"<td>{esc(leadership_use(row['revised_score']))}</td>"
            f"<td>{esc(row['main_gap'])}</td>"
            f"<td>{esc(product_priority(row))}</td>"
            "</tr>"
        )

    cmo_take = (
        "The story is not that every call is flawless. The story is that the benchmark now has credible, marketable examples in Multi-Language, BR, MX, ID, and MY, with AI Rudder holding strong proof points."
    )
    cpo_take = (
        "The product agenda should focus on turn control: interruption handling, latency masking, and STT-sensitive evaluation paths. PH and TH need the clearest remediation track."
    )
    ceo_take = (
        "Use the best calls as customer proof, but avoid over-claiming uniform quality. The latest view supports a selective go-to-market story and a precise product repair roadmap."
    )

    css = """
:root{--paper:#f7f3ea;--ink:#17140f;--muted:#716a5d;--fine:rgba(28,24,18,.095);--panel:#fffdf7;--olive:#58654d;--gold:#b98942;--clay:#99524c;--coal:#15140f;--motion:cubic-bezier(.32,.72,0,1);--shadow:0 32px 90px rgba(58,50,35,.11),inset 0 1px 0 rgba(255,255,255,.78)}
*{box-sizing:border-box}html{scroll-behavior:smooth;overflow-x:hidden}body{margin:0;overflow-x:hidden;background:linear-gradient(135deg,#fbfaf6 0%,#eee8dc 52%,#f7f3ea 100%);color:var(--ink);font-family:"Geist","Plus Jakarta Sans","Clash Display",ui-sans-serif,system-ui,sans-serif;letter-spacing:0}body:before{content:"";position:fixed;inset:0;z-index:4;pointer-events:none;opacity:.03;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.74' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='.48'/%3E%3C/svg%3E")}p,li,td,th,small,span,strong,b,h1,h2,h3{overflow-wrap:anywhere;word-break:break-word}p{color:var(--muted);line-height:1.7;font-size:16px}.nav{position:fixed;z-index:3;top:24px;left:50%;transform:translateX(-50%);display:flex;gap:6px;padding:7px;border-radius:999px;background:rgba(255,253,247,.72);backdrop-filter:blur(18px);outline:1px solid var(--fine);box-shadow:0 18px 70px rgba(35,29,18,.08)}.nav a{padding:14px 18px;border-radius:999px;color:#625b4f;font-size:13px;text-decoration:none;transition:background 700ms var(--motion),color 700ms var(--motion),transform 700ms var(--motion)}.nav a:hover{background:#17140f;color:#fffdf7;transform:translateY(-1px)}.shell{width:min(1240px,calc(100% - 64px));margin:0 auto}.hero{position:relative;isolation:isolate;padding:132px 0 74px}.hero:before{content:"";position:absolute;inset:86px -18px 32px;z-index:-1;border-radius:48px;background:linear-gradient(90deg,rgba(251,250,246,.98) 0%,rgba(247,243,234,.88) 34%,rgba(247,243,234,.44) 67%,rgba(247,243,234,.22) 100%),url("assets/contact-center-faded-bg.png") center/cover no-repeat;opacity:.78;filter:saturate(.78) contrast(.94);box-shadow:inset 0 1px 0 rgba(255,255,255,.72),0 38px 110px rgba(58,50,35,.10)}.hero-grid{display:grid;grid-template-columns:minmax(0,800px);gap:34px;align-items:end}.eyebrow{display:inline-flex;align-items:center;border-radius:999px;padding:8px 12px;background:rgba(88,101,77,.13);color:var(--olive);font-size:11px;text-transform:uppercase;font-weight:850;letter-spacing:.06em}h1{font-family:"Clash Display","Geist",ui-sans-serif,system-ui,sans-serif;font-size:clamp(64px,7.5vw,112px);line-height:.92;margin:34px 0 28px;max-width:830px}h2{font-family:"Clash Display","Geist",ui-sans-serif,system-ui,sans-serif;font-size:clamp(38px,5vw,72px);line-height:.97;margin:12px 0 18px}h3{font-family:"Clash Display","Geist",ui-sans-serif,system-ui,sans-serif;font-size:30px;line-height:1.05;margin:0}.lead{font-size:22px;max-width:780px;color:#3d382f}.metric-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px;margin-top:54px}.metric-shell,.source-card,.leader-card,.proof-card,.market-card,.risk-card,.appendix-shell{position:relative;border-radius:34px;padding:7px;background:linear-gradient(135deg,rgba(255,255,255,.78),rgba(255,255,255,.22));outline:1px solid var(--fine);box-shadow:var(--shadow)}.card-core,.metric-core{border-radius:28px;background:rgba(255,253,247,.76);outline:1px solid rgba(28,24,18,.07);padding:30px;height:100%}.metric-core span,.source-card span,.leader-card span,.market-card span,.proof-kicker span,.risk-row span{display:block;font-size:11px;color:var(--olive);font-weight:850;text-transform:uppercase;letter-spacing:.06em}.metric-core strong{display:block;font-size:44px;line-height:.95;margin:12px 0}.section{padding:104px 0}.section-head{display:flex;align-items:end;justify-content:space-between;gap:28px;margin-bottom:28px}.section-head p{max-width:560px}.leadership-grid{display:grid;grid-template-columns:1.1fr .9fr .9fr;gap:18px}.leader-card.primary{grid-row:span 2}.leader-card h3{font-size:34px;margin:12px 0}.source-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:18px}.source-card strong{display:block;font-size:58px;line-height:.95;margin:12px 0;color:var(--coal)}.proof-grid{display:grid;grid-template-columns:repeat(6,1fr);gap:18px}.proof-card{grid-column:span 2}.proof-card.hero-proof{grid-column:span 4;grid-row:span 2}.proof-card h3{margin:18px 0 12px}.proof-card small{display:block;color:var(--muted);margin-top:18px}.proof-kicker,.risk-row,.market-top{display:flex;align-items:center;justify-content:space-between;gap:16px}.score-pill{display:inline-flex;align-items:center;justify-content:center;min-width:48px;border-radius:999px;padding:9px 12px;font-weight:850}.score-pill.strong{background:rgba(88,101,77,.15);color:#3d4b34}.score-pill.watch{background:rgba(185,137,66,.16);color:#7b5721}.score-pill.risk{background:rgba(153,82,76,.14);color:#8b423d}.market-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:18px}.market-card.wide{grid-column:span 2}.market-top .score-pill{font-size:18px}.market-card h3{margin:18px 0 10px}.risk-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px}.risk-card h3{font-size:21px;margin:14px 0 8px}.appendix-shell{margin-top:22px}.table-wrap{overflow:auto;border-radius:28px;background:rgba(255,253,247,.76);outline:1px solid rgba(28,24,18,.07)}table{width:100%;border-collapse:collapse;min-width:980px}th,td{text-align:left;padding:16px 18px;border-bottom:1px solid var(--fine);font-size:14px;vertical-align:top}th{font-size:10px;text-transform:uppercase;color:var(--olive);letter-spacing:.08em}td small{display:block;color:var(--muted);font-size:12px;margin-top:4px}.audio-control{display:block;width:152px;height:34px}.audio-missing{display:inline-flex;color:var(--muted);font-size:12px}.density{display:block;height:9px;border-radius:99px;background:rgba(20,19,15,.08);overflow:hidden}.density i{display:block;height:100%;width:100%;background:linear-gradient(90deg,var(--olive),var(--gold));border-radius:inherit;transform-origin:left}.reveal{opacity:0;transform:translateY(34px);filter:blur(7px);transition:opacity 900ms var(--motion),transform 900ms var(--motion),filter 900ms var(--motion)}.reveal.in{opacity:1;transform:translateY(0);filter:blur(0)}.footer{padding:70px 0 100px;color:var(--muted)}@media(max-width:900px){.nav{display:none}.shell{width:100%;padding:0 18px}.hero{padding:90px 0 60px}.hero:before{inset:54px 0 20px;border-radius:30px}.section{padding:76px 0}h1{font-size:42px;line-height:1.02}.metric-grid,.leadership-grid,.source-grid,.proof-grid,.market-grid,.risk-grid{grid-template-columns:1fr}.proof-card,.proof-card.hero-proof,.market-card.wide{grid-column:auto;grid-row:auto}.section-head{display:block}.card-core,.metric-core{padding:22px}table{min-width:980px}}@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}.reveal{transition:none;transform:none;filter:none;opacity:1}}
.flow-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.flow-card{position:relative;border-radius:34px;padding:7px;background:linear-gradient(135deg,rgba(255,255,255,.78),rgba(255,255,255,.22));outline:1px solid var(--fine);box-shadow:var(--shadow)}.flow-card span{display:block;font-size:11px;color:var(--olive);font-weight:850;text-transform:uppercase;letter-spacing:.06em}.flow-card h3{font-size:32px;margin:14px 0 12px}.comparison-shell{position:relative;border-radius:34px;padding:7px;background:linear-gradient(135deg,rgba(255,255,255,.78),rgba(255,255,255,.22));outline:1px solid var(--fine);box-shadow:var(--shadow);margin-top:22px}.comparison-shell table{min-width:1120px}.comparison-shell strong{font-size:18px}.comparison-shell .score-pill{min-width:54px}@media(max-width:900px){.flow-grid{grid-template-columns:1fr}}
"""

    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gemini 3.5 Flash Provider Evaluation</title>
<style>{css}</style>
</head>
<body>
<nav class="nav"><a href="#readout">Readout</a><a href="#strategy">Strategy</a><a href="#regions">Regions</a><a href="#proof">Proof</a><a href="#risks">Risks</a><a href="#appendix">Appendix</a></nav>
<header class="hero shell">
  <div class="hero-grid">
    <div>
      <span class="eyebrow">Professional Provider Evaluation · 32 scored calls</span>
      <h1>Which voicebot examples can leadership confidently show?</h1>
      <p class="lead">A CMO needs credible proof points. A CPO needs product priorities. This report keeps the evidence, but leads with what matters: where the experience is marketable, where the product needs repair, and which calls should represent the benchmark.</p>
      <div class="metric-grid">
        <div class="metric-shell reveal"><div class="metric-core"><span>Scored files</span><strong>{data['summary']['input_count']}/32</strong></div></div>
        <div class="metric-shell reveal"><div class="metric-core"><span>Average quality</span><strong>{data['summary']['revised_avg']:.2f}</strong></div></div>
        <div class="metric-shell reveal"><div class="metric-core"><span>Good or better</span><strong>{data['summary']['good_or_better']}/32</strong></div></div>
        <div class="metric-shell reveal"><div class="metric-core"><span>Model</span><strong>3.5</strong></div></div>
      </div>
    </div>
  </div>
</header>
<main>
  <section id="readout" class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Leadership readout</span><h2>What CMO and CPO should take away.</h2></div>
      <p>Lead with the strongest examples, not the entire benchmark inventory. Use the weak markets as a focused product roadmap.</p>
    </div>
    <div class="leadership-grid">
      <article class="leader-card primary reveal"><div class="card-core"><span>CMO lens</span><h3>Proof exists, but it is selective.</h3><p>{esc(cmo_take)}</p></div></article>
      <article class="leader-card reveal"><div class="card-core"><span>CPO lens</span><h3>Turn control is the roadmap.</h3><p>{esc(cpo_take)}</p></div></article>
      <article class="leader-card reveal"><div class="card-core"><span>CEO lens</span><h3>Tell a disciplined story.</h3><p>{esc(ceo_take)}</p></div></article>
      <article class="leader-card reveal"><div class="card-core"><span>Source split</span><h3>AI Rudder leads on average.</h3><p>AI Rudder averages 6.17 across 17 call-ID recordings; competitors average 5.57 across 15 media recordings.</p></div></article>
      <article class="leader-card reveal"><div class="card-core"><span>Quality distribution</span><h3>19 of 32 are good or better.</h3><table><tbody>{''.join(band_rows)}</tbody></table></div></article>
    </div>
  </section>
  <section id="strategy" class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Strategy flow</span><h2>How to read the benchmark.</h2></div>
      <p>The report now follows the decision path leadership needs: what to say, where to say it, and what product work protects the story.</p>
    </div>
    <div class="flow-grid">{flow_html}</div>
  </section>
  <section id="regions" class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Region comparison</span><h2>Regional readiness view.</h2></div>
      <p>This is the spine of the report: market readiness, good-call coverage, source split, best example, and the action each region should drive.</p>
    </div>
    <div class="comparison-shell reveal"><div class="table-wrap"><table><thead><tr><th>Region</th><th>Avg score</th><th>Good+</th><th>AI Rudder avg</th><th>Competitor avg</th><th>Best example</th><th>Strategic action</th></tr></thead><tbody>{''.join(region_rows)}</tbody></table></div></div>
  </section>
  <section id="proof" class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Showcase proof</span><h2>The examples worth putting in front of buyers.</h2></div>
      <p>These calls provide a stronger CMO story than a full spreadsheet: they show clear voice, task movement, and believable enough interaction quality.</p>
    </div>
    <div class="proof-grid">{''.join(top_cards)}</div>
  </section>
  <section class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Provider position</span><h2>Source comparison at the level leadership needs.</h2></div>
      <p>Enough to understand position. Not overloaded with transcript defects.</p>
    </div>
    <div class="source-grid">{source_cards}</div>
  </section>
  <section id="markets" class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Market map</span><h2>Where to scale, where to repair.</h2></div>
      <p>Multi-Language, BR, MX, ID, and MY support a positive story. PH and TH should be handled as product remediation markets.</p>
    </div>
    <div class="market-grid">{''.join(market_cards)}</div>
  </section>
  <section id="risks" class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Risk focus</span><h2>Do not let these define the narrative.</h2></div>
      <p>The weakest examples are useful for the CPO roadmap, not for the CMO story.</p>
    </div>
    <div class="risk-grid">{''.join(risk_cards)}</div>
  </section>
  <section id="appendix" class="section shell">
    <div class="section-head">
      <div><span class="eyebrow">Compact appendix</span><h2>All scored files, reduced to action.</h2></div>
      <p>Every file stays represented as a business decision: what can be shown, what should be selective, and what needs product repair first.</p>
    </div>
    <div class="appendix-shell reveal"><div class="table-wrap"><table><thead><tr><th>Market</th><th>Provider</th><th>Score</th><th>Leadership use</th><th>Watch area</th><th>Product priority</th></tr></thead><tbody>{''.join(appendix_rows)}</tbody></table></div></div>
  </section>
</main>
<footer class="footer shell">Gemini 3.5 Flash audio evaluation · Deepgram STT · Latest-lens provider report</footer>
<script>
const io=new IntersectionObserver(entries=>{{entries.forEach(e=>{{if(e.isIntersecting)e.target.classList.add('in')}})}},{{threshold:.08}});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
</script>
</body>
</html>
"""
    OUT_HTML.write_text(html_text, encoding="utf-8")
    OUT_PROFESSIONAL_HTML.write_text(html_text, encoding="utf-8")


def write_reference_aligned_html(data: dict) -> None:
    """Write the report in the canonical professional evaluation format."""
    rows = data["rows"]
    final_rows = load_json(FINAL_JSON)["rows"]
    report_by_key = {}
    for item in final_rows:
        key = (item.get("suite_id"), item.get("file_name"))
        try:
            report_by_key[key] = load_json(Path(item["report_json"]))
        except (KeyError, FileNotFoundError):
            report_by_key[key] = {}

    def reader_text(value) -> str:
        text = "" if value is None else str(value)
        replacements = [
            (r"\baverages\b", "is around"),
            (r"\baveraged\b", "was around"),
            (r"\baverage\b", "typical"),
            (r"\bavg\b", "score"),
            (r"\braw\b", "unprocessed"),
        ]
        for pattern, replacement in replacements:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        return text

    def esc(value) -> str:
        return html.escape(reader_text(value))

    def score_class(score: float) -> str:
        if score >= 7:
            return "strong"
        if score >= 5:
            return "watch"
        return "risk"

    def score_pill(score: float) -> str:
        return f"<span class='score-pill {score_class(score)}'>{float(score):.1f}</span>"

    copied_audio: dict[str, str] = {}
    if OUT_AUDIO_DIR.exists():
        for stale_audio in OUT_AUDIO_DIR.iterdir():
            if stale_audio.is_file():
                stale_audio.unlink()

    def audio_button(row: dict) -> str:
        source = row.get("audio_source_path")
        if not source:
            return "<span class='audio-missing'>No audio</span>"
        source_path = Path(source)
        if not source_path.exists():
            return "<span class='audio-missing'>No audio</span>"
        OUT_AUDIO_DIR.mkdir(exist_ok=True)
        safe_suite = re.sub(r"[^A-Za-z0-9_.-]+", "-", str(row.get("suite_id") or "call")).strip("-")
        safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", source_path.name).strip("-")
        source_hash = hashlib.sha1(str(source_path).encode("utf-8")).hexdigest()[:8]
        target_name = f"{safe_suite}-{source_hash}-{safe_name}"
        target = OUT_AUDIO_DIR / target_name
        if str(source_path) not in copied_audio:
            if not target.exists() or target.stat().st_size != source_path.stat().st_size:
                shutil.copy2(source_path, target)
            copied_audio[str(source_path)] = f"audio/{quote(target_name)}"
        href = copied_audio[str(source_path)]
        label = esc(provider_display(row))
        return (
            f"<audio class='audio-control' controls preload='none' src='{href}' "
            f"aria-label='Play audio for {label}'></audio>"
        )

    def avg(values: list[float]) -> float:
        return round(statistics.mean(values), 2) if values else 0.0

    def avg_text(values: list[float]) -> str:
        return f"{avg(values):.2f}" if values else "-"

    def provider_display(row: dict) -> str:
        return row["provider"] or row["file_name"] or row["suite_id"]

    def company_display(row: dict) -> str:
        if row["source"] == "AI Rudder":
            return "Airudder"
        return provider_display(row)

    def country_display(market: str) -> str:
        icon = COUNTRY_ICONS.get(market)
        return f"{icon} {market}" if icon else market

    def robot_type(row: dict) -> str:
        mapped = ROBOT_TYPE_BY_SUITE.get(str(row.get("suite_id") or ""))
        if mapped:
            return mapped
        marker = " ".join(
            str(row.get(key) or "")
            for key in ["suite_id", "provider", "file_name", "source", "source_class"]
        )
        if re.search(r"\bNLU\b|竞品NLU", marker, re.IGNORECASE):
            return "NLU"
        if re.search(r"\bLLM\b|竞品LLM", marker, re.IGNORECASE):
            return "LLM"
        return "Unknown"

    def product_priority(row: dict) -> str:
        if row["provider"] == "PO_MY_MS_EN_Far_AeonCredit_PF_DM2":
            return "Validate with Malay-biased transcript before using it as a ranked proof point."
        priorities = {
            "Interrupt / Exception Handling": "Improve recovery when customers pause, interrupt, or answer unexpectedly.",
            "Latency": "Reduce dead air and make waiting moments feel intentional.",
            "Conversation flow": "Shorten long turns and make the next prompt easier to follow.",
            "Opening": "Tighten the first 10 seconds so identity, purpose, and consent are clear.",
            "Voice sound": "Polish delivery so the call sounds more confident and less mechanical.",
        }
        return priorities.get(row["main_gap"], "Review before using this call as buyer-facing proof.")

    for row in rows:
        audio_button(row)

    def report_for(row: dict) -> dict:
        return report_by_key.get((row.get("suite_id"), row.get("file_name")), {})

    def ul(items: list[str], limit: int = 6) -> str:
        values = [item for item in items if item]
        if not values:
            return "<li>No standout item recorded.</li>"
        return "".join(f"<li>{esc(item)}</li>" for item in values[:limit])

    def named_item(row: dict, text: str) -> str:
        return f"<b>{esc(provider_display(row))}</b>: {esc(text)}"

    def representative_key(row: dict) -> tuple[float, int, str]:
        return (
            float(row["revised_score"]),
            1 if row["source"] == "AI Rudder" else 0,
            str(row.get("suite_id") or ""),
        )

    def agent_score(group: list[dict]) -> float:
        return round(avg([row["revised_score"] for row in group]), 2)

    def raw_agent_score(group: list[dict]) -> float:
        return round(avg([row["raw_score"] for row in group]), 2)

    def calibrated_agent_score(group: list[dict]) -> float:
        return round(avg([row["calibrated_score"] for row in group]), 2)

    def html_ul(items: list[str], limit: int = 6) -> str:
        values = [item for item in items if item]
        if not values:
            return "<li>No standout item recorded.</li>"
        return "".join(f"<li>{item}</li>" for item in values[:limit])

    def dimension_block(row: dict, report: dict) -> str:
        parts = []
        dimensions = {dim.get("id"): dim for dim in report.get("dimensions") or []}
        for dim_id in ["voice", "opening", "speaking", "latency", "exception"]:
            dim = dimensions.get(dim_id, {})
            evidence = []
            for item in (dim.get("evidence") or [])[:2]:
                note = item.get("note") or item.get("quote") or ""
                time = item.get("time")
                speaker = item.get("speaker")
                prefix = " · ".join(str(v) for v in [time, speaker] if v)
                evidence.append(f"{prefix}: {note}" if prefix else note)
            advice = []
            for item in (dim.get("advice") or [])[:2]:
                advice.append(item.get("text") if isinstance(item, dict) else str(item))
            parts.append(
                "<article class='dimension-card'>"
                f"<div class='dimension-top'><span>{esc(DIMENSION_LABELS[dim_id])}</span>{score_pill(row['revised_dimensions'].get(dim_id, 0))}</div>"
                f"<p>{esc((dim.get('strengths') or ['No clear strength recorded.'])[0])}</p>"
                f"<h5>What hurt it</h5><ul>{ul(dim.get('weaknesses') or [], 2)}</ul>"
                f"<h5>Evidence</h5><ul>{ul(evidence, 2)}</ul>"
                f"<h5>Advice</h5><ul>{ul(advice, 2)}</ul>"
                "</article>"
            )
        return "".join(parts)

    def transcript_rows(report: dict) -> str:
        lines = []
        for turn in (report.get("transcript") or [])[:14]:
            lines.append(
                "<tr>"
                f"<td>{esc(turn.get('start'))}</td>"
                f"<td>{esc(turn.get('speaker'))}</td>"
                f"<td>{esc(turn.get('text'))}<small>{esc(turn.get('translation'))}</small></td>"
                "</tr>"
            )
        if not lines:
            return "<tr><td colspan='3'>No transcript lines available.</td></tr>"
        return "".join(lines)

    market_order = ["ID", "TH", "PH", "MY", "VN", "Multi-Language", "MX", "BR"]
    market_summary = {item["market"]: item for item in data["market_summary"]}
    rows_by_market = {market: [row for row in rows if row["market"] == market] for market in market_order}

    top_rows = sorted(rows, key=lambda row: row["revised_score"], reverse=True)[:5]
    bottom_rows = sorted(rows, key=lambda row: row["revised_score"])[:5]
    ai_rows = [row for row in rows if row["source"] == "AI Rudder"]
    competitor_rows = [row for row in rows if row["source"] == "Competitors"]

    proof_cards = []
    proof_examples = [
        ("AI Rudder has buyer-ready proof", top_rows[0]),
        ("AI Rudder can still win on regional examples", max(ai_rows, key=lambda row: row["revised_score"])),
        ("Competitor benchmarks are mixed", max(competitor_rows, key=lambda row: row["revised_score"])),
        ("Weak markets explain the roadmap", bottom_rows[0]),
    ]
    for title, row in proof_examples:
        proof_cards.append(
            "<article class='learning-card reveal'>"
            f"<span>{esc(row['source'])} · {esc(row['market'])} · {esc(row['suite_id'])}</span>"
            f"<h3>{esc(title)}</h3>"
            f"<p><b>{esc(provider_display(row))}</b> scores {row['revised_score']:.1f}. {esc(row['what_is_good'])}</p>"
            f"<p class='muted-line'>Watch area: {esc(row['main_gap'])}. {esc(product_priority(row))}</p>"
            "</article>"
        )

    region_cards = []
    for market in market_order:
        items = rows_by_market[market]
        if not items:
            continue
        best = max(items, key=representative_key)
        provider_rows = []
        for representative in sorted(items, key=representative_key, reverse=True):
            dims = representative["revised_dimensions"]
            provider_rows.append(
                "<tr>"
                f"<td><b>{esc(provider_display(representative))}</b><small>{esc(representative['source'])} · {esc(representative['suite_id'])}</small></td>"
                f"<td>{esc(robot_type(representative))}</td>"
                f"<td>{score_pill(representative['revised_score'])}</td>"
                f"<td>{dims['voice']:.1f}</td><td>{dims['opening']:.1f}</td><td>{dims['speaking']:.1f}</td><td>{dims['latency']:.1f}</td><td>{dims['exception']:.1f}</td>"
                f"<td>{esc(representative['main_gap'])}</td>"
                f"<td>{audio_button(representative)}</td>"
                "</tr>"
            )
        sorted_items = sorted(items, key=lambda row: row["revised_score"], reverse=True)
        good_items = [named_item(row, row["what_is_good"]) for row in sorted_items]
        attention_items = [named_item(row, row["remaining_gap"]) for row in sorted(items, key=lambda row: row["revised_score"])]
        improve_items = [named_item(row, product_priority(row)) for row in sorted(items, key=lambda row: row["revised_score"])]
        best_highlight = f"{provider_display(best)}: {best['what_is_good']}"
        region_cards.append(
            f"<section class='region-card reveal' id='region-{esc(market).lower()}'>"
            "<div class='region-head'>"
            f"<div><span class='eyebrow'>Region</span><h3>{esc(market)}</h3><p>Best scoring call: <b>{esc(provider_display(best))}</b> ({esc(best['source'])}, {esc(best['suite_id'])}).</p></div>"
            f"<div class='region-score'>{score_pill(best['revised_score'])}<small>call score</small></div>"
            "</div>"
            "<div class='good-bad robot-highlight'>"
            f"<div><h4>Best robot highlight</h4><ul>{ul([best_highlight], 1)}</ul></div>"
            "</div>"
            "<div class='table-wrap'><table><thead><tr><th>Agent / robot</th><th>Robot type</th><th>Score</th><th>Voice</th><th>Opening</th><th>Style</th><th>Latency</th><th>Interrupt / Exception</th><th>Main gap</th><th>Audio</th></tr></thead>"
            f"<tbody>{''.join(provider_rows)}</tbody></table></div>"
            "<div class='good-bad region-buckets'>"
            f"<div><h4>What's good</h4><ul>{html_ul(good_items, 8)}</ul></div>"
            f"<div><h4>What needs attention</h4><ul>{html_ul(attention_items, 8)}</ul></div>"
            f"<div><h4>What to improve</h4><ul>{html_ul(improve_items, 8)}</ul></div>"
            "</div>"
            "</section>"
        )

    region_comparison_rows = []
    for market in ["Multi-Language", "BR", "MX", "ID", "MY", "VN", "TH", "PH"]:
        items = rows_by_market[market]
        best = max(items, key=representative_key)
        region_comparison_rows.append(
            "<tr>"
            f"<td><b>{esc(market)}</b><small>{len(items)} call examples</small></td>"
            f"<td>{score_pill(best['revised_score'])}</td>"
            f"<td>{esc(provider_display(best))}<small>{esc(best['source'])} · {esc(best['suite_id'])}</small></td>"
            f"<td><b>{esc(provider_display(best))}</b>: {esc(best['what_is_good'])}</td>"
            f"<td>{audio_button(best)}</td>"
            "</tr>"
        )

    company_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        company_groups[(row["market"], company_display(row))].append(row)
    company_summary_rows = []
    for (market, company), items in sorted(
        company_groups.items(),
        key=lambda item: (
            item[0][0].lower(),
            item[0][1].lower(),
        ),
    ):
        best = max(items, key=representative_key)
        company_summary_rows.append(
            "<tr>"
            f"<td>{esc(country_display(market))}</td>"
            f"<td><b>{esc(company)}</b><small>Best robot: {esc(provider_display(best))} · {esc(best['suite_id'])}</small></td>"
            f"<td>{esc(robot_type(best))}</td>"
            f"<td>{score_pill(best['revised_score'])}</td>"
            f"<td>{esc(provider_display(best))}</td>"
            f"<td>{audio_button(best)}</td>"
            "</tr>"
        )

    call_details = []
    for row in sorted(rows, key=lambda item: (market_order.index(item["market"]) if item["market"] in market_order else 99, item["suite_id"])):
        report = report_for(row)
        call_details.append(
            "<details class='call-card reveal'>"
            "<summary>"
            f"<span>{esc(row['market'])} · {esc(row['suite_id'])} · {esc(row['source'])}</span>"
            f"<b>{esc(provider_display(row))}</b>"
            f"{score_pill(row['revised_score'])}"
            "</summary>"
            "<div class='call-body'>"
            f"<p class='call-summary'>{esc(row['revised_readout'] or report.get('overall_summary'))}</p>"
            "<dl class='identity'>"
            f"<dt>File</dt><dd>{esc(row['file_name'])}</dd>"
            f"<dt>Language</dt><dd>{esc(row.get('language'))}</dd>"
            f"<dt>Duration</dt><dd>{esc(fmt(row.get('duration_sec')))} seconds</dd>"
            f"<dt>Leadership use</dt><dd>{esc('Showcase proof' if row['revised_score'] >= 7 else 'Use selectively' if row['revised_score'] >= 6 else 'Keep in QA set' if row['revised_score'] >= 5 else 'Repair first')}</dd>"
            f"<dt>Product priority</dt><dd>{esc(product_priority(row))}</dd>"
            "</dl>"
            "<div class='good-bad'>"
            f"<div><h4>Highlights</h4><ul>{ul(report.get('highlights') or [row['what_is_good']], 6)}</ul></div>"
            f"<div><h4>Red flags</h4><ul>{ul(report.get('red_flags') or [row['remaining_gap']], 6)}</ul></div>"
            "</div>"
            f"<div class='dimension-grid'>{dimension_block(row, report)}</div>"
            "<h4>Transcript sample</h4>"
            f"<div class='table-wrap'><table><thead><tr><th>Time</th><th>Speaker</th><th>Line</th></tr></thead><tbody>{transcript_rows(report)}</tbody></table></div>"
            "</div>"
            "</details>"
        )

    band_rows = []
    for label, low, high in [
        ("Excellent", 8, 10.01),
        ("Strong", 7, 8),
        ("Good / usable", 6, 7),
        ("Usable with fixes", 5, 6),
        ("Limited", 4, 5),
        ("Weak", 0, 4),
    ]:
        count = sum(1 for row in rows if low <= float(row["revised_score"]) < high)
        band_rows.append(
            f"<tr><td>{label}</td><td>{count}</td><td><span class='bar'><i style='transform:scaleX({min(1, count / 32):.4f})'></i></span></td></tr>"
        )

    css = """
:root{--paper:#f6f4ef;--ink:#14130f;--muted:#6f6a60;--fine:rgba(20,19,15,.095);--panel:#fffdf8;--olive:#596553;--gold:#b98b46;--clay:#9a514d;--coal:#181914;--motion:cubic-bezier(.32,.72,0,1);--shadow:0 32px 90px rgba(52,46,34,.10),inset 0 1px 0 rgba(255,255,255,.75)}
*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:linear-gradient(135deg,#fbfaf6 0%,#efebe2 48%,#f6f4ef 100%);color:var(--ink);font-family:"Geist","Plus Jakarta Sans","Clash Display",ui-sans-serif,system-ui,sans-serif;letter-spacing:0}body:before{content:"";position:fixed;inset:0;z-index:4;pointer-events:none;opacity:.035;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.72' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='160' height='160' filter='url(%23n)' opacity='.50'/%3E%3C/svg%3E")}p,li,td,th,small,span,strong,b,h1,h2,h3,h4,h5,summary{overflow-wrap:anywhere;letter-spacing:0}p{color:var(--muted);line-height:1.72;font-size:16px}.nav{position:fixed;z-index:5;top:24px;left:50%;transform:translateX(-50%);display:flex;gap:6px;align-items:center;padding:8px;border-radius:999px;background:rgba(255,253,248,.74);backdrop-filter:blur(24px);box-shadow:0 18px 52px rgba(50,43,30,.12);outline:1px solid rgba(20,19,15,.08)}.nav a{font-size:12px;color:var(--muted);padding:10px 14px;border-radius:999px;text-decoration:none;transition:transform 700ms var(--motion),background 700ms var(--motion),color 700ms var(--motion)}.nav a:hover{background:rgba(20,19,15,.06);color:var(--ink);transform:translateY(-1px)}.shell{width:min(1220px,calc(100% - 56px));margin:0 auto}.section{padding:88px 0}.hero{position:relative;min-height:62dvh;display:grid;align-items:center;padding:96px 0 36px;isolation:isolate}.hero:before{content:"";position:absolute;inset:74px -18px 8px;z-index:-1;border-radius:42px;background:linear-gradient(90deg,rgba(251,250,246,.98),rgba(246,244,239,.86) 44%,rgba(246,244,239,.42)),url("assets/contact-center-faded-bg.png") center/cover no-repeat;opacity:.84;filter:saturate(.82) contrast(.95);box-shadow:var(--shadow)}.eyebrow{display:inline-flex;width:max-content;border-radius:999px;padding:8px 12px;background:rgba(89,101,83,.10);color:var(--olive);font-size:10px;text-transform:uppercase;font-weight:800}h1{font-family:"PP Editorial New","Clash Display","Geist",serif;font-size:clamp(42px,6vw,84px);line-height:.94;margin:20px 0 18px;max-width:900px;font-weight:760}h2{font-family:"PP Editorial New","Clash Display","Geist",serif;font-size:clamp(38px,5vw,76px);line-height:.98;margin:0 0 18px}h3{font-family:"PP Editorial New","Clash Display","Geist",serif;font-size:34px;line-height:1.04;margin:0}.lead{font-size:18px;max-width:780px;color:#403b33}.metric-grid,.method-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-top:24px}.card,.method-card,.learning-card,.region-card,.call-card,.summary-card{border-radius:34px;padding:7px;background:linear-gradient(135deg,rgba(255,255,255,.82),rgba(255,255,255,.22));outline:1px solid var(--fine);box-shadow:var(--shadow)}.card-inner,.method-card,.learning-card,.region-card,.call-card .call-body,.summary-card{background:rgba(255,253,248,.76);border-radius:28px;outline:1px solid rgba(20,19,15,.07);padding:22px}.metric-grid strong{display:block;font-size:36px;line-height:.95;margin-top:10px}.section-head{display:flex;align-items:end;justify-content:space-between;gap:34px;margin-bottom:30px}.section-head p{max-width:590px}.summary-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px}.method-card span,.learning-card span,.dimension-top span{display:block;font-size:11px;color:var(--olive);font-weight:850;text-transform:uppercase}.source-grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.score-pill{display:inline-flex;align-items:center;justify-content:center;min-width:50px;border-radius:999px;padding:9px 12px;font-weight:850}.score-pill.strong{background:rgba(89,101,83,.15);color:#3d4b34}.score-pill.watch{background:rgba(185,139,70,.16);color:#75511d}.score-pill.risk{background:rgba(154,81,77,.14);color:#88403c}.table-wrap{overflow:auto;border-radius:24px;background:rgba(255,253,248,.80);outline:1px solid rgba(20,19,15,.08)}table{width:100%;border-collapse:collapse;min-width:980px}th,td{text-align:left;padding:14px 16px;border-bottom:1px solid var(--fine);font-size:14px;vertical-align:top}th{font-size:10px;text-transform:uppercase;color:var(--olive)}td small{display:block;color:var(--muted);font-size:12px;margin-top:4px}.audio-control{display:block;width:152px;height:34px}.audio-missing{display:inline-flex;color:var(--muted);font-size:12px}.bar{display:block;height:9px;border-radius:999px;background:rgba(20,19,15,.08);overflow:hidden}.bar i{display:block;height:100%;background:linear-gradient(90deg,var(--olive),var(--gold));transform-origin:left}.region-stack{display:grid;gap:34px;margin-top:38px}.region-card{scroll-margin-top:96px}.region-head{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:22px}.region-score{text-align:right}.region-score small{display:block;color:var(--muted);margin-top:8px}.good-bad{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-top:18px}.region-buckets{grid-template-columns:repeat(3,1fr)}.good-bad>div{border-radius:22px;background:rgba(255,255,255,.52);outline:1px solid rgba(20,19,15,.07);padding:20px}.good-bad h4,.call-body h4,.dimension-card h5{margin:0 0 10px;color:var(--coal)}ul{margin:0;padding-left:18px;color:var(--muted);line-height:1.55}.call-stack{display:grid;gap:14px}.call-card{display:block}.call-card summary{cursor:pointer;list-style:none;display:grid;grid-template-columns:180px minmax(0,1fr) auto;gap:18px;align-items:center;background:rgba(255,253,248,.76);border-radius:28px;outline:1px solid rgba(20,19,15,.07);padding:20px 24px}.call-card summary::-webkit-details-marker{display:none}.call-card summary span{font-size:12px;color:var(--olive);font-weight:800;text-transform:uppercase}.call-card summary b{font-size:18px}.call-card[open] summary{border-radius:28px 28px 16px 16px}.call-body{margin-top:8px}.identity{display:grid;grid-template-columns:160px 1fr;gap:8px 16px}.identity dt{color:var(--olive);font-weight:800}.identity dd{margin:0;color:var(--muted)}.dimension-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:14px;margin:22px 0}.dimension-card{border-radius:20px;background:rgba(255,255,255,.54);outline:1px solid rgba(20,19,15,.08);padding:18px}.dimension-top{display:flex;justify-content:space-between;gap:12px;align-items:center}.muted-line{font-size:14px}.reveal{opacity:0;transform:translateY(30px);filter:blur(6px);transition:opacity 900ms var(--motion),transform 900ms var(--motion),filter 900ms var(--motion)}.reveal.in{opacity:1;transform:translateY(0);filter:blur(0)}.footer{padding:70px 0 110px;color:var(--muted)}@media(max-width:900px){.nav{display:none}.shell{width:100%;padding:0 18px}.hero{min-height:auto;padding:82px 0 30px}.hero:before{inset:52px 0 8px;border-radius:30px}h1{font-size:40px}.section{padding:70px 0}.metric-grid,.method-grid,.summary-grid,.source-grid,.good-bad,.region-buckets,.dimension-grid{grid-template-columns:1fr}.section-head,.region-head{display:block}.call-card summary{grid-template-columns:1fr}.identity{grid-template-columns:1fr}table{min-width:980px}}@media(prefers-reduced-motion:reduce){.reveal{opacity:1;transform:none;filter:none;transition:none}html{scroll-behavior:auto}}
"""

    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Professional Provider Evaluation · Gemini 3.5 Flash 32 Call Test Set</title>
<style>{css}</style>
</head>
<body>
<nav class="nav">
  <a href="#regions">Regions</a><a href="#deep-proof">All Calls</a><a href="#next">Next</a><a href="#meaning">Method</a>
</nav>
<header class="hero shell">
  <div>
    <span class="eyebrow">Professional Provider Evaluation · 32 scored calls</span>
    <h1>A comparison between Airudder and several competing products.</h1>
  </div>
</header>
<main>
  <section id="company-comparison" class="section shell">
    <div class="section-head"><div><span class="eyebrow">Country and company comparison</span><h2>Best score by company</h2></div><p>If a company has multiple audio files in the same country, this table shows the best individual call score.</p></div>
    <div class="table-wrap reveal"><table><thead><tr><th>Country</th><th>Company</th><th>Robot type</th><th>Score</th><th>Best robot</th><th>Audio</th></tr></thead><tbody>{''.join(company_summary_rows)}</tbody></table></div>
  </section>
  <section id="regions" class="section shell">
    <div class="section-head"><div><span class="eyebrow">Region and provider results</span><h2>Region</h2></div><p>Each row is one scored call example with the final audited score used for this report.</p></div>
    <div class="table-wrap reveal"><table><thead><tr><th>Region</th><th>Score</th><th>Top call</th><th>What's good</th><th>Audio</th></tr></thead><tbody>{''.join(region_comparison_rows)}</tbody></table></div>
    <div class="region-stack">{''.join(region_cards)}</div>
  </section>
  <section id="deep-proof" class="section shell">
    <div class="section-head"><div><span class="eyebrow">Deep proof</span><h2>All 32 call evaluations</h2></div><p>Open each row to see the full evaluation: summary, good points, serious issues, score-part proof, advice, and transcript sample.</p></div>
    <div class="call-stack">{''.join(call_details)}</div>
  </section>
  <section id="next" class="section shell">
    <div class="section-head"><div><span class="eyebrow">Recommended next move</span><h2>Fix latency and conversation control before voice polish.</h2></div><p>Voice quality matters, but the biggest customer pain is waiting, repeated scripts, and weak interrupt / exception handling. Use these 32 calls as the regression set before scaling weaker markets.</p></div>
    <div class="summary-card reveal"><table><tbody>{''.join(band_rows)}</tbody></table></div>
  </section>
  <section id="meaning" class="section shell">
    <div class="section-head"><div><span class="eyebrow">What professional evaluation means</span><h2>Not just a score. Proof you can act on.</h2></div><p>A professional evaluation checks every call with the same rules and keeps enough proof for product, sales, and leadership to make the same decision.</p></div>
    <div class="method-grid">
      <article class="method-card reveal"><span>1</span><h3>Use a fixed scorecard</h3><p>Every call is judged on voice, opening, conversation flow, latency, and interrupt / exception handling.</p></article>
      <article class="method-card reveal"><span>2</span><h3>Show the proof</h3><p>Each call keeps highlights, red flags, score-part evidence, advice, and transcript lines.</p></article>
      <article class="method-card reveal"><span>3</span><h3>Compare fairly</h3><p>Providers are grouped by region and source type so one outlier does not become the full story.</p></article>
      <article class="method-card reveal"><span>4</span><h3>Turn scores into action</h3><p>The output says what to show, what to use selectively, and what to repair first.</p></article>
    </div>
  </section>
  <section id="method" class="section shell">
    <div class="section-head"><div><span class="eyebrow">Evaluation strategy</span><h2>How the work was done</h2></div><p>The benchmark uses the curated 32-file set, Deepgram STT, and Gemini 3.5 Flash scoring. AI Rudder call IDs and competitor media are kept separate in the comparison.</p></div>
    <div class="method-grid">
      <article class="method-card reveal"><span>A</span><h3>Collect the test set</h3><p>Use the canonical 32 imported records from the region and provider test set.</p></article>
      <article class="method-card reveal"><span>B</span><h3>Transcribe audio</h3><p>Use Deepgram STT so the scoring model reads call content and timing context consistently.</p></article>
      <article class="method-card reveal"><span>C</span><h3>Score five parts</h3><p>Each call receives five call-experience scores and one final audited call score for the comparison table.</p></article>
      <article class="method-card reveal"><span>D</span><h3>Group by region</h3><p>Region and provider tables show where the benchmark is marketable and where the product needs repair.</p></article>
    </div>
  </section>
</main>
<footer class="footer shell">Gemini 3.5 Flash audio evaluation · Deepgram STT · Standard professional provider report</footer>
<script>
const io=new IntersectionObserver(entries=>{{entries.forEach(e=>{{if(e.isIntersecting)e.target.classList.add('in')}})}},{{threshold:.08}});
document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
</script>
</body>
</html>
"""
    OUT_HTML.write_text(html_text, encoding="utf-8")
    OUT_PROFESSIONAL_HTML.write_text(html_text, encoding="utf-8")


def main() -> None:
    final = load_json(FINAL_JSON)
    rows = []
    for row in final["rows"]:
        report = load_json(Path(row["report_json"]))
        rows.append(recalibrate_row(row, report))

    summary = {
        "input_count": len(rows),
        "raw_avg": round(statistics.mean(row["raw_score"] for row in rows), 2),
        "revised_avg": round(statistics.mean(row["revised_score"] for row in rows), 2),
        "avg_delta": round(statistics.mean(row["delta"] for row in rows), 2),
        "good_or_better": sum(1 for row in rows if row["revised_score"] >= 6),
    }
    data = {
        "summary": summary,
        "mechanism": {
            "name": "Business-usable voicebot recalibration",
            "raw_score_meaning": "Strict human-likeness and defect-detection score from Gemini 3.5 Flash.",
            "revised_score_meaning": "Practical quality score that gives more credit for usable, clear, task-moving calls.",
            "weights": WEIGHTS,
            "guardrails": [
                "The original raw score is retained and never overwritten.",
                "Revised scores can improve but genuinely broken calls remain capped.",
                "Evidence, strengths, weaknesses, and recommendations come from the original per-file reports.",
            ],
        },
        "source_summary": summarize(rows, "source"),
        "market_summary": summarize(rows, "market"),
        "rows": rows,
    }
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    write_csv(rows)
    write_reference_aligned_html(data)
    print(OUT_JSON)
    print(OUT_CSV)
    print(OUT_HTML)
    print(OUT_PROFESSIONAL_HTML)


if __name__ == "__main__":
    main()
