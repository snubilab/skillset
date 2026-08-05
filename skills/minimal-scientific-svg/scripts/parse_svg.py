#!/usr/bin/env python3
"""Parse the editable SVG subset used by minimal-scientific-svg."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


NUMBER = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
PRESENTATION_ATTRS = {
    "fill",
    "stroke",
    "stroke-width",
    "stroke-dasharray",
    "font-family",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "opacity",
}


def tag_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def number(value: str | None, default: float = 0.0) -> float:
    if value is None:
        return default
    match = re.search(NUMBER, str(value))
    return float(match.group(0)) if match else default


def declarations(raw: str | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for part in (raw or "").split(";"):
        if ":" not in part:
            continue
        key, value = part.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def expand_font(style: dict[str, str]) -> dict[str, str]:
    shorthand = style.pop("font", None)
    if not shorthand:
        return style
    size_match = re.search(rf"({NUMBER})px", shorthand)
    if not size_match:
        return style
    prefix = shorthand[: size_match.start()]
    suffix = shorthand[size_match.end() :].strip()
    style.setdefault("font-size", f"{size_match.group(1)}px")
    if re.search(r"\b(?:bold|[6-9]00)\b", prefix):
        style.setdefault("font-weight", "700")
    if "italic" in prefix:
        style.setdefault("font-style", "italic")
    if suffix:
        style.setdefault("font-family", suffix)
    return style


def parse_css(root: ET.Element) -> dict[str, dict[str, str]]:
    classes: dict[str, dict[str, str]] = {}
    for elem in root.iter():
        if tag_name(elem.tag) != "style":
            continue
        css = "".join(elem.itertext())
        for match in re.finditer(r"([^{}]+)\{([^{}]*)\}", css):
            style = expand_font(declarations(match.group(2)))
            for selector in match.group(1).split(","):
                selector = selector.strip()
                if selector.startswith(".") and re.fullmatch(r"\.[\w-]+", selector):
                    classes[selector[1:]] = style.copy()
    return classes


def multiply(left: tuple[float, ...], right: tuple[float, ...]) -> tuple[float, ...]:
    a, b, c, d, e, f = left
    g, h, i, j, k, l = right
    return (
        a * g + c * h,
        b * g + d * h,
        a * i + c * j,
        b * i + d * j,
        a * k + c * l + e,
        b * k + d * l + f,
    )


def transform_matrix(raw: str | None) -> tuple[float, ...]:
    matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    for name, args_raw in re.findall(r"([A-Za-z]+)\s*\(([^)]*)\)", raw or ""):
        args = [float(value) for value in re.findall(NUMBER, args_raw)]
        if name == "translate":
            tx, ty = args[0], args[1] if len(args) > 1 else 0.0
            current = (1.0, 0.0, 0.0, 1.0, tx, ty)
        elif name == "scale":
            sx, sy = args[0], args[1] if len(args) > 1 else args[0]
            current = (sx, 0.0, 0.0, sy, 0.0, 0.0)
        elif name == "rotate":
            angle = math.radians(args[0])
            rotation = (math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0.0, 0.0)
            if len(args) >= 3:
                cx, cy = args[1], args[2]
                current = multiply(
                    multiply((1.0, 0.0, 0.0, 1.0, cx, cy), rotation),
                    (1.0, 0.0, 0.0, 1.0, -cx, -cy),
                )
            else:
                current = rotation
        elif name == "matrix" and len(args) == 6:
            current = tuple(args)
        else:
            raise ValueError(f"Unsupported transform: {name}")
        matrix = multiply(matrix, current)
    return matrix


def point(matrix: tuple[float, ...], x: float, y: float) -> tuple[float, float]:
    a, b, c, d, e, f = matrix
    return a * x + c * y + e, b * x + d * y + f


def matrix_scale(matrix: tuple[float, ...]) -> float:
    a, b, c, d, _, _ = matrix
    return (math.hypot(a, b) + math.hypot(c, d)) / 2.0


def resolved_style(
    elem: ET.Element,
    inherited: dict[str, str],
    css_classes: dict[str, dict[str, str]],
) -> dict[str, str]:
    style = inherited.copy()
    for class_name in elem.attrib.get("class", "").split():
        style.update(css_classes.get(class_name, {}))
    style.update(expand_font(declarations(elem.attrib.get("style"))))
    for key in PRESENTATION_ATTRS:
        if key in elem.attrib:
            style[key] = elem.attrib[key]
    return style


def parse_points(raw: str) -> list[tuple[float, float]]:
    values = [float(value) for value in re.findall(NUMBER, raw)]
    if len(values) % 2:
        raise ValueError(f"Odd polygon coordinate count: {raw}")
    return list(zip(values[0::2], values[1::2]))


def parse_linear_path(raw: str) -> list[dict[str, object]]:
    tokens = re.findall(rf"[A-Za-z]|{NUMBER}", raw)
    paths: list[dict[str, object]] = []
    current_points: list[tuple[float, float]] = []
    current = (0.0, 0.0)
    start = (0.0, 0.0)
    command: str | None = None
    index = 0

    def finish(closed: bool = False) -> None:
        nonlocal current_points
        if current_points:
            paths.append({"points": current_points, "closed": closed})
            current_points = []

    while index < len(tokens):
        token = tokens[index]
        if token.isalpha():
            command = token
            index += 1
            if command in "Zz":
                finish(True)
                current = start
                command = None
                continue
            if command not in "MmLlHhVv":
                raise ValueError(f"Unsupported SVG path command: {command}")
        if command is None:
            raise ValueError(f"Malformed SVG path: {raw}")
        if command in "MmLl":
            if index + 1 >= len(tokens):
                raise ValueError(f"Incomplete SVG path command: {raw}")
            x, y = float(tokens[index]), float(tokens[index + 1])
            index += 2
            if command.islower():
                x += current[0]
                y += current[1]
            current = (x, y)
            if command in "Mm":
                finish(False)
                start = current
                current_points = [current]
                command = "l" if command == "m" else "L"
            else:
                current_points.append(current)
        elif command in "Hh":
            x = float(tokens[index])
            index += 1
            if command == "h":
                x += current[0]
            current = (x, current[1])
            current_points.append(current)
        elif command in "Vv":
            y = float(tokens[index])
            index += 1
            if command == "v":
                y += current[1]
            current = (current[0], y)
            current_points.append(current)
    finish(False)
    return paths


def parse_svg(path: Path) -> dict[str, object]:
    root = ET.parse(path).getroot()
    viewbox = [float(value) for value in re.findall(NUMBER, root.attrib.get("viewBox", ""))]
    if len(viewbox) == 4:
        origin_x, origin_y, width, height = viewbox
    else:
        origin_x = origin_y = 0.0
        width = number(root.attrib.get("width"), 1920.0)
        height = number(root.attrib.get("height"), 1080.0)

    css_classes = parse_css(root)
    symbols = {
        elem.attrib["id"]: elem
        for elem in root.iter()
        if tag_name(elem.tag) == "symbol" and "id" in elem.attrib
    }
    elements: list[dict[str, object]] = []
    warnings: list[str] = []
    sequence = 0

    def emit(kind: str, elem: ET.Element, style: dict[str, str], **payload: object) -> None:
        nonlocal sequence
        sequence += 1
        item: dict[str, object] = {
            "kind": kind,
            "name": elem.attrib.get("id", f"{kind}-{sequence}"),
            "fill": style.get("fill", "#000000"),
            "stroke": style.get("stroke", "none"),
            "stroke_width": number(style.get("stroke-width"), 1.0),
            "dashed": style.get("stroke-dasharray", "none") not in {"none", ""},
        }
        item.update(payload)
        elements.append(item)

    def walk(elem: ET.Element, parent_matrix: tuple[float, ...], inherited: dict[str, str]) -> None:
        tag = tag_name(elem.tag)
        if tag in {"defs", "style", "title", "desc", "metadata"}:
            return
        style = resolved_style(elem, inherited, css_classes)
        matrix = multiply(parent_matrix, transform_matrix(elem.attrib.get("transform")))

        if tag in {"svg", "g", "symbol"}:
            for child in list(elem):
                walk(child, matrix, style)
            return

        if tag == "use":
            href = elem.attrib.get("href") or elem.attrib.get("{http://www.w3.org/1999/xlink}href")
            target = symbols.get((href or "").lstrip("#"))
            if target is None:
                warnings.append(f"Unresolved <use>: {href}")
                return
            target_viewbox = [float(value) for value in re.findall(NUMBER, target.attrib.get("viewBox", ""))]
            tx, ty = number(elem.attrib.get("x")), number(elem.attrib.get("y"))
            use_matrix = multiply(matrix, (1.0, 0.0, 0.0, 1.0, tx, ty))
            if len(target_viewbox) == 4:
                vx, vy, vw, vh = target_viewbox
                target_width = number(elem.attrib.get("width"), vw)
                target_height = number(elem.attrib.get("height"), vh)
                use_matrix = multiply(use_matrix, (target_width / vw, 0.0, 0.0, target_height / vh, -vx * target_width / vw, -vy * target_height / vh))
            for child in list(target):
                walk(child, use_matrix, style)
            return

        if tag == "rect":
            x, y = number(elem.attrib.get("x")), number(elem.attrib.get("y"))
            w, h = number(elem.attrib.get("width")), number(elem.attrib.get("height"))
            corners = [point(matrix, x, y), point(matrix, x + w, y), point(matrix, x, y + h), point(matrix, x + w, y + h)]
            xs, ys = [p[0] for p in corners], [p[1] for p in corners]
            emit("rect", elem, style, x=min(xs), y=min(ys), width=max(xs) - min(xs), height=max(ys) - min(ys), rx=number(elem.attrib.get("rx") or style.get("rx")) * matrix_scale(matrix))
        elif tag in {"circle", "ellipse"}:
            cx, cy = number(elem.attrib.get("cx")), number(elem.attrib.get("cy"))
            rx = number(elem.attrib.get("r") or elem.attrib.get("rx"))
            ry = number(elem.attrib.get("r") or elem.attrib.get("ry"))
            center = point(matrix, cx, cy)
            x_edge = point(matrix, cx + rx, cy)
            y_edge = point(matrix, cx, cy + ry)
            out_rx = math.dist(center, x_edge)
            out_ry = math.dist(center, y_edge)
            emit("ellipse", elem, style, x=center[0] - out_rx, y=center[1] - out_ry, width=2 * out_rx, height=2 * out_ry)
        elif tag == "line":
            start_point = point(matrix, number(elem.attrib.get("x1")), number(elem.attrib.get("y1")))
            end_point = point(matrix, number(elem.attrib.get("x2")), number(elem.attrib.get("y2")))
            emit("line", elem, style, x1=start_point[0], y1=start_point[1], x2=end_point[0], y2=end_point[1], fill="none")
        elif tag in {"polygon", "polyline"}:
            points = [point(matrix, x, y) for x, y in parse_points(elem.attrib.get("points", ""))]
            emit("polygon", elem, style, points=points, closed=tag == "polygon")
        elif tag == "path":
            try:
                paths = parse_linear_path(elem.attrib.get("d", ""))
            except ValueError as exc:
                raise ValueError(f"{path}: {exc}") from exc
            transformed = [
                {"points": [point(matrix, x, y) for x, y in subpath["points"]], "closed": subpath["closed"]}
                for subpath in paths
            ]
            emit("path", elem, style, paths=transformed)
        elif tag == "text":
            text = "".join(elem.itertext()).strip()
            if not text:
                return
            x, y = point(matrix, number(elem.attrib.get("x")), number(elem.attrib.get("y")))
            elements.append(
                {
                    "kind": "text",
                    "name": elem.attrib.get("id", f"text-{sequence + 1}"),
                    "text": text,
                    "x": x,
                    "y": y,
                    "font_size": number(style.get("font-size"), 16.0) * matrix_scale(matrix),
                    "font_weight": style.get("font-weight", "400"),
                    "font_style": style.get("font-style", "normal"),
                    "font_family": style.get("font-family", "Pretendard").split(",")[0].strip(' "\''),
                    "anchor": style.get("text-anchor", "start"),
                    "fill": style.get("fill", "#000000"),
                }
            )
        else:
            warnings.append(f"Skipped unsupported element: <{tag}>")

    root_matrix = (1.0, 0.0, 0.0, 1.0, -origin_x, -origin_y)
    walk(root, root_matrix, {})
    return {"source": str(path), "width": width, "height": height, "elements": elements, "warnings": warnings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("svg", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = parse_svg(args.svg.resolve())
    payload = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        sys.stdout.write(payload + "\n")


if __name__ == "__main__":
    main()
