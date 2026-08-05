---
name: minimal-scientific-svg
description: Create or redraw clean, restrained, editable SVG diagrams for scientific papers, clinical research, workflow figures, Figma frames, and PowerPoint slides, and convert the supported SVG elements directly into native editable PPTX objects. Use when converting a screenshot, sketch, table, workflow, architecture, or conceptual figure into a monochrome or limited-color line diagram, when editable SVG or PPTX is required, when preparing a Figma-to-PPTX handoff, or when matching the same minimal line style as an existing diagram.
---

# Minimal Scientific SVG

Create publication-style diagrams from native SVG elements. Preserve the source meaning while simplifying the visual language.

## Workflow

1. Inspect the source image or specification and list its panels, nodes, labels, states, arrow directions, semantic text levels, and intended editing units.
2. Search the target project for a reusable SVG before creating a new file.
3. Preserve the original asset. Write the redraw as a separate `.svg` unless replacement is explicitly requested.
4. Define shared geometry and typography tokens before placing repeated elements. Do not repair peers one at a time.
5. Reconstruct the diagram semantically with `<g>`, `<rect>`, `<line>`, `<path>`, `<polygon>`, `<circle>`, `<text>`, and `<use>` elements. Do not embed or trace the raster image.
6. Render the SVG and editable PPTX, inspect the full figure and a dense crop, and correct every overflow, collision, missing arrowhead, disconnected scope, and ambiguous connection before delivery.

## Visual language

- Use a white background and dark ink `#111827`.
- Use muted gray only for secondary or excluded states: `#4B5563`, `#6B7280`, `#F4F4F5`.
- Use one primary accent, normally blue `#2457FF`, for the active state or main path.
- Add orange `#F97316` or teal `#0F766E` only when distinct semantic roles require them.
- Do not use gradients, shadows, textures, decorative illustrations, or more colors than the meaning requires.
- Use 2–2.5 px strokes at a 1920×1080 viewBox. Use 3 px only for the active state.
- Use rounded rectangles with 8–14 px radii. Keep corners, strokes, and spacing consistent.
- Route connectors horizontally or vertically by default. Use 90-degree elbows for turns.
- For nodes in one row, use the exact same connector `y` coordinate; for nodes in one column, use the exact same connector `x` coordinate.
- Do not accept a nearly horizontal or nearly vertical diagonal. Realign the nodes or use an orthogonal elbow.
- Use a diagonal only when it encodes a genuinely diagonal relationship and no clean orthogonal route exists.
- Avoid decorative curves, crossing lines, and connectors that touch labels.

## Alignment and icon quality

- Build on an 8 px or 10 px grid. Use exact numeric positions rather than visual approximation.
- Give items in the same row identical top positions or optical centerlines. Give their labels identical baselines.
- Center each complete content group from its occupied bounds, not from its first item; compare the empty margins on both sides of the card.
- In a single-row strip, align the icons and labels around the panel's vertical centerline instead of following the top padding.
- Distribute repeated cards and icons with equal gaps. Keep panel padding symmetric.
- Use one icon family: the same 2–2.5 px stroke, rounded caps and joins, visual weight, and level of detail.
- Draw icons inside equal-size icon frames and optically center them. Do not mix tiny detailed icons with large sparse icons.
- Redraw an unclear or unattractive source icon semantically instead of tracing its defects.
- Do not use emoji or Unicode symbols as final icons. Construct icons from editable SVG geometry.
- Use icons only when they identify a distinct role, input, process, output, or validation type.

## Circular workflows and scope outlines

