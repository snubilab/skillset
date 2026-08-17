---
name: making-conference-posters
description: Use when building a printed A0 academic conference poster from a paper or results, or when a poster has text clipped at a box edge, columns wider than the sheet, figures missing their axis labels, large empty gaps between blocks, or wording and terminology that do not appear in the source paper.
---

# Making Conference Posters

Build the poster as HTML at true physical size, **measure** that it fits, then export PDF + PPTX.

**Core principle: a poster is a layout that either fits or does not. Never judge fit by looking at a screenshot — measure it.** A poster viewed at 30% zoom hides a 15 cm overflow; the printer will not.

The scripts are not on `PATH`. Set this once:

```bash
S=~/.claude/skills/making-conference-posters/scripts
```

## Workflow

1. **Survey the paper.** Lists each figure/table caption and its absolute PDF page. It matches on caption-like text, so cross-references in body prose come through as hits; in a paper whose appendix dwarfs its body the list is mostly supplementary floats. Mark which hits are real captions and which are main-text before choosing.
   `uv run --with pillow $S/extract_assets.py survey paper.pdf`
2. **Extract the source's terminology.** Get the source text and normalise it — `pdftotext -layout paper.pdf - | tr '\n' ' ' | sed 's/- //g' | tr -s ' ' > source.txt` (the `.tex` works too). The normalisation is not optional: raw extraction keeps hard line breaks and end-of-line hyphenation, and `grep` is line-oriented, so a phrase present verbatim scores zero and write a plain term list you keep beside the poster: the method and its components, each baseline and how the paper classes it, dataset/split/setup nouns, each metric and the subset it is computed over, the paper's hedges on its own claims ("may", "suggests", "is consistent with"), and its section headings — the headings become the banners. Write the poster from this list; the grep in the paraphrase section verifies against it.
3. **Cut the assets.** One call per figure/table. Each prints the `aspect-ratio:` line to paste.
   `uv run --with pillow $S/extract_assets.py crop paper.pdf --page 11 --out fig1.png --box 252,148,1150,710 --ref-dpi 150`
   Add `--whole` first to eyeball a page and find the box, and **pass back the `--ref-dpi` that `--whole` prints** — its output is capped in width, so its pixels are not the dpi you asked for and a box measured on it lands somewhere else at any other value. Add `--text` for tables (1-bit PNG).
4. **Lay out.** Copy `assets/template.html`. Set `--sheet-w/h` and `--acc`; leave `--cols` at 3 — it is the only value verified. At 4 the banner's fixed clip-path corner eats enough of a narrower column to cut the heading, and nothing reports it. Write content from the step-2 term list. Give each `<img>` the `aspect-ratio` from step 3. Name the section banners from the headings on that list, and take every size and spacing value from the template — do not type one inline.
5. **Audit.** Fix everything it reports, repeat until clean. A `--root` or `--card` selector matching nothing is an error, not a pass. Exit 0 alone is not clean: `DEAD SPACE` and `LETTERBOX` are report-only and never fail the exit code — read the output, do not gate on the status.
   `uv run $S/audit_fit.py poster.html --sheet 84.1x118.9 --root '#poster'`
6. **Fit the type.** Sweeps `--s`, reports the largest that fits. Bake it in.
   `uv run $S/audit_fit.py poster.html --sheet 84.1x118.9 --root '#poster' --scan-scale`
7. **Export.** PDF (vector text — print this), PNG, PPTX.
   `bash $S/export_poster.sh poster.html 84.1 118.9 myposter`
8. **Editable PPTX (optional).** For people who must edit in PowerPoint. Rebuilds every box as a real shape and every block as a real text frame, from the rendered DOM.
   `uv run --with python-pptx $S/html_to_pptx.py poster.html --sheet 84.1x118.9 --root '#poster' --out editable.pptx`
