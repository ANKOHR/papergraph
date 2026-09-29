from pathlib import Path

from .io_utils import write_json


def fixture_papers():
    """Return the fixed synthetic fixture collection. No random values are used."""
    return [
        {
            "schema_version": 1,
            "synthetic": True,
            "paper": {"id": "paper-rise", "title": "A synthetic improvement study", "authors": ["Fixture Author A"]},
            "claims": [{
                "id": "claim-rise", "text": "Method Rise improves the benchmark score.",
                "dataset_id": "dataset-shared", "contradiction_group": "planted-shared-score",
                "supporting_papers": ["paper-rise"],
                "result": {"metric": "score", "baseline": 0.72, "observed": 0.81, "direction": "improves"},
            }],
            "methods": [{"id": "method-rise", "name": "Method Rise", "uses_datasets": ["dataset-shared"], "evaluated_on": ["dataset-shared"]}],
            "datasets": [{"id": "dataset-shared", "name": "Shared Synthetic Benchmark", "description": "A made-up shared evaluation dataset."}],
            "models": [{"id": "model-rise", "name": "Synthetic Model Rise"}],
            "citations": [{"id": "citation-rise-fall", "target_paper_id": "paper-fall", "reference_title": "A synthetic decline study"}],
            "results": [{"claim_id": "claim-rise", "dataset_id": "dataset-shared", "metric": "score", "baseline": 0.72, "observed": 0.81, "direction": "improves"}],
        },
        {
            "schema_version": 1,
            "synthetic": True,
            "paper": {"id": "paper-fall", "title": "A synthetic decline study", "authors": ["Fixture Author B"]},
            "claims": [{
                "id": "claim-fall", "text": "Method Fall reduces the benchmark score.",
                "dataset_id": "dataset-shared", "contradiction_group": "planted-shared-score",
                "supporting_papers": ["paper-fall"],
                "result": {"metric": "score", "baseline": 0.72, "observed": 0.65, "direction": "worsens"},
            }],
            "methods": [{"id": "method-fall", "name": "Method Fall", "uses_datasets": ["dataset-shared"], "evaluated_on": ["dataset-shared"]}],
            "datasets": [{"id": "dataset-shared", "name": "Shared Synthetic Benchmark", "description": "A made-up shared evaluation dataset."}],
            "models": [{"id": "model-fall", "name": "Synthetic Model Fall"}],
            "citations": [{"id": "citation-fall-rise", "target_paper_id": "paper-rise", "reference_title": "A synthetic improvement study"}],
            "results": [{"claim_id": "claim-fall", "dataset_id": "dataset-shared", "metric": "score", "baseline": 0.72, "observed": 0.65, "direction": "worsens"}],
        },
        {
            "schema_version": 1,
            "synthetic": True,
            "paper": {"id": "paper-explore", "title": "A synthetic unevaluated proposal", "authors": ["Fixture Author C"]},
            "claims": [{
                "id": "claim-explore", "text": "A proposed approach may improve response time.",
                "dataset_id": "dataset-niche", "supporting_papers": ["paper-explore"],
                "result": {"metric": "latency_ms", "baseline": 120, "observed": 118, "direction": "improves"},
            }],
            "methods": [{"id": "method-unchecked", "name": "Unchecked Proposal", "uses_datasets": ["dataset-niche"], "evaluated_on": []}],
            "datasets": [{"id": "dataset-niche", "name": "Niche Synthetic Dataset", "description": "A made-up dataset used by one method without evaluation."}],
            "models": [{"id": "model-explore", "name": "Synthetic Model Explore"}],
            "citations": [{"id": "citation-explore-rise", "target_paper_id": "paper-rise", "reference_title": "A synthetic improvement study"}],
            "results": [{"claim_id": "claim-explore", "dataset_id": "dataset-niche", "metric": "latency_ms", "baseline": 120, "observed": 118, "direction": "improves"}],
        },
    ]


def generate_fixtures(out_dir):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    for paper in fixture_papers():
        write_json(out_dir / f"{paper['paper']['id']}.json", paper)
    return out_dir
