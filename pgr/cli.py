import argparse
import json
import sys
from pathlib import Path

from .analysis import contradictions_from_graph, derive_questions
from .constants import NOTICE
from .errors import PaperGraphError
from .export import graph_json_bytes, graphml_bytes
from .extract import extract_papers, write_entities
from .fixtures import generate_fixtures
from .graph import build_graph, write_graph
from .io_utils import read_json, resolve_json_path
from .report import render_html, render_markdown


def _parser():
    honesty = f"{NOTICE}\nExtraction is rule-based parsing of structured fixture JSON, not NLP over real PDFs."
    parser = argparse.ArgumentParser(
        prog="pgr", description="Build and inspect graphs from synthetic structured paper fixtures.", epilog=honesty
    )
    commands = parser.add_subparsers(dest="command", required=True)

    fixtures = commands.add_parser("fixtures", help="write deterministic synthetic fixture papers", epilog=honesty)
    fixtures.add_argument("--out", required=True, type=Path, help="directory for the JSON fixture papers")

    extract = commands.add_parser("extract", help="parse structured synthetic papers into typed entities", epilog=honesty)
    extract.add_argument("--papers", required=True, type=Path, help="directory containing paper JSON files")
    extract.add_argument("--out", type=Path, default=Path("entities"), help="output directory or entities.json path")

    graph = commands.add_parser("graph", help="build a deterministic graph from extracted entities", epilog=honesty)
    graph.add_argument("--entities", required=True, type=Path, help="entity directory or entities.json path")
    graph.add_argument("--out", type=Path, default=Path("graph.json"), help="output graph JSON path")

    contradictions = commands.add_parser("contradictions", help="list opposing result claims with evidence", epilog=honesty)
    contradictions.add_argument("--graph", required=True, type=Path, help="graph JSON file")

    questions = commands.add_parser("questions", help="derive open questions from graph gaps", epilog=honesty)
    questions.add_argument("--graph", required=True, type=Path, help="graph JSON file")

    query = commands.add_parser("query", help="traverse from a claim or graph node", epilog=honesty)
    query.add_argument("--graph", required=True, type=Path, help="graph JSON file")
    start = query.add_mutually_exclusive_group(required=True)
    start.add_argument("--claim", help="claim source ID, for example claim-rise")
    start.add_argument("--node", help="typed node ID such as paper:paper-rise, or an unambiguous source ID")
    query.add_argument("--depth", type=int, default=3, help="maximum number of relationship steps, default 3")

    export = commands.add_parser("export", help="export a graph as JSON or GraphML", epilog=honesty)
    export.add_argument("--graph", required=True, type=Path, help="graph JSON file")
    export.add_argument("--format", required=True, choices=("json", "graphml"))
    export.add_argument("--out", type=Path, help="output file, defaults to standard output")

    report = commands.add_parser("report", help="render entity counts, contradictions, and open questions", epilog=honesty)
    report.add_argument("--graph", required=True, type=Path, help="graph JSON file")
    report.add_argument("--format", required=True, choices=("md", "html"))
    report.add_argument("--out", type=Path, help="output file, defaults to standard output")
    return parser


def _load_graph(path):
    graph = read_json(path)
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        raise PaperGraphError(f"Not a PaperGraph graph JSON file: {path}")
    return graph


def _load_entities(path):
    entities = read_json(resolve_json_path(path, "entities.json"))
    required = ("papers", "claims", "methods", "datasets", "models", "citations")
    if not isinstance(entities, dict) or any(not isinstance(entities.get(key), list) for key in required):
        raise PaperGraphError(f"Not a PaperGraph entity JSON file: {path}")
    return entities