9. **Check the PDF's internals.** `pdffonts out.pdf` — any `Type 3` is a print blocker (see the variable-font trap below). `pdfinfo` for the page size. Bleed: Chrome writes no TrimBox/BleedBox, so either get borderless printing confirmed in writing or add 3 mm and offset the content.
10. **Read the render.** `pdftocairo -png -r 100 myposter.pdf proof` then open `proof-1.png` and actually read it. **Not optional** — see the next section for why.

## Reading the render is where the real errors are

The audit proves nothing is *clipped* **by the measurements it takes**, and it cannot read. Four things it does not see, so do not treat a clean run as proof of them: **`clip-path` ink loss** — a diagonal corner removes glyphs without changing any scroll metric, so a decapitated banner prints no line; **per-element horizontal overflow** — width is checked at the root only; **overflow into a box's own padding** — an element can sit a padding-height plus `--tol` past its content box and still exit 0; and **per-glyph font fallback** — the font check is family-level, so a codepoint missing from a subset silently substitutes another face. What ships past a clean audit is wrong content, so read the proof for each of these:

- **The asset itself** — a crop can pass every geometry check with its last row of digits sliced through.
- **Trends and comparisons** — a caption can assert an analysis the source never ran.
- **Scope** — a property true of some compared items, stated as true of all of them.
- **Lost qualifiers** — a partial cost printed as the total. The qualifier tends to live in the source's table caption, not in the sentence that quotes the number.
- **Hardened hedges** — the source's "may" turned into "because".

**Quantifiers and scope go wrong more often than numbers, and are harder to spot.** Adding or dropping a domain qualifier changes what a claim invites: narrowed to the one method family the paper happens to use, the motivation invites "so use a different family"; widened, it claims territory the paper never defends. Check every *all / most / only / always* and every domain qualifier against the source, not just the digits.

**Check every claim against the source, not against your memory of the source.** You wrote the summary; you are the worst reader of it. If a sentence asserts a comparison, a trend, or a cause, find the line that supports it. If you cannot find that line, cut the sentence.

## You are transcribing the work, not reviewing it

**The poster carries the author's name. Put the source's content on it — not your opinion of the source.**

Fixing your own transcription error is required. Adding a caveat the source never makes is not yours to add. The two feel identical while you are doing them, and they are opposites:

| Legitimate — you misrepresented the source | Not yours — the source doesn't say it |
|---|---|
| The source qualifies a number, you swapped or dropped the qualifier → fix it | Source reports a p-value with no named test → **don't** append "test not named" |
| You stated a property of all baselines that the source gives only some → fix it | Source claims a mechanism → **don't** append a caveat that it was never isolated |
| Source hedges "may be" → restore the hedge | Source reports a metric → **don't** add effect sizes it never computed |
| You invented a trend → delete it | Source's own table has an error → tell the author; don't annotate it on their poster |

If review surfaces a real problem with the work, **raise it with the author**. Printing it under their name on their poster is not diligence, it is publishing your review of them. Select fewer of the source's sentences when space is short — that is normal poster-making. Rewriting their claims into your assessment is not.

**The same boundary applies to the layout.** A lab's poster template is shared, established property: its type scale, banner geometry, palette and logo slots are decisions already made. Fit content to the template, and adjust only the one global type-scale knob. If a review finds the template's own hierarchy is wrong, report the measurements to whoever owns the template — do not silently redesign it inside one poster. "The template" here means its identity: type-scale ratios, banner geometry, palette, logo slots. Per-poster spacing may be tightened (fix order below) — but only at its single declaration site, never inline at one use.

Which means **the template has to be the only place a geometry value is written.** Any spacing, height or size used at more than one site is declared once — a class or a custom property — and referenced; the drift row in the trap table has the check.

## Use the source's words, not your paraphrase

A meaning-preserving paraphrase still fails invisibly: every claim checks out, so the claim-level pass above reports clean — but to a reader who knows the field, a term they have never seen reads as a *different* method.

**The check is mechanical, and it verifies step 2's term list.** Grep every distinctive phrase you wrote against the source text; a phrase that is not on the list, or scores zero hits, is yours — replace it with the source's term.

