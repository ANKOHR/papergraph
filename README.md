# PaperGraph

PaperGraph turns a pile of papers into a map: who claims what, what it was tested on, where the claims collide, and what nobody has tried yet.

This project operates only on synthetic fixture papers in a structured JSON format. It does not analyse real publications or PDFs. Extraction is deterministic, rule-based parsing of fixture fields.

## Quickstart

```powershell
python -m pip install -e .
pgr fixtures --out fixtures
pgr extract --papers fixtures --out build/entities
pgr graph --entities build/entities --out build/graph.json
pgr contradictions --graph build/graph.json
pgr questions --graph build/graph.json
pgr report --graph build/graph.json --format md
pgr query --graph build/graph.json --claim claim-boosted
pgr export --graph build/graph.json --format graphml --out build/graph.graphml
pytest
```

All commands identify the data as synthetic and the extraction as rule-based. The CLI uses only Python's standard library at runtime.

## Architecture

```text
Synthetic JSON fixtures
          |
          v
Rule-based structured extraction
          |
          v
Typed entity collection
          |
          v
Deterministic graph builder ----> JSON or GraphML export
          |             |
          |             +--------> Claim and node traversal
          v
Contradiction rules -----------> Evidence-linked claim pairs
          |
          v
Open-question rules ----------> Evidence-linked research gaps
          |
          v
Markdown or HTML report
```

## HONESTY BOUNDARY

The papers are SYNTHETIC fixtures, NOT real publications. Extraction is RULE-BASED parsing of a structured fixture format, NOT NLP over real PDFs. PaperGraph does not claim real literature analysis, real citation data, or real scientific findings. CLI output, exported graph metadata, and reports label the data as synthetic and the extraction as rule-based. The HTML report displays a synthetic data banner.

## Fixture paper format reference

Each UTF-8 JSON file has `schema_version: 1` and `synthetic: true`, plus these fields:

- `paper`: globally unique `id`, `title`, and `authors` string list.
- `claims`: globally unique `id`, `text`, `dataset_id`, `result`, optional `contradiction_group`, and optional `supporting_papers` list. `result` contains `metric`, `baseline`, `observed`, and a `direction` of `improves`, `worsens`, or `neutral`. `supporting_papers` defaults to the current paper.
- `methods`: globally unique `id`, `name`, `uses_datasets` list, and `evaluated_on` list. A method can use a dataset without evaluating it.
- `datasets`: `id`, `name`, and optional `description`. A dataset can be declared by multiple papers if its ID and metadata agree.
- `models`: globally unique `id` and `name`.
- `citations`: globally unique `id`, `target_paper_id`, and optional `reference_title`. Citation targets must be in the fixture collection.
- `results`: one row per claim, with `claim_id`, `dataset_id`, `metric`, `baseline`, `observed`, and `direction`. These rows provide the cited evidence for contradiction records.

All referenced IDs must resolve. Files must be synthetic JSON papers of the documented schema. The fixture generator uses no random numbers, so no seed is needed.

## Contradiction rule

PaperGraph compares claims on the same dataset. It flags a pair when one result direction is `improves` and the other is `worsens`. A shared non-empty `contradiction_group` marks fixture annotation, and the heuristic still has to confirm the opposing directions before the pair is emitted. Each record and `contradicts` graph edge names both claim IDs, their papers, the dataset, and each result row's metric, baseline, observed value, and direction. Neutral results do not form contradictions.

## Open-question rules

PaperGraph derives three kinds of gap:

1. A method with no `evaluates-on` edge is unevaluated.
2. A claim supported by exactly one distinct paper has single-paper support.
3. A dataset used by exactly one distinct method has narrow method coverage.

Each question includes the relevant entity ID and a concise statement of the graph evidence behind the gap. A method may list a dataset under `uses_datasets` without evaluating it, which can produce both an unevaluated-method question and a single-method dataset question.

## CLI commands

- `pgr fixtures --out DIR` writes the deterministic synthetic collection.
- `pgr extract --papers DIR [--out DIR]` parses structured files into `entities.json`.
- `pgr graph --entities DIR [--out FILE]` creates the graph and its contradiction edges.
- `pgr contradictions --graph FILE` prints evidence-linked contradictions.
- `pgr questions --graph FILE` prints evidence-linked open questions.
- `pgr query --graph FILE (--claim ID | --node ID) [--depth N]` traverses the graph.
- `pgr export --graph FILE --format graphml|json [--out FILE]` exports the graph.
- `pgr report --graph FILE --format md|html [--out FILE]` creates a report.

PaperGraph sorts records and uses IDs derived from source IDs and edge types, making repeated runs byte-identical for the same input files.
