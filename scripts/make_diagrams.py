"""Generate docs/architecture.drawio.svg and docs/workflow.drawio.svg (stdlib only).

Each diagram is defined once (boxes + edges). The script writes an SVG with a white background
whose root `content` attribute holds the uncompressed mxfile XML, so diagrams.net opens it as an
editable diagram and the drawn SVG matches it. Run: uv run python scripts/make_diagrams.py
"""

import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from triage.config import load_models, load_policy_config  # noqa: E402

DOCS = ROOT / "docs"
# Labels follow config, so the diagrams never name a stale model, prompt or policy.
_ROLE = load_models().roles.extractor


def _short(model_id: str) -> str:
    return model_id.split("/")[-1].removesuffix(":free")


MODEL = f"{_short(_ROLE.model)}\nfallback {_short(_ROLE.fallbacks[0])}"
PROMPT = f"prompts/extract/v{_ROLE.prompt_version}.md"
POLICY = f"policy/policy_v{load_policy_config().version}.yaml"
FONT = "Helvetica, Arial, sans-serif"

# kind -> (fill, stroke, dashed)
STYLES = {
    "code": ("#dae8fc", "#6c8ebf", False),
    "model": ("#ffe6cc", "#d79b00", False),
    "service": ("#e1d5e7", "#9673a6", False),
    "store": ("#f5f5f5", "#666666", False),
    "person": ("#d5e8d4", "#82b366", False),
    "fail": ("#f8cecc", "#b85450", False),
    "io": ("#ffffff", "#000000", False),
    "group": ("none", "#999999", True),
}


@dataclass
class Box:
    id: str
    label: str
    x: int
    y: int
    w: int = 200
    h: int = 60
    kind: str = "code"


@dataclass
class Edge:
    src: str
    dst: str
    label: str = ""
    dashed: bool = False
    points: list[tuple[int, int]] = field(default_factory=list)


@dataclass
class Diagram:
    name: str
    width: int
    height: int
    boxes: list[Box]
    edges: list[Edge]


def _center(b: Box) -> tuple[float, float]:
    return b.x + b.w / 2, b.y + b.h / 2


def _clip(b: Box, toward: tuple[float, float]) -> tuple[float, float]:
    """Point where the line from the box centre toward `toward` leaves the box."""
    cx, cy = _center(b)
    dx, dy = toward[0] - cx, toward[1] - cy
    if dx == 0 and dy == 0:
        return cx, cy
    t = min(
        (b.w / 2) / abs(dx) if dx else float("inf"),
        (b.h / 2) / abs(dy) if dy else float("inf"),
    )
    return cx + dx * t, cy + dy * t


def _style(b: Box) -> str:
    fill, stroke, dashed = STYLES[b.kind]
    s = f"rounded=1;whiteSpace=wrap;html=1;fillColor={fill};strokeColor={stroke};"
    if b.kind == "group":
        s += "dashed=1;verticalAlign=top;align=left;spacingLeft=8;fontStyle=1;arcSize=3;"
    if b.kind == "model":
        s += "fontStyle=1;"
    return s


def mxfile(d: Diagram) -> str:
    root = ET.Element("root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")
    for b in d.boxes:
        cell = ET.SubElement(
            root,
            "mxCell",
            id=b.id,
            value=b.label.replace("\n", "<br>"),
            style=_style(b),
            vertex="1",
            parent="1",
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            {"x": str(b.x), "y": str(b.y), "width": str(b.w), "height": str(b.h)},
            **{"as": "geometry"},
        )
    for i, e in enumerate(d.edges):
        style = "endArrow=classic;html=1;rounded=0;" + ("dashed=1;" if e.dashed else "")
        cell = ET.SubElement(
            root,
            "mxCell",
            id=f"e{i}",
            value=e.label,
            style=style,
            edge="1",
            parent="1",
            source=e.src,
            target=e.dst,
        )
        geo = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        if e.points:
            arr = ET.SubElement(geo, "Array", **{"as": "points"})
            for px, py in e.points:
                ET.SubElement(arr, "mxPoint", x=str(px), y=str(py))
    model = ET.Element(
        "mxGraphModel",
        grid="1",
        gridSize="10",
        page="1",
        pageWidth=str(d.width),
        pageHeight=str(d.height),
        background="#ffffff",
    )
    model.append(root)
    mx = ET.Element("mxfile", host="drawio", type="device")
    diagram = ET.SubElement(mx, "diagram", id=d.name.lower(), name=d.name)
    diagram.append(model)
    return ET.tostring(mx, encoding="unicode")


def _text(parent: ET.Element, lines: list[str], x: float, y: float, **attrs: str) -> None:
    t = ET.SubElement(parent, "text", x=f"{x:.0f}", y=f"{y:.0f}", **attrs)
    for i, line in enumerate(lines):
        span = ET.SubElement(t, "tspan", x=f"{x:.0f}", dy="0" if i == 0 else "15")
        span.text = line