```bash
for p in "phrase-1" "phrase-2" "phrase-3"; do
  printf '%-24s %s\n' "$p" "$(grep -oc "$p" source.txt)"    # step 2's text - CASE-SENSITIVE
done
```

Watch especially for a category label the paper never uses, and for an inversion of the source's framing (keeping-the-best restated as discarding-the-worst).

**Grep case-sensitively.** Fields routinely distinguish methods by capitalisation alone — an acronym, its lower-cased variant and a mixed-case third method can be three different published methods by three different authors. A case-folding grep merges them and reports a healthy hit count for a term the paper never uses, so the check passes on exactly the error it exists to catch. If two entries on the step-2 list differ only in case, note that on the list.

**Run the grep before you accept that a term is wrong — including when the author names it.** A phrase challenged in review can be the paper's own wording, verbatim; deleting it out of deference is a regression. **A zero is not actionable until the normalised text has also scored zero** — on raw extraction a wrapped or hyphenated phrase scores zero while being present, and acting on that deletes the author's own words.

**Figure labels are source too.** The caption must call things what the plot's own legend and axis labels call them; a renamed legend entry is an invented term.

**Section banners are source structure, not free-form headings.** Take them from the section headings on the step-2 term list and nothing else. A banner reading `EVIDENCE` over what the paper calls Results is an invented category, and it is far more visible than an invented word inside a paragraph — it is the largest type on the sheet and it tells the reader the paper has a section it does not have. When a section outgrows one column, **drop the second banner and let the column continue the section**; do not rename the overflow into a new category to justify a second banner. The reverse case is commoner: a paper has more sections than a poster can carry. Drop whole sections rather than invent a merged name for them — a theory or derivation section usually has no poster form — and keep the surviving banners spelled as the paper spells them.

## Empty space is a content problem — never a type problem

Columns fill unevenly. The temptation at every uneven column is to enlarge its type, or pad its boxes, until the gap closes. Do that per column and the poster ends up with **a different body size in every column**, all of it invisible to the audit: nothing is clipped, and the inflated type fills the columns so no `DEAD SPACE` line ever prints.

**One body size, declared once, for the whole sheet.** `assets/template.html` declares it as `.card{font-size:calc(29pt * var(--s))}`; the only sanctioned deviations are its declared step-down classes `.compact` and `.dense` — never an inline `font-size`. Before you introduce a knob to control body size, `grep font-size` the template — the knob is already there, and adding a second one is how the drift starts.

The fix order when a column is short or long, hardest first:

1. **Is a source figure or table missing?** Inventory the paper's floats against the poster before anything else — a sparse column is often a missing figure, and padding hides the absence for revision after revision.
2. **Cut or merge content** in the long column.
3. **Reclaim spacing** — `gap`, `margin`, container `padding`. This is what "tighten it up" means.
4. **`--s`, last.** It is global: it shrinks the title, the banners and every other column to fix one. Reach for it only when the whole sheet is uniformly over or under.

**A complaint about spacing is not permission to change the type scale.** "This gap is too big" means fix 3 above, not `--s`. Changing `--s` there shrinks text the user never complained about, and they will notice.

## Traps that silently produce a broken poster

