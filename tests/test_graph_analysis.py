from pgr.analysis import derive_questions, detect_contradictions
from pgr.export import graph_json_bytes, graphml_bytes
from pgr.graph import build_graph


def test_graph_node_and_edge_counts_match_fixture_hand_count(pipeline):
    graph = pipeline["graph"]
    assert len(graph["nodes"]) == 14
    assert len(graph["edges"]) == 21
    assert sum(node["type"] == "paper" for node in graph["nodes"]) == 3
    assert sum(node["type"] == "claim" for node in graph["nodes"]) == 3
    assert sum(node["type"] == "method" for node in graph["nodes"]) == 3
    assert sum(node["type"] == "dataset" for node in graph["nodes"]) == 2
    assert sum(node["type"] == "model" for node in graph["nodes"]) == 3
    assert {edge["type"] for edge in graph["edges"]} >= {
        "cites", "uses-method", "uses-dataset", "evaluates-on", "claims-result", "supports", "contradicts"
    }
    contradiction_edge = next(edge for edge in graph["edges"] if edge["type"] == "contradicts")
    assert contradiction_edge["contradiction"]["claim_ids"] == ["claim-fall", "claim-rise"]


def test_contradictions_have_both_claims_and_result_evidence(pipeline):
    found = detect_contradictions(pipeline["entities"])
    assert len(found) == 1
    item = found[0]
    assert item["claim_ids"] == ["claim-fall", "claim-rise"]
    assert item["paper_ids"] == ["paper-fall", "paper-rise"]
    assert item["dataset_id"] == "dataset-shared"
    assert item["directions"] == ["worsens", "improves"]
    assert item["fixture_annotated"] is True
    assert item["confirmed_by_rule"] is True
    assert {record["claim_id"] for record in item["evidence"]} == {"claim-fall", "claim-rise"}
    assert {record["observed"] for record in item["evidence"]} == {0.65, 0.81}
    assert all(record["dataset_id"] == "dataset-shared" for record in item["evidence"])


def test_neutral_and_different_dataset_claims_do_not_form_false_pairs(pipeline):
    entities = pipeline["entities"]
    claim_rise = next(item for item in entities["claims"] if item["id"] == "claim-rise")
    claim_rise["result"]["direction"] = "neutral"
    assert detect_contradictions(entities) == []


def test_questions_cite_each_gap(pipeline):
    questions = derive_questions(pipeline["graph"])["questions"]
    by_type = {}
    for item in questions:
        by_type.setdefault(item["type"], []).append(item)
    method = next(item for item in by_type["method_without_evaluation"] if item["entity_id"] == "method-unchecked")
    assert method["gap"] == {"method_id": "method-unchecked", "evaluated_datasets": []}
    claim = next(item for item in by_type["single_paper_support"] if item["entity_id"] == "claim-rise")
    assert claim["gap"] == {"claim_id": "claim-rise", "supporting_paper_ids": ["paper-rise"]}
    dataset = next(item for item in by_type["single_method_dataset"] if item["entity_id"] == "dataset-niche")
    assert dataset["gap"] == {"dataset_id": "dataset-niche", "method_ids": ["method-unchecked"]}


def test_repeated_full_pipeline_has_byte_identical_graph_json(tmp_path, pipeline):
    from pgr.extract import extract_papers
    from pgr.fixtures import generate_fixtures

    other_papers = generate_fixtures(tmp_path / "second" / "papers")
    other_entities = extract_papers(other_papers)
    other_graph = build_graph(other_entities)
    first_bytes = graph_json_bytes(pipeline["graph"])
    second_bytes = graph_json_bytes(other_graph)
    assert first_bytes == second_bytes


def test_graphml_export_is_valid_xml_and_contains_synthetic_notice(pipeline):
    import xml.etree.ElementTree as ET

    data = graphml_bytes(pipeline["graph"])
    root = ET.fromstring(data)
    joined = " ".join(element.text or "" for element in root.iter())
    assert root.tag.endswith("graphml")
    assert "Synthetic fixture papers only" in joined
    assert len([element for element in root.iter() if element.tag.endswith("node")]) == 14