def svg(d: Diagram) -> str:
    s = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        version="1.1",
        width=str(d.width),
        height=str(d.height),
        viewBox=f"0 0 {d.width} {d.height}",
        content=mxfile(d),
        style="background-color: #ffffff;",
    )
    defs = ET.SubElement(s, "defs")
    marker = ET.SubElement(
        defs,
        "marker",
        id="arrow",
        viewBox="0 0 10 10",
        refX="10",
        refY="5",
        markerWidth="8",
        markerHeight="8",
        orient="auto",
    )
    ET.SubElement(marker, "path", d="M0,0 L10,5 L0,10 z", fill="#333333")
    ET.SubElement(s, "rect", width="100%", height="100%", fill="#ffffff")
    by_id = {b.id: b for b in d.boxes}
    for b in d.boxes:
        fill, stroke, dashed = STYLES[b.kind]
        rect = {"x": str(b.x), "y": str(b.y), "width": str(b.w), "height": str(b.h)}
        rect |= {"rx": "8", "fill": fill, "stroke": stroke, "stroke-width": "1.5"}
        if dashed:
            rect["stroke-dasharray"] = "6 4"
        ET.SubElement(s, "rect", rect)
        lines = b.label.split("\n")
        weight = "bold" if b.kind in ("model", "group") else "normal"
        common = {"font-family": FONT, "font-size": "13", "font-weight": weight}
        if b.kind == "group":
            _text(s, lines, b.x + 10, b.y + 18, **common)
        else:
            top = b.y + b.h / 2 - (len(lines) - 1) * 7.5 + 4.5
            _text(s, lines, b.x + b.w / 2, top, **common, **{"text-anchor": "middle"})
    for e in d.edges:
        a, z = by_id[e.src], by_id[e.dst]
        mids = [(float(px), float(py)) for px, py in e.points]
        start = _clip(a, mids[0] if mids else _center(z))
        end = _clip(z, mids[-1] if mids else _center(a))
        pts = [start, *mids, end]
        line = {
            "points": " ".join(f"{x:.1f},{y:.1f}" for x, y in pts),
            "fill": "none",
            "stroke": "#333333",
            "stroke-width": "1.5",
            "marker-end": "url(#arrow)",
        }
        if e.dashed:
            line["stroke-dasharray"] = "5 4"
        ET.SubElement(s, "polyline", line)
        if e.label:
            i = len(pts) // 2
            (x1, y1), (x2, y2) = pts[i - 1], pts[i]
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            w = 7 * len(e.label) + 8
            ET.SubElement(
                s,
                "rect",
                x=f"{mx - w / 2:.0f}",
                y=f"{my - 10:.0f}",
                width=str(w),
                height="18",
                fill="#ffffff",
            )
            _text(
                s,
                [e.label],
                mx,
                my + 4,
                **{"font-family": FONT, "font-size": "11", "text-anchor": "middle"},
            )
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(s, encoding="unicode")


ARCHITECTURE = Diagram(
    name="Architecture",
    width=1340,
    height=700,
    boxes=[
        Box("pipe", "triage/ pipeline (Python, runs locally)", 20, 120, 1040, 300, "group"),
        Box("web", "Local showcase (one process, 127.0.0.1:8000)", 20, 560, 560, 120, "group"),
        Box("in", "WhatsApp .txt export\n(synthetic chat)", 40, 20, kind="io"),
        Box("cache", "diskcache\n.cache/ (LLM responses)", 300, 20, kind="store"),
        Box(
            "llm",
            f"OpenRouter :free LLM\n{MODEL}",
            560,
            20,
            220,
            kind="model",
        ),
        Box("lf", "Langfuse Cloud (free)\ntraces · latency · tokens", 820, 20, kind="service"),
        Box("parse", "parse\nchat-miner → m001…", 40, 160),
        Box("render", "render\nS1…Sn handles, no phones", 300, 160),
        Box(
            "extract",
            f"extract (LLM, Instructor)\n{PROMPT}",
            560,
            160,
            220,
            kind="model",
        ),
        Box("ground", "ground\ndrop invalid message IDs", 820, 160),
        Box("identity", "identity\nphonenumbers + rapidfuzz", 820, 320),
        Box("policy", "policy\nrule-engine, most cautious wins", 560, 320, 220),
        Box("route", "route\nsimulated actions only", 300, 320),
        Box(
            "runs",
            "runs/*.jsonl (append-only)\nactions · approvals · handoffs · alerts",
            220,
            460,
            280,
            kind="store",
        ),
        Box("pol", f"{POLICY}\nrules R1–R10 + intents", 560, 460, 220, kind="store"),
        Box("roster", "data/world/roster.yaml\ncontacts · roles · outlets", 820, 460, kind="store"),
        Box("api", "FastAPI  /api/triage\n(uvicorn)", 40, 600, kind="code"),
        Box(
            "site",
            "static site/  (HTML, GSAP + Lenis CDN)\nprecomputed site/data/*.json",
            300,
            600,
            260,
            kind="io",
        ),
        Box("eval", "eval/run_eval.py\nmetrics → eval/results/<tag>/", 1100, 160, 220),
        Box(
            "data",
            "data/ dev (15 chats) + gold\n· challenge (frozen, human-written)",
            1100,
            320,
            220,
            kind="store",
        ),
        Box(
            "person", "Support agent / approver\n(reads queues, approves)", 820, 600, kind="person"
        ),
        Box("lg_title", "Legend", 1100, 460, 220, 30, "io"),
        Box("lg_model", "LLM step / model", 1100, 496, 220, 26, "model"),
        Box("lg_code", "plain code", 1100, 528, 220, 26, "code"),
        Box("lg_store", "file / log / cache", 1100, 560, 220, 26, "store"),
        Box("lg_service", "external free service", 1100, 592, 220, 26, "service"),
        Box("lg_person", "person", 1100, 624, 220, 26, "person"),
    ],
    edges=[
        Edge("in", "parse"),
        Edge("parse", "render"),
        Edge("render", "extract"),
        Edge("extract", "llm", "1 call / chat"),
        Edge("extract", "cache", "cache", dashed=True),
        Edge("extract", "lf", "trace", dashed=True),
        Edge("extract", "ground"),
        Edge("ground", "identity"),
        Edge("identity", "policy"),
        Edge("policy", "route", "grade"),
        Edge("route", "runs"),
        Edge("pol", "policy"),
        Edge("roster", "identity"),
        Edge("site", "api", "POST"),
        Edge("api", "parse", "runs pipeline"),
        Edge("data", "eval"),
        Edge("eval", "ground"),
        Edge("runs", "person", "queues", points=[(360, 540), (920, 540)]),
    ],
)