| Trap | Symptom | Fix |
|---|---|---|
| `pdfimages` to extract a figure | Figure appears with no column headers, axis labels, or per-panel numbers | Journal figures are a raster panel + **vector text on top**. Render the page and crop. `extract_assets.py crop` does this. |
| `grid-template-columns: 1fr 1fr 1fr` | Columns render unequal and the grid runs off the sheet | `1fr` = `minmax(auto,1fr)` and **will not shrink below min-content**. One long unbreakable string blows it out. Use `repeat(N, minmax(0,1fr))`. |
| Checking only the top-level container for overflow | Reports "fits" while content is clipped | `min-height:0` lets a flex child shrink, so the parent's `scrollHeight == clientHeight` even though inner content is cut. Walk **every** descendant. |
| Eyeballing the crop box | Last table column or row sliced off | Auto-trim to the ink. `extract_assets.py` does, with padding — but still read the result (step 10). |
| Sizing an image's box by hand — a fixed height, or shrinking its container to reclaim vertical space | Letterbox gaps or a cropped image; with a width-capped image the reclaimed space just reappears left and right as `LETTERBOX` | Declare `aspect-ratio: W/H` on the `<img>` (step 3 prints the line) and let height follow width. If `LETTERBOX` still fires — only possible with `object-fit:contain` — look at the render before obeying: letterbox matching the background is invisible in print and fine; otherwise set the container to the `fix:` height the audit prints and take the space from text instead. |
| System font stack (`Helvetica, Arial, …`) | Poster reflows on another machine or at the print shop | Pin a webfont. Fallbacks have different metrics and your fit margin is usually 1–2 cm. `audit_fit.py` fails if the font did not load. |
| Retyping numbers from `pdftotext` | A wrong digit nobody catches until it's 2 m wide | Crop the real table as an image. If you must retype, cross-check against the rendered page. |
| Bolding a whole "ours" row | Claims a win on a metric a baseline actually won | Bold only genuinely-best cells, per metric. Check the source table's own bolding — it may itself be wrong. |
| `justify-content: space-between` to fill a column | Several large holes between blocks — **and the audit reports clean** | It spreads the leftover evenly, so no single block ever shows dead space at its bottom and the script sees nothing. Delete it and re-audit: the slack collects into one number. That number is the finding — a column reporting 9 cm is under-filled, not badly spaced. |
| Geometry written as an inline value at each use site (`gap:0.5cm` in one column, `0.25cm` in the others) | One banner sits lower than its siblings; nothing is clipped or empty, and the audit reports clean | The audit scores absolute defects, never conformance. **Do not fix this by comparing siblings** — columns that drift together still agree with each other. The template owns the value: declare it once as a class or custom property (`--gap-banner:0.25cm`) and reference it everywhere, so a deviation cannot be written in the first place. Auditing markup you inherited: `grep -n 'gap:\|padding:\|height:' poster.html` and check each hit **against the template's declared value**. |
| Deleting a few words to clear an overflow | Audit reports the **same** overflow, twice in a row | Height only moves when a line-wrap boundary is crossed; sub-line trims are free. Stop nibbling — merge two blocks or delete a whole one. |
| Auditing before deciding CJK line-breaking | Korean/CJK text that fit now overflows after `word-break:keep-all` is added — or breaks mid-word without it | CJK wraps per syllable by default; `keep-all` enlarges the unbreakable units that decide where lines wrap. Set it on the body before the first audit — every fit measured under the other setting is stale. |
| Removing `flex:1` from the last card to kill the dead space inside it | The box now hugs its text — and that column's bottom edge no longer lines up with the others | `flex:1` does **two** jobs: absorb the column's slack *and* hold the bottom edge on the shared baseline. Deleting it fixes the first and breaks the second. Keep the stretch; close the gap by adding content above it. |
| Two bordered cards for one section that simply continues | A hard rule across a section that has no break in it | Each card boundary costs ~2.8 cm of column height — two borders, two lots of `padding`, plus the gap. Merge them and separate the parts with a `margin-top` instead. |
| Hand-styling a new line of body text (`<div style="font-size:…">`) | It is the wrong size, or the right size with no bullet and no hanging indent | Use the existing body element verbatim — `<p class="b">&bull; …</p>`. The `&bull;` is the bullet; `.b` carries the `em`-based hanging indent and the line-height. Reaching for `.note` because the line sits next to a figure is the usual slip: `.note` is a caption style (smaller, grey), not a body style. |
| Judging a text block's true width from `audit_fit.py` | Reports `0 cm wide` no matter the font size | The audit measures per-element overflow vertically only (`scrollHeight`); width is checked at the root alone, whose fixed sheet width absorbs it. Measure in the browser (`Range.getBoundingClientRect`, or canvas `measureText`) — and if the result looks suspiciously round, re-measure by the other method before acting on it. |
| `Image.open(asset).convert('RGB')` while prepping a figure | Transparent regions turn **black**, so the source looks like a different (wrong) version and you keep a low-res copy | Alpha composites onto black by default. `alpha_composite` onto white first, then trim to ink. Check this before concluding a hi-res source does not exist. |
| Embedding images as base64 in a tool call | Runs out of output budget mid-file, corrupt asset | Keep images as **files beside the HTML**, referenced with `<img src>`. |
| Text-heavy crops as JPEG/WebP | Table text soft in print, file large | `--text` writes 1-bit PNG: sharper *and* ~3× smaller for black-on-white. |
| A **variable** webfont (`...Variable`, `wght 100..900`) | `pdffonts` shows dozens of **Type 3** subsets; print bureaus reject the file or it renders badly on older RIPs | Chrome cannot subset a variable font for PDF, so it emits Type 3 glyph procedures. Load the **static** family instead and re-check with `pdffonts` — you want `CID TrueType` or `Type 1C`. |
| Fixed-cm hanging indents (`padding-left:0.9cm`) | Wrapped bullet lines sit a few mm right of the first line, at every size below ~27 pt | The bullet's advance scales with type; the indent does not. Use `padding-left:0.75em; text-indent:-0.75em`. |
| A logo copied out of a browser | Prints soft at sheet size; fine hairlines and small caps mush | A right-click copy gives you the *displayed* size, often ~500 px. `audit_fit.py` reports effective dpi per image and fails below `--min-dpi` (default 150). Get the vector/original, or shrink the placement until it clears the floor. Never upscale — it invents no detail and smears edges. |
| A hardcoded port for the local preview server | Exports a **correctly sized PDF of someone else's poster** | Bind an ephemeral port and verify the server answers. The bundled scripts all bind ephemeral ports; only `export_poster.sh` also curl-checks the server. |

