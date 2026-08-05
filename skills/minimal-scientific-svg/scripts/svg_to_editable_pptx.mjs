#!/usr/bin/env node

import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath, pathToFileURL } from "node:url";


function parseArgs(argv) {
  const inputs = [];
  let output;
  let previewDir;
  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    if (arg === "--input") inputs.push(argv[++index]);
    else if (arg === "--output") output = argv[++index];
    else if (arg === "--preview-dir") previewDir = argv[++index];
    else if (arg === "--help") return { help: true, inputs, output, previewDir };
    else throw new Error(`Unknown argument: ${arg}`);
  }
  if (!inputs.length || !output) throw new Error("Use --input slide.svg [--input slide2.svg] --output deck.pptx");
  return { inputs, output, previewDir };
}


async function loadArtifactTool() {
  const configured = process.env.CODEX_ARTIFACT_TOOL_ENTRY;
  const base = path.join(
    os.homedir(),
    ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist",
  );
  const candidates = configured
    ? [configured]
    : [path.join(base, "node/artifact_tool.mjs"), path.join(base, "artifact_tool.mjs")];
  for (const candidate of candidates) {
    try {
      await fs.access(candidate);
      return import(pathToFileURL(candidate).href);
    } catch {
      // Try the next bundled entry point.
    }
  }
  throw new Error("@oai/artifact-tool was not found. Set CODEX_ARTIFACT_TOOL_ENTRY to its artifact_tool.mjs file.");
}


function parseSvg(svgPath) {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const parserPath = path.join(scriptDir, "parse_svg.py");
  const python = process.env.CODEX_PYTHON || "python3";
  const result = spawnSync(python, [parserPath, path.resolve(svgPath)], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(result.stderr.trim() || `SVG parsing failed: ${svgPath}`);
  return JSON.parse(result.stdout);
}


function prepareForEditing(pptxPath) {
  const scriptDir = path.dirname(fileURLToPath(import.meta.url));
  const scriptPath = path.join(scriptDir, "prepare_pptx_editing.py");
  const python = process.env.CODEX_PYTHON || "python3";
  const result = spawnSync(python, [scriptPath, path.resolve(pptxPath)], { encoding: "utf8" });
  if (result.status !== 0) throw new Error(result.stderr.trim() || `PPTX editing preparation failed: ${pptxPath}`);
}


function lineStyle(element) {
  if (!element.stroke || element.stroke === "none" || Number(element.stroke_width) === 0) {
    return { style: "solid", fill: "none", width: 0 };
  }
  return {
    style: element.dashed ? "dashed" : "solid",
    fill: element.stroke,
    width: Number(element.stroke_width) || 1,
  };
}


function shapeFill(element) {
  return !element.fill || element.fill === "none" ? "none" : element.fill;
}


function addRect(slide, element) {
  slide.shapes.add({
    geometry: element.rx > 0 ? "roundRect" : "rect",
    name: element.name,
    position: { left: element.x, top: element.y, width: element.width, height: element.height },
    fill: shapeFill(element),
    line: lineStyle(element),
    ...(element.rx > 0 ? { borderRadius: element.rx } : {}),
  });
}


function addEllipse(slide, element) {
  slide.shapes.add({
    geometry: "ellipse",
    name: element.name,
    position: { left: element.x, top: element.y, width: element.width, height: element.height },
    fill: shapeFill(element),
    line: lineStyle(element),
  });
}


function addLine(slide, element) {
  const left = Math.min(element.x1, element.x2);
  const top = Math.min(element.y1, element.y2);
  const width = Math.abs(element.x2 - element.x1);
  const height = Math.abs(element.y2 - element.y1);
  const style = lineStyle(element);
  if (!element.dashed && height < 0.001 && style.fill !== "none") {
    slide.shapes.add({
      geometry: "rect",
      name: element.name,
      position: { left, top: top - style.width / 2, width, height: style.width },
      fill: style.fill,
      line: { style: "solid", fill: "none", width: 0 },
    });
    return;
  }
  if (!element.dashed && width < 0.001 && style.fill !== "none") {
    slide.shapes.add({
      geometry: "rect",
      name: element.name,
      position: { left: left - style.width / 2, top, width: style.width, height },
      fill: style.fill,
      line: { style: "solid", fill: "none", width: 0 },
    });
    return;
  }
  slide.shapes.add({
    geometry: "line",
    name: element.name,
    position: {
      left,
      top,
      width: Math.max(width, 0.01),
      height: Math.max(height, 0.01),
      horizontalFlip: element.x2 < element.x1,
      verticalFlip: element.y2 < element.y1,
    },
    fill: "none",
    line: style,
  });
}


function addCustom(slide, element, paths) {
  const allPoints = paths.flatMap((item) => item.points);
  if (!allPoints.length) return;
  const xs = allPoints.map((item) => item[0]);
  const ys = allPoints.map((item) => item[1]);
  const left = Math.min(...xs);
  const top = Math.min(...ys);
  const width = Math.max(Math.max(...xs) - left, 0.01);
  const height = Math.max(Math.max(...ys) - top, 0.01);
  const customPaths = paths.map((item) => {
    const commands = [];
    item.points.forEach(([x, y], index) => {
      commands.push(index === 0 ? { moveTo: { x: x - left, y: y - top } } : { lineTo: { x: x - left, y: y - top } });
    });
    if (item.closed) commands.push({ close: {} });
    return { width, height, commands };
  });
  slide.shapes.add({
    geometry: "custom",
    name: element.name,
    position: { left, top, width, height },
    fill: shapeFill(element),
    line: lineStyle(element),
    customPaths,
  });
}


function addText(slide, element, slideWidth) {
  const fontSize = Number(element.font_size) || 16;
  const fontSizePt = Math.max(1, Math.round(fontSize * 0.75));
  const typeface = "Pretendard";
  const bold = ["bold", "600", "700", "800", "900"].includes(String(element.font_weight));
  const estimatedWidth = Math.max(20, element.text.length * fontSize * 0.67 + 20);
  let left;
  let alignment;
  if (element.anchor === "middle") {
    left = Math.max(0, element.x - estimatedWidth / 2);
    alignment = "center";
  } else if (element.anchor === "end") {
    left = Math.max(0, element.x - estimatedWidth);
    alignment = "right";
  } else {
    left = Math.max(0, element.x);
    alignment = "left";
  }
  const width = Math.min(estimatedWidth, slideWidth - left);
  const height = fontSize * 1.55;
  const shape = slide.shapes.add({
    geometry: "textbox",
    name: element.name,
    position: { left, top: element.y - fontSize * 1.15, width, height },
    fill: "none",
    line: { style: "solid", fill: "none", width: 0 },
  });
  shape.text.set([{
    runs: [{
      run: element.text,
      textStyle: {
        fontSize: `${fontSizePt}pt`,
        bold,
        color: element.fill || "#000000",
        typeface,
      },
    }],
  }]);
  shape.text.style = {
    alignment,
    verticalAlignment: "middle",
    wrap: "none",
    autoFit: "none",
    insets: { top: 0, right: 0, bottom: 0, left: 0 },
    typeface,
  };
}


function addElement(slide, element, slideWidth) {
  if (element.kind === "rect") addRect(slide, element);
  else if (element.kind === "ellipse") addEllipse(slide, element);
  else if (element.kind === "line") addLine(slide, element);
  else if (element.kind === "polygon") addCustom(slide, element, [{ points: element.points, closed: element.closed }]);
  else if (element.kind === "path") addCustom(slide, element, element.paths);
  else if (element.kind === "text") addText(slide, element, slideWidth);
  else throw new Error(`Unsupported manifest element: ${element.kind}`);
}


async function saveBlob(filePath, blob) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, new Uint8Array(await blob.arrayBuffer()));
}


