#!/usr/bin/env python3
"""Hard-gate common SVG and editable-PPTX diagram regressions."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

P_NS = "http://schemas.openxmlformats.org/presentationml/2006/main"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
NS = {"p": P_NS, "a": A_NS}
LOCK_RE = re.compile(
    r'\b(?:noGrp|noUngrp|noSelect|noMove|noResize|noRot|noTextEdit|noEditPoints)="1"'
)
FONT_SIZE_RE = re.compile(r"font-size\s*(?:=|:)\s*[\"']?([0-9]+(?:\.[0-9]+)?)")
FONT_FAMILY_RE = re.compile(r"font-family\s*(?:=|:)\s*[\"']?([^;\"']+)")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--svg", type=Path)
    parser.add_argument("--pptx", type=Path)
    parser.add_argument("--require-font")
    parser.add_argument("--require-group", action="append", default=[])
    parser.add_argument(
        "--same-font",
        action="append",
        default=[],
        help="Comma-separated PowerPoint shape names that must share one font-size set.",
    )
    parser.add_argument(
        "--same-font-regex",
        action="append",
        default=[],
        help="Regex selecting PowerPoint shapes that must share one font-size set.",
    )
    parser.add_argument(
        "--no-autofit",
        action="append",
        default=[],
        help="Regex selecting PowerPoint shapes that must not use normAutofit/shrinkText.",
    )
    parser.add_argument("--allow-pictures", action="store_true")
    args = parser.parse_args()
    if not args.svg and not args.pptx:
        parser.error("provide --svg, --pptx, or both")
    return args


def primary_font(value: str) -> str:
    return value.split(",", 1)[0].strip().strip("'\"")


def validate_svg(
    path: Path, required_font: str | None, errors: list[str], summary: dict[str, object]
) -> None:
    text = path.read_text(encoding="utf-8")
    root = ET.fromstring(text)
    if "viewBox" not in root.attrib:
        errors.append("SVG has no viewBox")
    tags = [element.tag.rsplit("}", 1)[-1] for element in root.iter()]
    if "foreignObject" in tags:
        errors.append("SVG contains foreignObject")
    if "image" in tags:
        errors.append("SVG contains a raster/image element")
    ids = [element.attrib["id"] for element in root.iter() if "id" in element.attrib]
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in ids:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        errors.append(f"SVG duplicate ids: {sorted(duplicates)}")
    sizes = [float(value) for value in FONT_SIZE_RE.findall(text)]
    fractional = sorted({value for value in sizes if not value.is_integer()})
    if fractional:
        errors.append(f"SVG fractional font sizes: {fractional}")
    families = [primary_font(value) for value in FONT_FAMILY_RE.findall(text)]
    if required_font:
        if not families:
            errors.append("SVG has no explicit font-family declaration")
        wrong = sorted({value for value in families if value != required_font})
        if wrong:
            errors.append(f"SVG primary fonts are not {required_font}: {wrong}")
    summary["svg"] = {
        "path": str(path),
        "ids": len(ids),
        "font_sizes": sorted(set(sizes)),
        "primary_fonts": sorted(set(families)),
        "raster_elements": tags.count("image"),
    }


def shape_name(shape: ET.Element) -> str:
    node = shape.find("./p:nvSpPr/p:cNvPr", NS)
    return node.get("name", "") if node is not None else ""


def shape_font_sizes(shape: ET.Element) -> tuple[int, ...]:
    sizes: set[int] = set()
    for element in shape.iter():
        if element.tag.rsplit("}", 1)[-1] in {"rPr", "defRPr", "endParaRPr"}:
            raw = element.get("sz")
            if raw is not None:
                sizes.add(int(raw))
    return tuple(sorted(sizes))


def validate_same_font(
    label: str, names: list[str], fonts: dict[str, tuple[int, ...]], errors: list[str]
) -> None:
    missing = [name for name in names if name not in fonts]
    if missing:
        errors.append(f"{label} missing shapes: {missing}")
        return
    values = {fonts[name] for name in names}
    if len(values) != 1:
        detail = {name: [value / 100 for value in fonts[name]] for name in names}
        errors.append(f"{label} font-size mismatch: {detail}")


def validate_pptx(
    path: Path, args: argparse.Namespace, errors: list[str], summary: dict[str, object]
) -> None:
    with zipfile.ZipFile(path) as archive:
        broken = archive.testzip()
        if broken:
            errors.append(f"PPTX zip member is corrupt: {broken}")
        slide_names = sorted(
            name
            for name in archive.namelist()
            if re.fullmatch(r"ppt/slides/slide[0-9]+\.xml", name)
        )
        xml_texts = {
            name: archive.read(name).decode("utf-8", "ignore") for name in slide_names
        }
        all_xml = "".join(
            archive.read(name).decode("utf-8", "ignore")
            for name in archive.namelist()
            if name.endswith(".xml")
        )

    slide_xml = "".join(xml_texts.values())
    locks = LOCK_RE.findall(slide_xml)
    if locks:
        errors.append(f"PPTX contains {len(locks)} editing locks")
    pictures = sum(len(re.findall(r"<p:pic\b", xml)) for xml in xml_texts.values())
    if pictures and not args.allow_pictures:
        errors.append(f"PPTX contains {pictures} picture objects")

    explicit_sizes = [int(value) for value in re.findall(r"\bsz=\"([0-9]+)\"", all_xml)]
    fractional = sorted({value for value in explicit_sizes if value % 100})
    if fractional:
        errors.append(
            "PPTX fractional point sizes (hundredths of pt): " + str(fractional)
        )

    fonts: dict[str, tuple[int, ...]] = {}
    autofit: dict[str, bool] = {}
    groups: set[str] = set()
    slide_typefaces: set[str] = set()
    for xml in xml_texts.values():
        root = ET.fromstring(xml)
        slide_typefaces.update(re.findall(r'\btypeface="([^"]+)"', xml))
        for group in root.findall(".//p:grpSp", NS):
            node = group.find("./p:nvGrpSpPr/p:cNvPr", NS)
            if node is not None:
                groups.add(node.get("name", ""))
        for shape in root.findall(".//p:sp", NS):
            name = shape_name(shape)
            if not name:
                continue
            fonts[name] = shape_font_sizes(shape)
            autofit[name] = shape.find(".//a:normAutofit", NS) is not None

    if args.require_font:
        explicit = {font for font in slide_typefaces if font and not font.startswith("+")}
        if args.require_font not in explicit:
            errors.append(f"PPTX has no explicit {args.require_font} typeface")
        wrong = sorted(explicit - {args.require_font})
        if wrong:
            errors.append(f"PPTX explicit fonts are not {args.require_font}: {wrong}")
    for required in args.require_group:
        if required not in groups:
            errors.append(f"PPTX missing native group: {required}")
    for value in args.same_font:
        names = [name.strip() for name in value.split(",") if name.strip()]
        validate_same_font(f"same-font({value})", names, fonts, errors)
    for pattern in args.same_font_regex:
        regex = re.compile(pattern)
        names = sorted(name for name in fonts if regex.search(name))
        if len(names) < 2:
            errors.append(f"same-font-regex({pattern}) matched fewer than two shapes")
        else:
            validate_same_font(f"same-font-regex({pattern})", names, fonts, errors)
    for pattern in args.no_autofit:
        regex = re.compile(pattern)
        names = sorted(name for name in autofit if regex.search(name))
        if not names:
            errors.append(f"no-autofit({pattern}) matched no shapes")
        for name in names:
            if autofit[name]:
                errors.append(f"PPTX shape uses normAutofit/shrinkText: {name}")

    summary["pptx"] = {
        "path": str(path),
        "slides": len(slide_names),
        "pictures": pictures,
        "editing_locks": len(locks),
        "groups": sorted(groups),
        "font_sizes_pt": sorted({value / 100 for value in explicit_sizes}),
        "explicit_typefaces": sorted(slide_typefaces),
    }


def main() -> int:
    args = parse_args()
    errors: list[str] = []
    summary: dict[str, object] = {}
    try:
        if args.svg:
            validate_svg(args.svg.resolve(), args.require_font, errors, summary)
        if args.pptx:
            validate_pptx(args.pptx.resolve(), args, errors, summary)
    except (OSError, ET.ParseError, zipfile.BadZipFile) as exc:
        errors.append(str(exc))
    summary["status"] = "fail" if errors else "pass"
    summary["errors"] = errors
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