def _node_id(graph, raw_id, expected_type=None):
    ids = {node["id"] for node in graph["nodes"]}
    if raw_id in ids:
        if expected_type and not raw_id.startswith(f"{expected_type}:"):
            raise PaperGraphError(f"Node {raw_id!r} is not a {expected_type} node")
        return raw_id
    if expected_type:
        candidate = f"{expected_type}:{raw_id}"
        if candidate in ids:
            return candidate
        raise PaperGraphError(f"No {expected_type} node found for ID {raw_id!r}")
    matches = [node["id"] for node in graph["nodes"] if node["source_id"] == raw_id]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise PaperGraphError(f"Source ID {raw_id!r} is ambiguous. Use a typed node ID.")
    raise PaperGraphError(f"No graph node found for ID {raw_id!r}")


def _traverse(graph, start_id, max_depth):
    adjacency = {}
    for edge in graph["edges"]:
        adjacency.setdefault(edge["source"], []).append((edge["target"], edge))
        adjacency.setdefault(edge["target"], []).append((edge["source"], edge))
    distances = {start_id: 0}
    queue = [start_id]
    for current in queue:
        distance = distances[current]
        if distance >= max_depth:
            continue
        for neighbor, _ in sorted(adjacency.get(current, []), key=lambda pair: (pair[0], pair[1]["id"])):
            if neighbor not in distances:
                distances[neighbor] = distance + 1
                queue.append(neighbor)
    node_ids = set(distances)
    nodes = sorted((node for node in graph["nodes"] if node["id"] in node_ids), key=lambda item: item["id"])
    edges = sorted((edge for edge in graph["edges"] if edge["source"] in node_ids and edge["target"] in node_ids), key=lambda item: item["id"])
    return nodes, edges


def _emit_json(value):
    sys.stdout.buffer.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8") + b"\n")


def main(argv=None):
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "fixtures":
            directory = generate_fixtures(args.out)
            print(f"Wrote 3 synthetic fixture papers to {directory}. {NOTICE}")
        elif args.command == "extract":
            entities = extract_papers(args.papers)
            target = write_entities(entities, args.out)
            print(f"Extracted {len(entities['claims'])} claims, {len(entities['methods'])} methods, {len(entities['datasets'])} datasets, {len(entities['models'])} models, and {len(entities['citations'])} citations to {target}. {NOTICE}")
        elif args.command == "graph":
            graph = build_graph(_load_entities(args.entities))
            target = write_graph(graph, args.out)
            print(f"Built graph with {len(graph['nodes'])} nodes and {len(graph['edges'])} edges at {target}. {NOTICE}")
        elif args.command == "contradictions":
            graph = _load_graph(args.graph)
            _emit_json({"synthetic": True, "notice": NOTICE, "contradictions": contradictions_from_graph(graph)})
        elif args.command == "questions":
            _emit_json(derive_questions(_load_graph(args.graph)))
        elif args.command == "query":
            if args.depth < 0:
                raise PaperGraphError("--depth must be zero or greater")
            graph = _load_graph(args.graph)
            start_id = _node_id(graph, args.claim, "claim") if args.claim is not None else _node_id(graph, args.node)
            nodes, edges = _traverse(graph, start_id, args.depth)
            _emit_json({
                "synthetic": True,
                "notice": NOTICE,
                "start_node": start_id,
                "depth": args.depth,
                "nodes": nodes,
                "edges": edges,
            })
        elif args.command == "export":
            graph = _load_graph(args.graph)
            data = graph_json_bytes(graph) if args.format == "json" else graphml_bytes(graph)
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_bytes(data)
                print(f"Exported synthetic rule-based graph as {args.format} to {args.out}. {NOTICE}")
            else:
                sys.stdout.buffer.write(data)
        elif args.command == "report":
            graph = _load_graph(args.graph)
            text = render_markdown(graph) if args.format == "md" else render_html(graph)
            data = text.encode("utf-8")
            if args.out:
                args.out.parent.mkdir(parents=True, exist_ok=True)
                args.out.write_bytes(data)
                print(f"Wrote synthetic rule-based {args.format} report to {args.out}. {NOTICE}")
            else:
                sys.stdout.buffer.write(data)
        return 0
    except (PaperGraphError, OSError, ValueError) as exc:
        print(f"pgr: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
