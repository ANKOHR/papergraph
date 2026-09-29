import math
from pathlib import Path

from .constants import EXTRACTION_METHOD, FORMAT_VERSION, NOTICE
from .errors import PaperFormatError
from .io_utils import read_json, write_json

_DIRECTIONS = {"improves", "worsens", "neutral"}


def _fail(filename, field, problem):
    raise PaperFormatError(f"{filename}: {field}: {problem}")


def _object(value, filename, field):
    if not isinstance(value, dict):
        _fail(filename, field, "expected an object")
    return value


def _list(value, filename, field):
    if not isinstance(value, list):
        _fail(filename, field, "expected a list")
    return value


def _string(value, filename, field):
    if not isinstance(value, str) or not value.strip():
        _fail(filename, field, "expected a non-empty string")
    return value.strip()


def _string_list(value, filename, field):
    values = _list(value, filename, field)
    result = [_string(item, filename, f"{field}[{index}]") for index, item in enumerate(values)]
    if len(result) != len(set(result)):
        _fail(filename, field, "values must be unique")
    return result


def _claim_result(value, filename, field):
    result = _object(value, filename, field)
    metric = _string(result.get("metric"), filename, f"{field}.metric")
    direction = _string(result.get("direction"), filename, f"{field}.direction")
    if direction not in _DIRECTIONS:
        _fail(filename, f"{field}.direction", f"expected one of {', '.join(sorted(_DIRECTIONS))}")
    for key in ("baseline", "observed"):
        number = result.get(key)
        if isinstance(number, bool) or not isinstance(number, (int, float)):
            _fail(filename, f"{field}.{key}", "expected a number")
        if isinstance(number, float) and not math.isfinite(number):
            _fail(filename, f"{field}.{key}", "expected a finite number")
    return {"metric": metric, "baseline": result["baseline"], "observed": result["observed"], "direction": direction}


