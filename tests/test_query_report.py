from pgr.cli import _traverse
from pgr.report import render_html, render_markdown


def test_query_traversal_from_claim_returns_paper_method_and_dataset(pipeline):
    nodes, edges = _traverse(pipeline["graph"], "claim:claim-rise", 3)
    typed = {(node["type"], node["source_id"]) for node in nodes}
    assert ("claim", "claim-rise") in typed
    assert ("paper", "paper-rise") in typed
    assert ("method", "method-rise") in typed
    assert ("dataset", "dataset-shared") in typed
    assert any(edge["type"] == "evaluates-on" for edge in edges)


def test_report_includes_counts_contradiction_gap_and_honesty_banner(pipeline):
    markdown = render_markdown(pipeline["graph"])
    html = render_html(pipeline["graph"])
    assert "Entity counts" in markdown
    assert "claim-fall, claim-rise" in markdown
    assert "method-unchecked" in markdown
    assert "supporting paper" in markdown
    assert "SYNTHETIC" in markdown
    assert 'class="banner"' in html
    assert "Synthetic fixture papers only" in html
    assert "not NLP over real PDFs" in html
    assert "claim-fall" in html and "method-unchecked" in html