WORKFLOW = Diagram(
    name="Workflow",
    width=1000,
    height=900,
    boxes=[
        Box("in", "Chat export (.txt)", 260, 20, 240, 50, "io"),
        Box("parse", "Parse + render\n(IDs m001…, sender handles)", 260, 100, 240, 56),
        Box(
            "extract",
            "Extract requests, evidence IDs,\nreferences, entities, flags",
            260,
            186,
            240,
            56,
            "model",
        ),
        Box("fail", "Schema fails twice,\n429 or any error", 640, 186, 220, 56, "fail"),
        Box(
            "unproc",
            'Run marked UNPROCESSED\nwhole chat → team queue\n(never "no requests")',
            640,
            300,
            220,
            64,
            "fail",
        ),
        Box("ground", "Ground: drop candidates\nwith unknown message IDs", 260, 272, 240, 56),
        Box("rej", "Logged as\nrejected hallucination", 20, 272, 190, 56, "store"),
        Box(
            "ident", "Identity from roster:\nCONFIRMED / AMBIGUOUS / UNCONFIRMED", 230, 358, 300, 56
        ),
        Box(
            "policy",
            "Policy: evaluate every rule,\nmost cautious grade wins, cite rule",
            230,
            444,
            300,
            56,
        ),
        Box("act", "act\nsimulated action →\nruns/actions.jsonl", 20, 560, 200, 70),
        Box("seek", "seek_approval\n→ runs/approvals.jsonl", 260, 560, 200, 70),
        Box("hand", "hand_off\n→ runs/handoffs.jsonl", 500, 560, 200, 70),
        Box(
            "refuse",
            "refuse\nrefusal + security alert\n→ runs/alerts.jsonl",
            740,
            560,
            200,
            70,
            "fail",
        ),
        Box("approver", "Approver (person)\napprove or reject", 260, 680, 200, 56, "person"),
        Box("team", "Team queue (person)\ntakes over", 500, 680, 200, 56, "person"),
        Box("rejected", "Rejected: logged,\nnothing done", 260, 790, 200, 50, "store"),
        Box("lg_title", "Legend", 760, 680, 180, 30, "io"),
        Box("lg_model", "model decides (describes)", 760, 716, 180, 26, "model"),
        Box("lg_code", "plain code decides", 760, 748, 180, 26, "code"),
        Box("lg_person", "a person decides", 760, 780, 180, 26, "person"),
        Box("lg_fail", "failure / refusal path", 760, 812, 180, 26, "fail"),
    ],
    edges=[
        Edge("in", "parse"),
        Edge("parse", "extract"),
        Edge("extract", "fail", "on failure", dashed=True),
        Edge("fail", "unproc"),
        Edge("unproc", "team", points=[(720, 400), (720, 708)]),
        Edge("extract", "ground", "valid output"),
        Edge("ground", "rej", "invalid"),
        Edge("ground", "ident"),
        Edge("ident", "policy"),
        Edge("policy", "act", points=[(380, 525), (120, 525)]),
        Edge("policy", "seek", points=[(380, 525), (360, 525)]),
        Edge("policy", "hand", points=[(380, 525), (600, 525)]),
        Edge("policy", "refuse", points=[(380, 525), (840, 525)]),
        Edge("seek", "approver"),
        Edge("approver", "act", "approve", points=[(120, 708)]),
        Edge("approver", "rejected", "reject"),
        Edge("hand", "team"),
    ],
)


def main() -> None:
    for d, name in ((ARCHITECTURE, "architecture"), (WORKFLOW, "workflow")):
        out = DOCS / f"{name}.drawio.svg"
        out.write_text(svg(d), encoding="utf-8")
        print(f"wrote {out.relative_to(DOCS.parent)}")


if __name__ == "__main__":
    main()
