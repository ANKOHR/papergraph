import json
import xml.etree.ElementTree as ET

from .io_utils import json_bytes

_NS = "http://graphml.graphdrawing.org/xmlns"
ET.register_namespace("", _NS)


def graph_json_bytes(graph):
    return json_bytes(graph)


def graphml_bytes(graph):
    root = ET.Element(f"{{{_NS}}}graphml")
    for key_id, target, name in (
        ("d0", "node", "type"), ("d1", "node", "source_id"), ("d2", "node", "label"),
        ("d3", "node", "attributes"), ("d4", "edge", "type"), ("d5", "edge", "attributes"),
        ("d6", "graph", "synthetic"), ("d7", "graph", "notice"),
        ("d8", "graph", "extraction_method"),
    ):
        ET.SubElement(root, f"{{{_NS}}}key", {"id": key_id, "for": target, "attr.name": name, "attr.type": "string"})
    graph_el = ET.SubElement(root, f"{{{_NS}}}graph", {"id": "papergraph", "edgedefault": "directed"})
    for name, key in (("synthetic", "d6"), ("notice", "d7"), ("extraction_method", "d8")):
        data = ET.SubElement(graph_el, f"{{{_NS}}}data", {"key": key})
        data.text = str(graph.get(name, ""))
    for node in graph["nodes"]:
        node_el = ET.SubElement(graph_el, f"{{{_NS}}}node", {"id": node["id"]})
        for key, value in (("d0", node["type"]), ("d1", node["source_id"]), ("d2", node["label"])):
            ET.SubElement(node_el, f"{{{_NS}}}data", {"key": key}).text = str(value)
        attrs = {key: value for key, value in node.items() if key not in {"id", "type", "source_id", "label"}}
        ET.SubElement(node_el, f"{{{_NS}}}data", {"key": "d3"}).text = json.dumps(attrs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    for edge in graph["edges"]:
        edge_el = ET.SubElement(graph_el, f"{{{_NS}}}edge", {"id": edge["id"], "source": edge["source"], "target": edge["target"]})
        ET.SubElement(edge_el, f"{{{_NS}}}data", {"key": "d4"}).text = edge["type"]
        attrs = {key: value for key, value in edge.items() if key not in {"id", "type", "source", "target"}}
        ET.SubElement(edge_el, f"{{{_NS}}}data", {"key": "d5"}).text = json.dumps(attrs, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return ET.tostring(root, encoding="utf-8", xml_declaration=True) + b"\n"
