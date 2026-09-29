import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_pgr(*args, cwd=None):
    env = os.environ.copy()
    current = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(ROOT) + (os.pathsep + current if current else "")
    return subprocess.run(
        [sys.executable, "-m", "pgr", *map(str, args)], cwd=cwd or ROOT,
        env=env, capture_output=True, text=True, check=False,
    )


def test_cli_smoke_all_subcommands_and_end_to_end(tmp_path):
    papers = tmp_path / "papers"
    entities = tmp_path / "entities"
    graph = tmp_path / "graph.json"
    generated = run_pgr("fixtures", "--out", papers)
    assert generated.returncode == 0, generated.stderr
    assert "synthetic fixture papers" in generated.stdout
    assert len(list(papers.glob("*.json"))) == 3

    extracted = run_pgr("extract", "--papers", papers, "--out", entities)
    assert extracted.returncode == 0, extracted.stderr
    assert (entities / "entities.json").exists()
    assert "rule-based parsing" in extracted.stdout

    built = run_pgr("graph", "--entities", entities, "--out", graph)
    assert built.returncode == 0, built.stderr
    graph_data = json.loads(graph.read_text(encoding="utf-8"))
    assert len(graph_data["nodes"]) == 14
    assert len(graph_data["edges"]) == 21

    contradictions = run_pgr("contradictions", "--graph", graph)
    assert contradictions.returncode == 0, contradictions.stderr
    contradiction_data = json.loads(contradictions.stdout)
    assert contradiction_data["contradictions"][0]["claim_ids"] == ["claim-fall", "claim-rise"]

    questions = run_pgr("questions", "--graph", graph)
    assert questions.returncode == 0, questions.stderr
    question_data = json.loads(questions.stdout)
    assert any(item["entity_id"] == "method-unchecked" for item in question_data["questions"])

    query = run_pgr("query", "--graph", graph, "--claim", "claim-rise")
    assert query.returncode == 0, query.stderr
    query_data = json.loads(query.stdout)
    assert {node["type"] for node in query_data["nodes"]} >= {"paper", "method", "dataset"}

    markdown_path = tmp_path / "report.md"
    report = run_pgr("report", "--graph", graph, "--format", "md", "--out", markdown_path)
    assert report.returncode == 0, report.stderr
    assert "SYNTHETIC" in markdown_path.read_text(encoding="utf-8")
    html_path = tmp_path / "report.html"
    report_html = run_pgr("report", "--graph", graph, "--format", "html", "--out", html_path)
    assert report_html.returncode == 0, report_html.stderr
    assert 'class="banner"' in html_path.read_text(encoding="utf-8")

    json_path = tmp_path / "export.json"
    export_json = run_pgr("export", "--graph", graph, "--format", "json", "--out", json_path)
    assert export_json.returncode == 0, export_json.stderr
    assert json_path.read_bytes() == graph.read_bytes()
    graphml_path = tmp_path / "export.graphml"
    export_graphml = run_pgr("export", "--graph", graph, "--format", "graphml", "--out", graphml_path)
    assert export_graphml.returncode == 0, export_graphml.stderr
    assert b"Synthetic fixture papers only" in graphml_path.read_bytes()


def test_cli_defaults_and_named_error(tmp_path):
    papers = tmp_path / "papers"
    papers.mkdir()
    (papers / "broken.json").write_text('{"synthetic": true, "schema_version": 1, "paper": {"title": "No ID"}}', encoding="utf-8")
    result = run_pgr("extract", "--papers", papers, "--out", tmp_path / "entities")
    assert result.returncode == 2
    assert "broken.json" in result.stderr
    assert "paper" in result.stderr


def test_cli_help_states_honesty_boundary_and_project_text_avoids_em_dash():
    result = run_pgr("query", "--help")
    assert result.returncode == 0
    assert "Synthetic fixture papers only" in result.stdout
    assert "not NLP over real PDFs" in result.stdout
    sources = list((ROOT / "pgr").glob("*.py")) + list((ROOT / "tests").glob("*.py")) + [ROOT / "README.md"]
    assert all("\u2014" not in path.read_text(encoding="utf-8") for path in sources)