- Place repeated stages from one center, one radius, and equal angular increments. Do not hand-position a nearly circular sequence.
- Put arrowheads at the angular midpoints and rotate them tangentially. Keep the track itself a true circle; do not approximate it with independently curved arrows.
- Test complete card bounds, not only card centers. For every card corner `(x, y)`, require `hypot(x-cx, y-cy) + stroke/2 <= inner_radius - clearance`.
- Reserve at least 12 px between the farthest card corner and an enclosing ring at presentation scale. Include stroke width in the calculation.
- Keep an assignment or responsibility scope behind its cards. Its dashed boundary must surround all assigned cards, avoid their labels and borders, and remain inside the parent system boundary.
- Join a scope to its external label with exact shared endpoints. A connector must touch both the scope and callout; do not leave a visually small but real gap.
- Prefer an unfilled dashed boundary when color already identifies the scope. A tinted fill must not reduce contrast or imply data ownership that was not specified.
- Render the diagonal and bottom sectors at high zoom; circular containment errors are usually hidden in a full-slide thumbnail.

## Typography and spacing

- Use `Pretendard` as the explicit primary typeface for every SVG and PowerPoint text run. In SVG, use `Pretendard, "Apple SD Gothic Neo", Arial, sans-serif` only as a fallback stack; in PPTX, set `typeface: "Pretendard"` explicitly instead of relying on the theme.
- At 1920×1080, use 18–20 px for body text, 21–24 px for card titles, and 25–32 px for section titles.
- Define one shared class or token per semantic level, such as `project-label`, `stage-id`, `stage-title`, and `stage-output`. Peers at the same level must use the exact same size and weight.
- Use integer font sizes in both SVG and PowerPoint. In PPTX XML, explicit DrawingML font sizes must be divisible by 100 because they are stored in hundredths of a point.
- Disable `shrinkText`/`normAutofit` for repeated peer cards. Wrap or shorten text manually; otherwise longer peers silently render smaller than the rest.
- Use bold only for hierarchy, stage codes, titles, and active states.
- Keep at least 24 px internal horizontal padding and 18 px vertical padding.
- Wrap text with separate `<text>` elements. Do not use `<foreignObject>`.
- Shorten wording or add a line before reducing body text below 18 px.
- Never hide overflow with clipping and never force-fit text with horizontal distortion.
- Leave visible safety space around the longest line so PowerPoint font substitution cannot push it outside the box.

## Editable and compatible SVG

- Use `viewBox`; default to `1920 1080` for slides unless the requested destination requires another ratio.
- Keep all labels as text and all diagram parts as independent vector elements.
- Give major panels, stages, cards, and roles stable `id` values.
- Include `<title>` and `<desc>` for accessibility.
- SVG has no standalone `<arrow>` element. Prefer one closed filled `<path>` containing both shaft and head, or one native connector with an arrowhead when the complete export pipeline preserves it.
- Treat a separate line/rectangle plus triangle as a hard failure, including on circular tracks. Do not simulate an arrow by visually attaching a triangle to another object.
- Use `marker-end` only when SVG and PPTX validation prove that the connector and head remain one selectable object. Otherwise replace it with a single closed path or native connector.
- Export each arrow as one native PowerPoint object whenever possible so moving or recoloring it cannot separate the head from the shaft.
- Draw connectors behind boxes and arrowheads above connectors.
- Do not outline fonts, embed raster images, or rely on external fonts.

## Figma and Framedeck handoff

Use this path when the final deliverable is an editable PowerPoint deck:

1. Create one 1920×1080 SVG per slide or figure.
2. Import each SVG into Figma and place it inside a top-level 1920×1080 Frame. Do not leave the slide as a loose Group.
3. Preserve text as text and simple geometry as native vectors. Avoid masks, blur, blend modes, complex effects, and deeply nested clipping groups because PPTX exporters may flatten them.
4. Name top-level frames in slide order and keep every visible element within the frame boundary.
5. In Framedeck, select the frames and use **Native text and shapes** for editable PPTX output. Use an image fallback only for a layer that cannot map cleanly to PowerPoint.
6. Open the exported `.pptx` and verify fonts, line endings, arrowheads, grouping, and slide order.

Treat Framedeck export as a local Figma step. Prepare compatible frames automatically when Figma access is available, but do not claim that the third-party plugin export itself was automated unless it was actually run and verified.

## Direct editable PPTX export