## The poster's own consistency

A third class of defect, and the one with no natural home in the two above: not a fit failure, so the audit is
silent; not a source mismatch, so checking against the paper finds nothing. These are conventions the poster
owes its reader, and they break when you **move or insert something after the first pass** — which is most of
the work. Re-check them after every reorder, not once at the end.

- **Numbering follows the poster's reading order, not the source's.** The paper's Figure 5 can be your Fig. 3.
  So inserting one float renumbers every float after it. Markup order is reading order, so the check is one
  line per sequence — figures and tables number independently, so check them apart and require each ascending:
  `grep -oE 'Fig\. [0-9]+\)' poster.html` and `grep -oE 'Table [0-9]+\)' poster.html`
  (match the label exactly as your captions write it; a pattern that misses one label reports a clean
  ascending run over the floats it did match)
- **A figure's caption goes below it; a table's goes above it.** Readers use the side to tell the two apart at
  a glance. This is the numbered caption only — it does not move an explanatory block that happens to sit near
  a figure (see the figure-before-its-legend rule below). Check the markup order inside each float's block.
- **Positional words are cross-references and they rot.** "detailed below", "the panel at left", "the table
  above" are true only of the arrangement you had when you typed them. `grep -niE 'above|below|left|right|following|previous' poster.html` after any move, and confirm each hit still describes the sheet.
- **Every float earns a caption, and every caption points at a float.** An asset dropped in during a
  space-filling pass tends to arrive uncaptioned; a float removed during a trimming pass tends to leave its
  caption behind.

## Judgment calls the scripts cannot make