async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log("Usage: node svg_to_editable_pptx.mjs --input slide.svg [--input slide2.svg] --output deck.pptx [--preview-dir previews]");
    return;
  }
  const manifests = args.inputs.map(parseSvg);
  const width = manifests[0].width;
  const height = manifests[0].height;
  for (const manifest of manifests) {
    if (manifest.width !== width || manifest.height !== height) {
      throw new Error("All SVG inputs must use the same viewBox size.");
    }
    if (manifest.warnings.length) {
      throw new Error(`${manifest.source}: ${manifest.warnings.join("; ")}`);
    }
  }

  const { Presentation, PresentationFile } = await loadArtifactTool();
  const presentation = Presentation.create({ slideSize: { width, height } });
  for (let index = 0; index < manifests.length; index += 1) {
    const manifest = manifests[index];
    const slide = presentation.slides.add();
    slide.background.fill = "#FFFFFF";
    for (const element of manifest.elements) addElement(slide, element, width);
    if (args.previewDir) {
      const preview = await presentation.export({ slide, format: "png", scale: 1 });
      await saveBlob(path.join(path.resolve(args.previewDir), `slide-${String(index + 1).padStart(2, "0")}.png`), preview);
    }
  }

  const outputPath = path.resolve(args.output);
  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  const pptx = await PresentationFile.exportPptx(presentation);
  await pptx.save(outputPath);
  prepareForEditing(outputPath);
  await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
  console.log(outputPath);
}


main().catch((error) => {
  console.error(error.stack || error.message || error);
  process.exitCode = 1;
});