Prefer the bundled local converter when the input follows this skill's SVG vocabulary. It converts text, rectangles, rounded rectangles, circles, ellipses, lines, polygons, and straight-line SVG paths into native PowerPoint objects. It supports nested translation, scale, rotation, CSS classes, and reusable SVG symbols. It fails instead of silently flattening unsupported curve, mask, blur, or filter features.

```bash
node scripts/svg_to_editable_pptx.mjs \
  --input slide-01.svg \
  --input slide-02.svg \
  --output deck.pptx \
  --preview-dir preview
```

Use one `--input` per slide, in slide order. Require the same `viewBox` size for all inputs. Keep `--preview-dir` for QA runs and omit it when only the final PPTX is requested.

After export, render and inspect the PPTX with the available presentation QA tools. Confirm that simple elements remain PowerPoint shapes or text boxes rather than pictures. Use the Figma/Framedeck route only when Figma editing or third-party compatibility testing is specifically required.

The direct converter removes DrawingML locks that block selecting, moving, resizing, grouping, ungrouping, rotating, editing text, or editing shape geometry.

## PowerPoint editing readiness

Prepare the file for immediate editing before delivery:

- Keep text as native text boxes and simple artwork as native shapes; do not flatten the slide or logical units into pictures.
- Remove `noGrp`, `noUngrp`, `noSelect`, `noMove`, `noResize`, `noRot`, `noTextEdit`, and related DrawingML edit locks.
- Give major panels, cards, arrows, icons, and labels stable names so they are identifiable in PowerPoint's Selection Pane.
- Use native groups for meaningful editing units when the exporter supports them: group an icon with its label, a card's contents, or one workflow stage. For a single self-contained figure that must resize as one unit, add one top-level figure group while preserving every child object; keep slide titles, subtitles, and footers outside that group.
- Never satisfy a resize-together request by flattening the figure or combining all content into one shape. The parent group must scale text and geometry together, and the children must remain editable after ungrouping.
- If an exporter flattens SVG `<g>` elements, state that the file is groupable but not pre-grouped; never claim that SVG grouping was preserved.
- Keep backgrounds and card plates at the back, connectors behind nodes, and labels above their shapes. Avoid invisible or transparent overlays that intercept selection.
- Open or render the exported PPTX and confirm that representative text, shapes, arrows, and groups remain selectable and editable.
- Reopen a copy, resize the figure group to 50%, and render it. Reject the export if fonts stay large, connectors separate, or child objects stop being editable.

## Validation

Run the smallest available checks:

```bash
xmllint --noout output.svg
sips -s format png output.svg --out preview.png

python scripts/validate_editable_diagram.py \
  --svg output.svg \
  --pptx output.pptx \
  --require-font Pretendard \
  --require-group workflow-diagram-group \
  --same-font-regex '^stage-[0-9]+-card$' \
  --same-font 'project-label-a,project-label-b,project-label-c' \
  --no-autofit '^stage-[0-9]+-card$'
```

Inspect the rendered preview at full size. Confirm:

- every label remains inside its box with safety margins;
- same-level labels use identical explicit font sizes and weights;
- every SVG/PPTX text run resolves to Pretendard as its primary typeface;
- repeated cards do not use automatic font shrinking;
- no text, line, or arrow overlaps another label;
- every arrowhead renders and points in the intended direction;
- each arrow remains a single selectable object rather than separate shaft and head objects;
- exported native shapes contain no DrawingML lock that blocks normal PowerPoint editing;
- all intended horizontal and vertical connectors remain exactly axis-aligned in both SVG and exported PPTX;
- nodes in a row share their icon centerline and label baseline;
- repeated icons share stroke weight, frame size, and optical scale;
- active, excluded, past, current, and next states remain distinguishable without relying on color alone;
- every card and dashed scope remains inside its intended enclosing boundary with measured clearance;
- every scope-to-callout connector is continuous at both endpoints;
- the original file remains unchanged when a derivative was requested.

Inspect a zoomed crop of the densest row after PPTX export. Do not approve the figure from a full-slide thumbnail alone.

Deliver the SVG path and state that it is editable and render-validated. Avoid producing extra PNG or PDF files unless requested.
