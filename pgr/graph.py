from pathlib import Path

from .analysis import detect_contradictions
from .constants import EXTRACTION_METHOD, GRAPH_VERSION, NOTICE
from .io_utils import read_json, resolve_json_path, write_json


def _node(kind, record, label, **extra):
    return {"id": f"{kind}:{record['id']}", "type": kind, "source_id": record["id"], "label": label, **extra}


def _edge(edge_type, source, target, **extra):
    return {"id": f"edge:{edge_type}:{source}:{target}", "type": edge_type, "source": source, "target": target, **extra}


def build_graph(entities):
    nodes, edges = [], []
    for paper in entities["papers"]:
        nodes.append(_node("paper", paper, paper["title"], authors=paper["authors"]))
    for claim in entities["claims"]:
        nodes.append(_node("claim", claim, claim["text"], paper_id=claim["paper_id"], dataset_id=claim["dataset_id"], result=claim["result"]))
        edges.append(_edge("claims-result", f"paper:{claim['paper_id']}", f"claim:{claim['id']}", evidence={"result": claim["result"], "dataset_id": claim["dataset_id"]}))
        for paper_id in claim["supporting_papers"]:
            edges.append(_edge("supports", f"claim:{claim['id']}", f"paper:{paper_id}"))
    for method in entities["methods"]:
        nodes.append(_node("method", method, method["name"], paper_id=method["paper_id"]))
        edges.append(_edge("uses-method", f"paper:{method['paper_id']}", f"method:{method['id']}"))
        for dataset_id in method["uses_datasets"]:
            edges.append(_edge("uses-dataset", f"method:{method['id']}", f"dataset:{dataset_id}"))
        for dataset_id in method["evaluated_on"]:
            edges.append(_edge("evaluates-on", f"method:{method['id']}", f"dataset:{dataset_id}"))
    for dataset in entities["datasets"]:
        nodes.append(_node("dataset", dataset, dataset["name"], description=dataset["description"]))
    for model in entities["models"]:
        nodes.append(_node("model", model, model["name"], paper_id=model["paper_id"]))
        edges.append(_edge("uses-model", f"paper:{model['paper_id']}", f"model:{model['id']}"))
    for citation in entities["citations"]:
        edges.append({
            **_edge("cites", f"paper:{citation['paper_id']}", f"paper:{citation['target_paper_id']}"),
            "id": f"edge:cites:{citation['paper_id']}:{citation['id']}",
            "citation_id": citation["id"], "reference_title": citation["reference_title"],
        })

    contradictions = detect_contradictions(entities)
    for item in contradictions:
        claim_a, claim_b = item["claim_ids"]
        edges.append(_edge("contradicts", f"claim:{claim_a}", f"claim:{claim_b}", contradiction=item))
    nodes.sort(key=lambda item: item["id"])
    edges.sort(key=lambda item: item["id"])
    return {
        "graph_version": GRAPH_VERSION,
        "synthetic": True,
        "notice": NOTICE,
        "extraction_method": EXTRACTION_METHOD,
        "nodes": nodes,
        "edges": edges,
    }


def build_graph_from_path(entities_path):
    entities = read_json(resolve_json_path(entities_path, "entities.json"))
    return build_graph(entities)


def write_graph(graph, out):
    return write_json(Path(out), graph)
