import pytest

from pgr.extract import extract_papers
from pgr.fixtures import generate_fixtures
from pgr.graph import build_graph


@pytest.fixture
def pipeline(tmp_path):
    papers_dir = generate_fixtures(tmp_path / "papers")
    entities = extract_papers(papers_dir)
    graph = build_graph(entities)
    return {"root": tmp_path, "papers_dir": papers_dir, "entities": entities, "graph": graph}
