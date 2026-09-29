from collections import Counter
from html import escape

from .analysis import contradictions_from_graph, derive_questions
from .constants import NOTICE


def report_data(graph):
    return {
        "synthetic": True,
        "notice": NOTICE,
        "extraction_method": graph.get("extraction_method", "rule_based_structured_json"),
        "entity_counts": dict(sorted(Counter(node["type"] for node in graph["nodes"]).items())),
        "edge_counts": dict(sorted(Counter(edge["type"] for edge in graph["edges"]).items())),
        "contradictions": contradictions_from_graph(graph),
        "questions": derive_questions(graph)["questions"],
    }


def _markdown_list(items, empty):
    if not items:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in items)


def render_markdown(graph):
    data = report_data(graph)
    lines = [
        "# PaperGraph report",
        "",
        f"**SYNTHETIC fixture data notice:** {NOTICE}",
        "",
        "Extraction method: rule-based parsing of structured synthetic JSON fixtures.",
        "",
        "## Entity counts",
        "",
    ]
    lines.extend(f"- {kind}: {count}" for kind, count in data["entity_counts"].items())
    lines.extend(["", "## Edge counts", ""])
    lines.extend(f"- {kind}: {count}" for kind, count in data["edge_counts"].items())
    lines.extend(["", "## Contradictions", ""])
    contradiction_lines = [
        f"Claims `{', '.join(item['claim_ids'])}` on dataset `{item['dataset_id']}` have opposing directions "
        f"({item['directions'][0]} and {item['directions'][1]}). Evidence: " + "; ".join(
            f"{e['claim_id']} in {e['paper_id']}: {e['metric']} {e['baseline']} to {e['observed']} ({e['direction']})"
            for e in item["evidence"]
        ) + "."
        for item in data["contradictions"]
    ]
    lines.append(_markdown_list(contradiction_lines, "No opposing result pairs found."))
    lines.extend(["", "## Open questions", ""])
    question_lines = [f"{item['question']} Gap evidence: {item['gap']}." for item in data["questions"]]
    lines.append(_markdown_list(question_lines, "No configured gaps found."))
    return "\n".join(lines) + "\n"


def render_html(graph):
    data = report_data(graph)
    entity_rows = "".join(f"<tr><th>{escape(kind)}</th><td>{count}</td></tr>" for kind, count in data["entity_counts"].items())
    edge_rows = "".join(f"<tr><th>{escape(kind)}</th><td>{count}</td></tr>" for kind, count in data["edge_counts"].items())
    contradictions = []
    for item in data["contradictions"]:
        evidence = "<ul>" + "".join(
            f"<li><code>{escape(record['claim_id'])}</code> in <code>{escape(record['paper_id'])}</code>: "
            f"{escape(record['metric'])} {escape(str(record['baseline']))} to {escape(str(record['observed']))} "
            f"({escape(record['direction'])}) on <code>{escape(record['dataset_id'])}</code></li>"
            for record in item["evidence"]
        ) + "</ul>"
        contradictions.append(f"<li>Claims {escape(', '.join(item['claim_ids']))} have opposing directions. {evidence}</li>")
    question_html = "".join(
        f"<li>{escape(item['question'])} <strong>Gap evidence:</strong> <code>{escape(str(item['gap']))}</code></li>"
        for item in data["questions"]
    )
    return """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>PaperGraph report</title><style>
body{font:16px/1.5 system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;color:#18202a}
.banner{padding:1rem;border:2px solid #9a3412;background:#fff7ed;color:#7c2d12;font-weight:700}
table{border-collapse:collapse;margin:1rem 0}th,td{padding:.4rem .8rem;border:1px solid #bbc4ce;text-align:left}
code{overflow-wrap:anywhere}section{margin:2rem 0}
</style></head><body>
<header class="banner" role="alert">Synthetic fixture papers only. Extraction is rule-based parsing of structured JSON, not NLP over real PDFs.</header>
<main><h1>PaperGraph report</h1><p>""" + escape(NOTICE) + "</p><p>Extraction method: rule-based parsing of structured synthetic JSON fixtures.</p>" + \
        f"<section><h2>Entity counts</h2><table><tbody>{entity_rows}</tbody></table></section>" + \
        f"<section><h2>Edge counts</h2><table><tbody>{edge_rows}</tbody></table></section>" + \
        f"<section><h2>Contradictions</h2><ul>{''.join(contradictions) or '<li>No opposing result pairs found.</li>'}</ul></section>" + \
        f"<section><h2>Open questions</h2><ul>{question_html or '<li>No configured gaps found.</li>'}</ul></section></main></body></html>\n"
