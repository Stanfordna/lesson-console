#!/usr/bin/env python3
"""Lesson Console builder: validates lesson data and materializes diagrams.

Two input modes:

  build.py lesson.html [more.html ...]
      Re-reads the lesson-data JSON embedded in each HTML file, validates it,
      and regenerates the SCENES and ATLAS blocks in place.

  build.py lesson.json --template template.html --output lesson.html
      Full generation from a standalone JSON source: title, initial
      LESSON_STATE, embedded data block, scenes, and atlas levels.

Flags:
  --check     Validate and report whether generated blocks are stale, without
              writing anything. Exit 1 if a rebuild would change the file.

Scenes and atlas levels are declarative views over one normalized graph
(nodes and edges declared once); this script materializes them as static
Mermaid blocks so a local server and a strict-CSP static host render through
the identical pipeline, with no runtime generation and no drift.

Validation never raises a traceback for bad lesson data: every problem is
reported as "ERROR <where>: <what>" and the build exits non-zero.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ID_RE = re.compile(r"^[a-zA-Z0-9_]+$")
DIRS = {"LR", "RL", "TD", "TB", "BT"}
STYLES = {"solid", "dashed"}
SHAPES = {"box", "decision", "round"}
MODES = {"guided", "atlas"}
SCENE_KINDS = {"overview", "scene", "recap", "memoryStory"}

SCENES_RE = re.compile(r"<!-- SCENES:BEGIN.*?<!-- SCENES:END -->", re.S)
ATLAS_RE = re.compile(r"<!-- ATLAS:BEGIN.*?<!-- ATLAS:END -->", re.S)
DATA_RE = re.compile(
    r'(<script type="application/json" id="lesson-data">\n)(.*?)(\n</script>)', re.S
)
STATE_RE = re.compile(r"<script>/\* LESSON_STATE[^<]*?</script>", re.S)
TITLE_RE = re.compile(r"<title>.*?</title>", re.S)


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def mlabel(text):
    """Escape a label for a quoted Mermaid string embedded in HTML <pre> text.

    Escapes HTML-sensitive characters (so labels cannot break out of the
    <pre> or inject markup), swaps double quotes for single (Mermaid quoted
    strings cannot contain them), and flattens newlines to spaces.
    """
    s = str(text)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = s.replace('"', "'")
    s = re.sub(r"\s*\n\s*", " ", s)
    return s


def json_for_script(data):
    """Serialize JSON safe for embedding in a <script> block."""
    return json.dumps(data, indent=1, ensure_ascii=False).replace("</", "<\\/")


def derived_edge_id(edge, index):
    """Best-effort edge identifier for diagnostics; never raises."""
    if not isinstance(edge, dict):
        return f"<edge {index}>"
    if edge.get("id"):
        return str(edge["id"])
    src, dst = edge.get("from"), edge.get("to")
    if src and dst:
        return f"{src}__{dst}"
    return f"<edge {index}>"


def as_cluster_list(clusters, where, errors):
    """Accept {label: [ids]} or [{id?, label, nodes}]; return a normalized list."""
    out = []
    if clusters is None:
        return out
    if isinstance(clusters, dict):
        for label, ids in clusters.items():
            if not isinstance(ids, list):
                errors.append(f"{where}: cluster {label!r} members must be a list")
                continue
            out.append({"id": None, "label": str(label), "nodes": ids})
        return out
    if isinstance(clusters, list):
        for i, c in enumerate(clusters):
            if not isinstance(c, dict) or not isinstance(c.get("nodes"), list):
                errors.append(f"{where}: cluster #{i} must be an object with a nodes list")
                continue
            out.append({"id": c.get("id"), "label": str(c.get("label") or c.get("id") or f"cluster{i}"),
                        "nodes": c["nodes"]})
        return out
    errors.append(f"{where}: clusters must be an object or a list")
    return out


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate(data):
    """Return (errors, warnings). Never raises on malformed data."""
    errors, warnings = [], []

    if not isinstance(data, dict):
        return ["lesson data must be a JSON object"], []

    meta = data.get("meta")
    if not isinstance(meta, dict) or not meta.get("title"):
        errors.append("meta: required object with at least a title")

    graph = data.get("graph")
    if not isinstance(graph, dict):
        errors.append("graph: required object with nodes and edges")
        graph = {}
    nodes = graph.get("nodes")
    if not isinstance(nodes, dict):
        errors.append("graph.nodes: required object")
        nodes = {}
    edges = graph.get("edges")
    if edges is None:
        edges = []
    if not isinstance(edges, list):
        errors.append("graph.edges: must be a list")
        edges = []

    groups = graph.get("groups") or {}
    if not isinstance(groups, dict):
        errors.append("graph.groups: must be an object")
        groups = {}

    for nid, n in nodes.items():
        if not ID_RE.match(str(nid)):
            errors.append(f"graph.nodes: id not [a-zA-Z0-9_]+: {nid!r}")
        if not isinstance(n, dict):
            errors.append(f"graph.nodes.{nid}: must be an object")
            continue
        if n.get("shape") is not None and n["shape"] not in SHAPES:
            errors.append(f"graph.nodes.{nid}: shape must be one of {sorted(SHAPES)}")
        if n.get("group") is not None and n["group"] not in groups:
            warnings.append(f"graph.nodes.{nid}: group {n['group']!r} not in graph.groups")
        for rid in n.get("related") or []:
            if rid not in nodes:
                errors.append(f"graph.nodes.{nid}: related id {rid!r} unknown")
        for j, s in enumerate(n.get("src") or []):
            if not isinstance(s, dict):
                errors.append(f"graph.nodes.{nid}: src[{j}] must be an object")
                continue
            if s.get("url"):
                if not re.match(r"^https?://", str(s["url"])):
                    errors.append(f"graph.nodes.{nid}: src[{j}].url must be http(s)")
            elif not s.get("path"):
                errors.append(f"graph.nodes.{nid}: src[{j}] needs a path or a url")
            if s.get("endLine") is not None and s.get("line") is None:
                errors.append(f"graph.nodes.{nid}: src[{j}].endLine requires line")

    edge_ids = set()
    valid_edges = {}
    for i, e in enumerate(edges):
        eid = derived_edge_id(e, i)
        if not isinstance(e, dict):
            errors.append(f"graph.edges[{i}]: must be an object")
            continue
        ok = True
        for end in ("from", "to"):
            v = e.get(end)
            if not v:
                errors.append(f"graph.edges {eid}: missing {end!r}")
                ok = False
            elif v not in nodes:
                errors.append(f"graph.edges {eid}: {end} references unknown node {v!r}")
                ok = False
        if e.get("style") is not None and e["style"] not in STYLES:
            errors.append(f"graph.edges {eid}: style must be one of {sorted(STYLES)}")
        if eid in edge_ids:
            errors.append(f"graph.edges: duplicate edge id {eid!r} "
                          "(give parallel edges explicit distinct ids)")
        edge_ids.add(eid)
        if ok:
            valid_edges[eid] = e

    def check_view(v, where, allow_big):
        """Shared checks for scenes and atlas levels (both are graph views)."""
        if v.get("syntax") is not None:
            if not isinstance(v["syntax"], str) or not v["syntax"].strip():
                errors.append(f"{where}: syntax must be a non-empty string")
            for k in ("nodes", "edges", "clusters", "relabel"):
                if v.get(k):
                    warnings.append(f"{where}: {k} is ignored when syntax is present")
            return
        cast = v.get("nodes")
        if not isinstance(cast, list) or not cast:
            errors.append(f"{where}: nodes list required (or a raw syntax block)")
            return
        if len(cast) != len(set(cast)):
            errors.append(f"{where}: duplicate node in cast")
        hi = 30 if allow_big else 9
        if not 2 <= len(cast) <= hi:
            errors.append(f"{where}: {len(cast)} nodes (hard bounds 2-{hi})")
        elif not allow_big and not 3 <= len(cast) <= 7:
            warnings.append(f"{where}: {len(cast)} nodes (teaching sweet spot is 3-7)")
        cast_set = set(cast)
        for nid in cast:
            if nid not in nodes:
                errors.append(f"{where}: unknown node {nid!r}")
        for f in v.get("focus") or []:
            if f not in cast_set:
                errors.append(f"{where}: focus {f!r} not in nodes")
        if v.get("focus") is not None and not isinstance(v["focus"], list):
            errors.append(f"{where}: focus must be a list")
        if v.get("edges") is not None:
            for eid in v["edges"]:
                e = valid_edges.get(eid)
                if e is None:
                    errors.append(f"{where}: unknown edge id {eid!r}")
                elif e["from"] not in cast_set or e["to"] not in cast_set:
                    errors.append(f"{where}: edge {eid!r} has an endpoint outside nodes")
        seen_in_cluster = set()
        for c in as_cluster_list(v.get("clusters"), where, errors):
            for nid in c["nodes"]:
                if nid not in cast_set:
                    errors.append(f"{where}: cluster {c['label']!r} member {nid!r} not in nodes")
                if nid in seen_in_cluster:
                    errors.append(f"{where}: node {nid!r} appears in more than one cluster")
                seen_in_cluster.add(nid)
        for rid in (v.get("relabel") or {}):
            if rid not in cast_set:
                errors.append(f"{where}: relabel key {rid!r} not in nodes")
        if v.get("dir") is not None and v["dir"] not in DIRS:
            errors.append(f"{where}: dir must be one of {sorted(DIRS)}")

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        errors.append("scenes: required non-empty list")
        scenes = []
    scene_ids = set()
    for i, sc in enumerate(scenes):
        if not isinstance(sc, dict):
            errors.append(f"scenes[{i}]: must be an object")
            continue
        sid = sc.get("id") or f"<scene {i}>"
        where = f"scene {sid}"
        if not sc.get("id") or not ID_RE.match(str(sc["id"])):
            errors.append(f"{where}: id required, [a-zA-Z0-9_]+")
        if sid in scene_ids:
            errors.append(f"scenes: duplicate id {sid!r}")
        scene_ids.add(sid)
        if not sc.get("title"):
            errors.append(f"{where}: title required")
        if sc.get("kind") is not None and sc["kind"] not in SCENE_KINDS:
            errors.append(f"{where}: kind must be one of {sorted(SCENE_KINDS)}")

        if sc.get("kind") == "memoryStory":
            snodes = sc.get("storyNodes")
            if not isinstance(snodes, dict) or not snodes:
                errors.append(f"{where}: storyNodes object required")
                snodes = {}
            for nid in snodes:
                if not ID_RE.match(str(nid)):
                    errors.append(f"{where}: story node id not [a-zA-Z0-9_]+: {nid!r}")
            for j, e in enumerate(sc.get("storyEdges") or []):
                eid = derived_edge_id(e, j)
                if not isinstance(e, dict):
                    errors.append(f"{where}: storyEdges[{j}] must be an object")
                    continue
                for end in ("from", "to"):
                    if not e.get(end):
                        errors.append(f"{where}: story edge {eid} missing {end!r}")
                    elif e[end] not in snodes:
                        errors.append(f"{where}: story edge {eid} references unknown story node {e.get(end)!r}")
            lit = sc.get("literalScene")
            if lit and lit not in {s.get("id") for s in scenes if isinstance(s, dict)}:
                errors.append(f"{where}: literalScene {lit!r} is not a scene id")
            mappings = sc.get("mapping") or []
            strict = any(isinstance(m, dict) and m.get("storyNode") for m in mappings)
            mapped = set()
            for j, m in enumerate(mappings):
                if not isinstance(m, dict) or "story" not in m or "technical" not in m:
                    errors.append(f"{where}: mapping[{j}] needs story and technical text")
                    continue
                if m.get("storyNode"):
                    if m["storyNode"] not in snodes:
                        errors.append(f"{where}: mapping[{j}].storyNode {m['storyNode']!r} unknown")
                    if m["storyNode"] in mapped:
                        errors.append(f"{where}: duplicate mapping for story node {m['storyNode']!r}")
                    mapped.add(m["storyNode"])
                for t in m.get("technicalNodes") or []:
                    if t not in nodes:
                        errors.append(f"{where}: mapping[{j}].technicalNodes id {t!r} unknown")
                for t in m.get("technicalEdges") or []:
                    if t not in edge_ids:
                        errors.append(f"{where}: mapping[{j}].technicalEdges id {t!r} unknown")
            if strict:
                unmapped = [nid for nid in snodes if nid not in mapped]
                if unmapped:
                    errors.append(f"{where}: story nodes without a mapping: {unmapped} "
                                  "(every story element must map to something real)")
            elif mappings:
                warnings.append(f"{where}: mapping uses free text only; add storyNode/"
                                "technicalNodes ids to make 1:1 completeness checkable")
            for j, q in enumerate(sc.get("recallQuestions") or []):
                if isinstance(q, str):
                    continue
                if not isinstance(q, dict) or not q.get("prompt"):
                    errors.append(f"{where}: recallQuestions[{j}] must be a string or "
                                  "an object with a prompt")
                    continue
                for r in q.get("refs") or []:
                    if r not in nodes:
                        errors.append(f"{where}: recallQuestions[{j}].refs id {r!r} unknown")
        else:
            check_view(sc, where, allow_big=False)

    levels = data.get("levels")
    if levels is None:
        levels = []
    if not isinstance(levels, list):
        errors.append("levels: must be a list")
        levels = []
    level_ids = set()
    for i, lv in enumerate(levels):
        if not isinstance(lv, dict):
            errors.append(f"levels[{i}]: must be an object")
            continue
        lid = lv.get("id") or f"<level {i}>"
        where = f"level {lid}"
        if not lv.get("id") or not ID_RE.match(str(lv["id"])):
            errors.append(f"{where}: id required, [a-zA-Z0-9_]+")
        if lid in level_ids:
            errors.append(f"levels: duplicate id {lid!r}")
        level_ids.add(lid)
        if not lv.get("title"):
            errors.append(f"{where}: title required")
        check_view(lv, where, allow_big=True)

    state = data.get("initialState")
    if state is not None:
        if not isinstance(state, dict):
            errors.append("initialState: must be an object")
        else:
            if not isinstance(state.get("revision"), int):
                errors.append("initialState.revision: required integer")
            if state.get("mode") is not None and state["mode"] not in MODES:
                errors.append(f"initialState.mode: must be one of {sorted(MODES)}")
            if state.get("scene") is not None and state["scene"] not in scene_ids:
                errors.append(f"initialState.scene {state['scene']!r} is not a scene id")
            if state.get("level") is not None and state["level"] not in level_ids:
                errors.append(f"initialState.level {state['level']!r} is not a level id")
            for f in state.get("focus") or []:
                if f not in nodes:
                    errors.append(f"initialState.focus id {f!r} unknown")

    return errors, warnings


# --------------------------------------------------------------------------
# materialization
# --------------------------------------------------------------------------

def node_decl(nid, node, relabel=None):
    label = mlabel((relabel or {}).get(nid) or node.get("label") or nid)
    shape = node.get("shape")
    if shape == "decision":
        return f'  {nid}{{"{label}"}}'
    if shape == "round":
        return f'  {nid}(["{label}"])'
    return f'  {nid}["{label}"]'


def edge_decl(e):
    arrow = "-.->" if e.get("style") == "dashed" else "-->"
    if e.get("label"):
        return f'  {e["from"]} {arrow}|"{mlabel(e["label"])}"| {e["to"]}'
    return f'  {e["from"]} {arrow} {e["to"]}'


def view_mermaid(view, graph, story=False):
    """Materialize one declarative view (scene or atlas level) as Mermaid."""
    if view.get("syntax"):
        return view["syntax"].strip("\n")
    if story:
        nodes = view.get("storyNodes") or {}
        edges = view.get("storyEdges") or []
        lines = [f'flowchart {view.get("dir", "LR")}']
        for nid, n in nodes.items():
            lines.append(node_decl(nid, n))
        for e in edges:
            lines.append(edge_decl(e))
        return "\n".join(lines)

    nodes = graph.get("nodes") or {}
    all_edges = graph.get("edges") or []
    cast = view.get("nodes") or []
    cast_set = set(cast)
    if view.get("edges") is not None:
        wanted = set(view["edges"])
        edges = [e for i, e in enumerate(all_edges)
                 if derived_edge_id(e, i) in wanted]
    else:
        edges = [e for e in all_edges
                 if e.get("from") in cast_set and e.get("to") in cast_set]
    relabel = view.get("relabel") or {}
    clusters = as_cluster_list(view.get("clusters"), "", [])
    clustered = {nid for c in clusters for nid in c["nodes"]}
    lines = [f'flowchart {view.get("dir", "LR")}']
    for ci, c in enumerate(clusters):
        cid = c["id"] or f"c{ci}"
        lines.append(f'  subgraph view_{cid} ["{mlabel(c["label"])}"]')
        for nid in c["nodes"]:
            if nid in cast_set:
                lines.append("  " + node_decl(nid, nodes[nid], relabel).strip())
        lines.append("  end")
    for nid in cast:
        if nid not in clustered:
            lines.append(node_decl(nid, nodes[nid], relabel))
    for e in edges:
        lines.append(edge_decl(e))
    return "\n".join(lines)


def section(kind, key, mermaid):
    attr = "data-scene" if kind == "scene" else "data-level"
    return (f'      <section class="diag {kind}" {attr}="{key}">\n'
            f'<pre class="mermaid">\n{mermaid}\n</pre>\n'
            f"      </section>")


def scenes_block(data):
    parts = []
    for sc in data.get("scenes") or []:
        mer = view_mermaid(sc, data.get("graph") or {},
                           story=(sc.get("kind") == "memoryStory"))
        parts.append(section("scene", sc["id"], mer))
    return ("<!-- SCENES:BEGIN generated by build.py from lesson-data; do not hand-edit -->\n"
            + "\n".join(parts) + "\n      <!-- SCENES:END -->")


def atlas_block(data):
    parts = []
    for lv in data.get("levels") or []:
        mer = view_mermaid(lv, data.get("graph") or {})
        parts.append(section("level", lv["id"], mer))
    return ("<!-- ATLAS:BEGIN generated by build.py from lesson-data; do not hand-edit -->\n"
            + "\n".join(parts) + "\n      <!-- ATLAS:END -->")


DEFAULT_STATE = {"mode": "guided", "scene": None, "focus": [], "note": None,
                 "pulse": False, "revision": 1}


def render_html(template_text, data):
    """Full generation: template + title + state + data + scenes + atlas."""
    state = dict(DEFAULT_STATE)
    state.update(data.get("initialState") or {})
    if state["scene"] is None and data.get("scenes"):
        state["scene"] = data["scenes"][0]["id"]
    out, n1 = TITLE_RE.subn(
        lambda _: f'<title>{mlabel(data["meta"]["title"])}</title>', template_text, count=1)
    state_block = ("<script>/* LESSON_STATE — edit this line only */\n"
                   "const LESSON_STATE = " + json.dumps(state, ensure_ascii=False)
                   + ";\n</script>")
    out, n2 = STATE_RE.subn(lambda _: state_block, out, count=1)
    data_block_inner = json_for_script(data)
    out, n3 = DATA_RE.subn(lambda m: m.group(1) + data_block_inner + m.group(3),
                           out, count=1)
    out, n4 = SCENES_RE.subn(lambda _: scenes_block(data), out, count=1)
    out, n5 = ATLAS_RE.subn(lambda _: atlas_block(data), out, count=1)
    if (n1, n2, n3, n4, n5) != (1, 1, 1, 1, 1):
        raise BuildError(f"template is missing a required zone "
                         f"(title/state/data/scenes/atlas = {(n1, n2, n3, n4, n5)})")
    return out


class BuildError(Exception):
    pass


def atomic_write(path, text):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def load_data_from_html(text, path):
    m = DATA_RE.search(text)
    if not m:
        raise BuildError(f"{path}: lesson-data block not found")
    try:
        return json.loads(m.group(2))
    except json.JSONDecodeError as e:
        raise BuildError(f"{path}: lesson-data is not valid JSON: {e}")


def report(path, errors, warnings):
    for w in warnings:
        print(f"  WARNING {w}")
    for e in errors:
        print(f"  ERROR {e}")
    if errors:
        print(f"{path}: {len(errors)} validation error(s); nothing written")
        return False
    return True


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("inputs", nargs="+", help="lesson .html files, or one .json source")
    ap.add_argument("--template", help="template HTML (required for .json input)")
    ap.add_argument("--output", help="output HTML path (required for .json input)")
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if generated blocks are stale; write nothing")
    args = ap.parse_args(argv)

    exit_code = 0
    json_inputs = [p for p in args.inputs if p.endswith(".json")]
    if json_inputs:
        if len(args.inputs) != 1 or not args.template or not args.output:
            print("ERROR: .json input requires exactly one input plus --template and --output")
            return 2
        src = Path(args.inputs[0])
        try:
            data = json.loads(src.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"ERROR {src}: {e}")
            return 2
        errors, warnings = validate(data)
        if not report(src, errors, warnings):
            return 1
        try:
            template_text = Path(args.template).read_text(encoding="utf-8")
            out = render_html(template_text, data)
        except (OSError, BuildError) as e:
            print(f"ERROR {e}")
            return 2
        dest = Path(args.output)
        if args.check:
            current = dest.read_text(encoding="utf-8") if dest.exists() else None
            if current != out:
                print(f"{dest}: STALE (rebuild would change it)")
                return 1
            print(f"{dest}: up to date")
            return 0
        atomic_write(dest, out)
        print(f"{dest}: built from {src} "
              f"({len(data.get('scenes') or [])} scenes, {len(data.get('levels') or [])} levels)")
        mm_src = Path(args.template).parent / "mermaid.min.js"
        mm_dst = dest.parent / "mermaid.min.js"
        if mm_src.exists() and mm_src.resolve() != mm_dst.resolve() and not mm_dst.exists():
            mm_dst.write_bytes(mm_src.read_bytes())
            print(f"{mm_dst}: copied vendored mermaid.min.js beside the output")
        return 0

    for p in args.inputs:
        path = Path(p)
        try:
            text = path.read_text(encoding="utf-8")
            data = load_data_from_html(text, path)
        except (OSError, BuildError) as e:
            print(f"ERROR {e}")
            exit_code = 2
            continue
        errors, warnings = validate(data)
        if not report(path, errors, warnings):
            exit_code = 1
            continue
        try:
            out, n1 = SCENES_RE.subn(lambda _: scenes_block(data), text, count=1)
            out, n2 = ATLAS_RE.subn(lambda _: atlas_block(data), out, count=1)
            if (n1, n2) != (1, 1):
                raise BuildError(f"{path}: SCENES/ATLAS markers not found ({n1},{n2})")
        except BuildError as e:
            print(f"ERROR {e}")
            exit_code = 2
            continue
        if args.check:
            if out != text:
                print(f"{path}: STALE (rebuild would change it)")
                exit_code = max(exit_code, 1)
            else:
                print(f"{path}: up to date")
            continue
        if out != text:
            atomic_write(path, out)
        print(f"{path}: materialized "
              f"{len(data.get('scenes') or [])} scenes, {len(data.get('levels') or [])} levels")
    return exit_code


if __name__ == "__main__":
    sys.exit(run())