- **Dead space is content debt, not a layout bug.** >3 cm empty at a card's bottom usually means you over-trimmed, not that gaps need stretching.
- **Put the source's stated costs on the poster** — runtime, failure modes, the metric where a baseline wins. A reviewer finds them anyway. **Then re-check the number's arithmetic against the source before printing it.**
- **Body text ≥ 24 pt, title ~70–80 pt.** These are A0 numbers and A0 is the only supported sheet. If content only fits below the floor, cut content.
- **A dense figure in a narrow column is unreadable even when it "fits."** A wide multi-panel figure squeezed into a single column renders its in-panel text far below the body-size floor. Span columns (`.span2`) or crop to the panels that carry the argument.
- **An image of a table is not a table.** A table cropped from the paper's page prints its digits *smaller* than your own smallest poster type, carries the paper's serif hairlines, and converts to 4-colour black (registration fringing). Re-typeset natively unless exactness against the paper matters more — and if you capture it, check the source table's own bolding before you inherit its errors.
- **Inventory the source's floats before you write a word.** List every figure and table in the paper and mark which ones the poster uses; the unused ones are the answer to any column that later reads sparse.
- **A poster is not the paper's index.** "Unfiltered results are in Supplementary Table S1" earns nothing — nobody at the session will look it up. If the pointer exists to flag that the printed table is filtered, state the filtering outright (or let the table's own caption do it) and cut the pointer. Keep disclosures, delete directions.
- **A figure goes above the text that explains it.** If a block is effectively the figure's legend, placing it first explains a picture the reader has not seen yet. Order it figure → parts → dynamics, and make the caption name the mapping. Reordering siblings inside one flex column costs zero height, so re-auditing is a formality.
- **Do not multiply the source's numbers into one it never reports.** Two quantities do not license their product just because the units compose — least of all when they come from different analyses. If the product appears nowhere in the source, print the qualified numbers it does give, qualifiers attached, and let the source's own scaling claim carry the rest.
- **A weakly reported statistic — a p-value with no named test, a relative-% gain on a bounded index — is still the source's number.** Transcribe it as-is and flag the gap to the author; the poster gets no annotation the source does not make (see the transcription table).

## Sheet sizes (cm)

**A0 only.** Portrait `84.1×118.9`; landscape `118.9×84.1` — swap the two values. `--sheet`, the template's `--sheet-w/h` and `export_poster.sh` all take width first, and the sheet gates check the render against what you declared, in both directions.

Smaller sheets are **not supported**, deliberately. The type scale is a pure multiple of `--s`, so it survives scaling — but the template's banner height, card padding, border width and clip-path corners are absolute centimetres and do not scale with it, so below A0 the hierarchy stops being proportional while every geometric check still passes. Building an A1 or A2 poster from this template requires editing those literals, which is editing the design. If you need a smaller sheet, print an A0 layout scaled down, or take it to whoever owns the template.

PowerPoint caps a slide at **142.24 cm**; `export_poster.sh` errors rather than silently shrinking (the PDF and PNG are still written).

## Requirements

poppler (`pdftocairo`, `pdftotext`, `pdfinfo`), Chrome or Chromium (set `CHROME_BIN` to override discovery), Python, `uv`, `curl`.
`extract_assets.py` needs Pillow (`uv run --with pillow`); `html_to_pptx.py` and the PPTX step of `export_poster.sh` need python-pptx (`uv run --with python-pptx`); `audit_fit.py` is stdlib-only.
The bundled template pulls its webfont from a CDN, so **audit and export need network access** — or self-host the woff2 and change the `<link>`.

## What you hand over

`export_poster.sh` writes all three from the one HTML, so there is nothing to re-make by hand:

| File | Use |
|---|---|
| `name.pdf` | **Send this to the printer.** Vector text, images embedded at full resolution, sheet size verified against `--sheet`. |
| `name.pptx` | One slide at the true physical size with the poster placed full-bleed — layout can never drift, but the text is not editable. Capped at PowerPoint's 142.24 cm limit. |
| `editable.pptx` | From `html_to_pptx.py`: real shapes + real text frames, so text can be edited in PowerPoint. **PowerPoint re-wraps with its own metrics**, so lines may break differently and blocks can overlap — treat it as a handoff copy, never as the print master. Needs the poster's font installed. |
| `name-1.png` | 150 dpi raster for email, Slack, or a proof read-through. |

Hand over the PDF as the print master and the PPTX alongside it — say which is which, because a poster shop given the PPTX will rasterise text that was vector in the PDF.
