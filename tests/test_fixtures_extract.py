import json

import pytest

from pgr.errors import PaperFormatError
from pgr.extract import extract_papers, write_entities
from pgr.fixtures import fixture_papers, generate_fixtures


def test_fixture_generation_has_planted_contradiction_and_unevaluated_method(tmp_path):
    expected = fixture_papers()
    out = generate_fixtures(tmp_path / "papers")
    files = sorted(out.glob("*.json"))
    assert len(files) == 3
    papers = [json.loads(path.read_text(encoding="utf-8")) for path in files]
    claims = [claim for paper in papers for claim in paper["claims"]]
    opposing = [claim for claim in claims if claim.get("contradiction_group") == "planted-shared-score"]
    assert {claim["result"]["direction"] for claim in opposing} == {"improves", "worsens"}
    assert {claim["dataset_id"] for claim in opposing} == {"dataset-shared"}
    methods = [method for paper in papers for method in paper["methods"]]
    assert any(method["id"] == "method-unchecked" and method["evaluated_on"] == [] for method in methods)
    assert len(expected) == 3


def test_fixture_files_are_byte_identical_across_runs(tmp_path):
    first = generate_fixtures(tmp_path / "first")
    second = generate_fixtures(tmp_path / "second")
    first_files = sorted(first.glob("*.json"), key=lambda path: path.name)
    second_files = sorted(second.glob("*.json"), key=lambda path: path.name)
    assert [path.name for path in first_files] == [path.name for path in second_files]
    assert [path.read_bytes() for path in first_files] == [path.read_bytes() for path in second_files]


def test_extraction_returns_all_typed_entities_with_ids(pipeline):
    entities = pipeline["entities"]
    assert [paper["id"] for paper in entities["papers"]] == ["paper-explore", "paper-fall", "paper-rise"]
    assert {item["id"] for item in entities["claims"]} == {"claim-rise", "claim-fall", "claim-explore"}
    assert {item["id"] for item in entities["methods"]} == {"method-rise", "method-fall", "method-unchecked"}
    assert {item["id"] for item in entities["datasets"]} == {"dataset-shared", "dataset-niche"}
    assert {item["id"] for item in entities["models"]} == {"model-rise", "model-fall", "model-explore"}
    assert {item["id"] for item in entities["citations"]} == {
        "citation-rise-fall", "citation-fall-rise", "citation-explore-rise"
    }
    shared = next(item for item in entities["datasets"] if item["id"] == "dataset-shared")
    assert shared["paper_ids"] == ["paper-fall", "paper-rise"]
    assert entities["synthetic"] is True
    assert entities["extraction_method"] == "rule_based_structured_json"


def test_malformed_paper_has_named_error(tmp_path):
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    (papers_dir / "bad-paper.json").write_text(json.dumps({"synthetic": True, "schema_version": 1, "paper": {"title": "No ID"}}))
    with pytest.raises(PaperFormatError, match=r"bad-paper\.json: paper\.id"):
        extract_papers(papers_dir)


def test_non_synthetic_input_is_rejected(tmp_path):
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    (papers_dir / "real-paper.json").write_text(json.dumps({"synthetic": False}))
    with pytest.raises(PaperFormatError, match=r"real-paper\.json: synthetic"):
        extract_papers(papers_dir)


def test_non_finite_result_value_is_rejected_with_paper_name(tmp_path):
    papers_dir = tmp_path / "papers"
    papers_dir.mkdir()
    paper = fixture_papers()[0]
    paper["claims"][0]["result"]["baseline"] = float("nan")
    paper["results"][0]["baseline"] = float("nan")
    (papers_dir / "paper-rise.json").write_text(json.dumps(paper), encoding="utf-8")
    with pytest.raises(PaperFormatError, match=r"paper-rise\.json: claims\[0\]\.result\.baseline: expected a finite number"):
        extract_papers(papers_dir)


def test_entity_json_writer_supports_directory_and_file(tmp_path, pipeline):
    directory_path = write_entities(pipeline["entities"], tmp_path / "entities")
    file_path = write_entities(pipeline["entities"], tmp_path / "another.json")
    assert directory_path.name == "entities.json"
    assert file_path.name == "another.json"
    assert directory_path.read_bytes() == file_path.read_bytes()
