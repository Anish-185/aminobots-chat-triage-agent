"""The .drawio.svg files are valid SVG, embed an editable mxfile, and match the generator."""

import importlib.util
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SVG_NS = "{http://www.w3.org/2000/svg}"

spec = importlib.util.spec_from_file_location("make_diagrams", ROOT / "scripts/make_diagrams.py")
make_diagrams = importlib.util.module_from_spec(spec)
spec.loader.exec_module(make_diagrams)

DIAGRAMS = {"architecture": make_diagrams.ARCHITECTURE, "workflow": make_diagrams.WORKFLOW}


@pytest.mark.parametrize("name", DIAGRAMS)
def test_drawio_svg_is_valid_and_editable(name: str):
    path = ROOT / "docs" / f"{name}.drawio.svg"
    svg = ET.parse(path).getroot()  # noqa: S314 - our own generated file, not untrusted input
    assert svg.tag == f"{SVG_NS}svg"
    assert "#ffffff" in svg.get("style", "")
    background = svg.find(f"{SVG_NS}rect")
    assert background is not None and background.get("fill") == "#ffffff"

    mx = ET.fromstring(svg.get("content"))  # noqa: S314 - same file
    assert mx.tag == "mxfile"
    model = mx.find("diagram/mxGraphModel")
    assert model is not None and model.get("background") == "#ffffff"
    cells = model.findall("root/mxCell")
    vertices = {c.get("id") for c in cells if c.get("vertex") == "1"}
    edges = [c for c in cells if c.get("edge") == "1"]
    assert vertices == {b.id for b in DIAGRAMS[name].boxes}
    assert all(e.get("source") in vertices and e.get("target") in vertices for e in edges)
    # drawn SVG matches the XML: one drawn rect per vertex (+ background, + edge labels)
    labelled = sum(1 for e in DIAGRAMS[name].edges if e.label)
    assert len(svg.findall(f"{SVG_NS}rect")) == 1 + len(vertices) + labelled
    assert len(svg.findall(f"{SVG_NS}polyline")) == len(edges)


@pytest.mark.parametrize("name", DIAGRAMS)
def test_committed_svg_matches_generator(name: str):
    committed = (ROOT / "docs" / f"{name}.drawio.svg").read_text(encoding="utf-8")
    assert committed == make_diagrams.svg(DIAGRAMS[name]), "run scripts/make_diagrams.py"
