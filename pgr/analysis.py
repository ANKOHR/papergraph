from .constants import NOTICE

_OPPOSITES = {"improves": "worsens", "worsens": "improves"}


def detect_contradictions(entities):
    """Find same-dataset claim pairs with opposing structured result directions."""
    claims = sorted(entities["claims"], key=lambda item: item["id"])
    found = []
    for index, left in enumerate(claims):
        for right in claims[index + 1:]:
            left_direction = left["result"]["direction"]
            right_direction = right["result"]["direction"]
            if left["dataset_id"] != right["dataset_id"] or _OPPOSITES.get(left_direction) != right_direction:
                continue
            group_a, group_b = left.get("contradiction_group"), right.get("contradiction_group")
            found.append({
                "claim_ids": [left["id"], right["id"]],
                "paper_ids": [left["paper_id"], right["paper_id"]],
                "dataset_id": left["dataset_id"],
                "directions": [left_direction, right_direction],
                "fixture_annotated": bool(group_a and group_a == group_b),
                "annotation_group": group_a if group_a and group_a == group_b else None,
                "confirmed_by_rule": True,
                "rule": "same dataset and opposing improves/worsens result directions",
                "evidence": [
                    {"claim_id": claim["id"], "paper_id": claim["paper_id"], "dataset_id": claim["dataset_id"], **claim["result"]}
                    for claim in (left, right)
                ],
            })
    return found


def contradictions_from_graph(graph):
    return sorted(
        [edge["contradiction"] for edge in graph["edges"] if edge["type"] == "contradicts"],
        key=lambda item: tuple(item["claim_ids"]),
    )


def derive_questions(graph):
    nodes = {node["id"]: node for node in graph["nodes"]}
    edges = graph["edges"]
    used = {}
    evaluated = set()
    supports = {}
    for edge in edges:
        if edge["type"] == "uses-dataset":
            used.setdefault(edge["target"], set()).add(edge["source"])
        elif edge["type"] == "evaluates-on":
            evaluated.add(edge["source"])
        elif edge["type"] == "supports":
            supports.setdefault(edge["source"], set()).add(edge["target"])

    questions = []
    for node in sorted(graph["nodes"], key=lambda item: item["id"]):
        if node["type"] == "method" and node["id"] not in evaluated:
            questions.append({
                "id": f"question:method-without-evaluation:{node['source_id']}",
                "type": "method_without_evaluation",
                "entity_id": node["source_id"],
                "question": f"How does method {node['source_id']} perform? No evaluation edge is recorded.",
                "gap": {"method_id": node["source_id"], "evaluated_datasets": []},
            })
        elif node["type"] == "claim":
            paper_ids = sorted(nodes[paper_id]["source_id"] for paper_id in supports.get(node["id"], set()))
            if len(paper_ids) == 1:
                questions.append({
                    "id": f"question:single-paper-support:{node['source_id']}",
                    "type": "single_paper_support",
                    "entity_id": node["source_id"],
                    "question": f"Can claim {node['source_id']} be independently supported? It has one supporting paper.",
                    "gap": {"claim_id": node["source_id"], "supporting_paper_ids": paper_ids},
                })
        elif node["type"] == "dataset":
            method_ids = sorted(nodes[method_id]["source_id"] for method_id in used.get(node["id"], set()))
            if len(method_ids) == 1:
                questions.append({
                    "id": f"question:single-method-dataset:{node['source_id']}",
                    "type": "single_method_dataset",
                    "entity_id": node["source_id"],
                    "question": f"What other methods work on dataset {node['source_id']}? It is used by one method.",
                    "gap": {"dataset_id": node["source_id"], "method_ids": method_ids},
                })

    return {"synthetic": True, "notice": NOTICE, "questions": sorted(questions, key=lambda item: item["id"])}