def extract_papers(papers_dir):
    """Parse and validate structured synthetic JSON papers into typed records."""
    papers_dir = Path(papers_dir)
    if not papers_dir.is_dir():
        raise PaperFormatError(f"Paper directory not found: {papers_dir}")
    files = sorted(papers_dir.glob("*.json"), key=lambda item: item.name.casefold())
    if not files:
        raise PaperFormatError(f"No JSON paper files found in {papers_dir}")

    papers, claims, methods, datasets, models, citations = [], [], [], {}, [], []
    raw_results = []
    seen_papers, seen_claims, seen_methods, seen_models, seen_citations = set(), set(), set(), set(), set()

    for path in files:
        filename = path.name
        try:
            raw = _object(read_json(path), filename, "root")
        except PaperFormatError:
            raise
        except Exception as exc:
            _fail(filename, "json", f"could not read the paper: {exc}")
        if raw.get("synthetic") is not True:
            _fail(filename, "synthetic", "must be true because PaperGraph accepts synthetic fixtures only")
        if raw.get("schema_version") != 1:
            _fail(filename, "schema_version", "expected 1")

        paper_raw = _object(raw.get("paper"), filename, "paper")
        paper_id = _string(paper_raw.get("id"), filename, "paper.id")
        if paper_id in seen_papers:
            _fail(filename, "paper.id", f"duplicate paper ID {paper_id!r}")
        seen_papers.add(paper_id)
        title = _string(paper_raw.get("title"), filename, "paper.title")
        authors = _string_list(paper_raw.get("authors"), filename, "paper.authors")
        papers.append({"id": paper_id, "title": title, "authors": authors})

        for index, item in enumerate(_list(raw.get("datasets"), filename, "datasets")):
            field = f"datasets[{index}]"
            item = _object(item, filename, field)
            dataset_id = _string(item.get("id"), filename, f"{field}.id")
            record = {
                "id": dataset_id,
                "name": _string(item.get("name"), filename, f"{field}.name"),
                "description": item.get("description", ""),
            }
            if not isinstance(record["description"], str):
                _fail(filename, f"{field}.description", "expected a string")
            record["description"] = record["description"].strip()
            if dataset_id in datasets:
                prior = {key: val for key, val in datasets[dataset_id].items() if key != "paper_ids"}
                if prior != record:
                    _fail(filename, f"{field}.id", f"dataset {dataset_id!r} has conflicting metadata")
            if dataset_id not in datasets:
                datasets[dataset_id] = {**record, "paper_ids": []}
            datasets[dataset_id]["paper_ids"].append(paper_id)

        for index, item in enumerate(_list(raw.get("claims"), filename, "claims")):
            field = f"claims[{index}]"
            item = _object(item, filename, field)
            claim_id = _string(item.get("id"), filename, f"{field}.id")
            if claim_id in seen_claims:
                _fail(filename, f"{field}.id", f"duplicate claim ID {claim_id!r}")
            seen_claims.add(claim_id)
            group = item.get("contradiction_group")
            if group is not None:
                group = _string(group, filename, f"{field}.contradiction_group")
            support = item.get("supporting_papers", [paper_id])
            support = _string_list(support, filename, f"{field}.supporting_papers")
            result = _claim_result(item.get("result"), filename, f"{field}.result")
            claim_dataset = _string(item.get("dataset_id"), filename, f"{field}.dataset_id")
            claims.append({
                "id": claim_id,
                "paper_id": paper_id,
                "text": _string(item.get("text"), filename, f"{field}.text"),
                "dataset_id": claim_dataset,
                "result": result,
                "contradiction_group": group,
                "supporting_papers": support,
            })

        for index, item in enumerate(_list(raw.get("methods"), filename, "methods")):
            field = f"methods[{index}]"
            item = _object(item, filename, field)
            method_id = _string(item.get("id"), filename, f"{field}.id")
            if method_id in seen_methods:
                _fail(filename, f"{field}.id", f"duplicate method ID {method_id!r}")
            seen_methods.add(method_id)
            uses = _string_list(item.get("uses_datasets"), filename, f"{field}.uses_datasets")
            evaluated = _string_list(item.get("evaluated_on"), filename, f"{field}.evaluated_on")
            if not set(evaluated).issubset(uses):
                _fail(filename, f"{field}.evaluated_on", "every evaluated dataset must also appear in uses_datasets")
            methods.append({
                "id": method_id,
                "paper_id": paper_id,
                "name": _string(item.get("name"), filename, f"{field}.name"),
                "uses_datasets": uses,
                "evaluated_on": evaluated,
            })

        for index, item in enumerate(_list(raw.get("models"), filename, "models")):
            field = f"models[{index}]"
            item = _object(item, filename, field)
            model_id = _string(item.get("id"), filename, f"{field}.id")
            if model_id in seen_models:
                _fail(filename, f"{field}.id", f"duplicate model ID {model_id!r}")
            seen_models.add(model_id)
            models.append({"id": model_id, "paper_id": paper_id, "name": _string(item.get("name"), filename, f"{field}.name")})

        for index, item in enumerate(_list(raw.get("citations"), filename, "citations")):
            field = f"citations[{index}]"
            item = _object(item, filename, field)
            citation_id = _string(item.get("id"), filename, f"{field}.id")
            if citation_id in seen_citations:
                _fail(filename, f"{field}.id", f"duplicate citation ID {citation_id!r}")
            seen_citations.add(citation_id)
            reference_title = item.get("reference_title", "")
            if not isinstance(reference_title, str):
                _fail(filename, f"{field}.reference_title", "expected a string")
            citations.append({
                "id": citation_id,
                "paper_id": paper_id,
                "target_paper_id": _string(item.get("target_paper_id"), filename, f"{field}.target_paper_id"),
                "reference_title": reference_title.strip(),
            })

        for index, item in enumerate(_list(raw.get("results"), filename, "results")):
            field = f"results[{index}]"
            item = _object(item, filename, field)
            result = _claim_result(item, filename, field)
            raw_results.append({
                "filename": filename,
                "paper_id": paper_id,
                "claim_id": _string(item.get("claim_id"), filename, f"{field}.claim_id"),
                "dataset_id": _string(item.get("dataset_id"), filename, f"{field}.dataset_id"),
                **result,
            })

    known_papers = {paper["id"] for paper in papers}
    known_datasets = set(datasets)
    known_claims = {claim["id"]: claim for claim in claims}
    for claim in claims:
        if claim["dataset_id"] not in known_datasets:
            _fail("collection", f"claims.{claim['id']}.dataset_id", f"unknown dataset ID {claim['dataset_id']!r}")
        for paper_id in claim["supporting_papers"]:
            if paper_id not in known_papers:
                _fail("collection", f"claims.{claim['id']}.supporting_papers", f"unknown paper ID {paper_id!r}")
    for method in methods:
        for dataset_id in method["uses_datasets"]:
            if dataset_id not in known_datasets:
                _fail("collection", f"methods.{method['id']}.uses_datasets", f"unknown dataset ID {dataset_id!r}")
    for citation in citations:
        if citation["target_paper_id"] not in known_papers:
            _fail("collection", f"citations.{citation['id']}.target_paper_id", f"unknown paper ID {citation['target_paper_id']!r}")

    result_by_claim = {}
    for result in raw_results:
        claim_id = result["claim_id"]
        if claim_id in result_by_claim:
            _fail(result["filename"], "results", f"duplicate result row for claim {claim_id!r}")
        if claim_id not in known_claims:
            _fail(result["filename"], "results.claim_id", f"unknown claim ID {claim_id!r}")
        claim = known_claims[claim_id]
        if result["paper_id"] != claim["paper_id"]:
            _fail(result["filename"], f"results.{claim_id}", "result row must be in the claim's source paper")
        expected = {"dataset_id": claim["dataset_id"], **claim["result"]}
        actual = {key: result[key] for key in expected}
        if actual != expected:
            _fail(result["filename"], f"results.{claim_id}", "result table row does not match the claim")
        result_by_claim[claim_id] = actual
    missing_results = sorted(set(known_claims) - set(result_by_claim))
    if missing_results:
        _fail("collection", "results", f"missing result rows for claims: {', '.join(missing_results)}")

    for record in datasets.values():
        record["paper_ids"] = sorted(set(record["paper_ids"]))
    return {
        "format_version": FORMAT_VERSION,
        "synthetic": True,
        "notice": NOTICE,
        "extraction_method": EXTRACTION_METHOD,
        "papers": sorted(papers, key=lambda item: item["id"]),
        "claims": sorted(claims, key=lambda item: item["id"]),
        "methods": sorted(methods, key=lambda item: item["id"]),
        "datasets": sorted(datasets.values(), key=lambda item: item["id"]),
        "models": sorted(models, key=lambda item: item["id"]),
        "citations": sorted(citations, key=lambda item: item["id"]),
    }


def write_entities(entities, out):
    out = Path(out)
    target = out / "entities.json" if out.suffix.lower() != ".json" else out
    return write_json(target, entities)
