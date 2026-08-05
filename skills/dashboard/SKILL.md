---
name: dashboard
description: 'Build a single self-contained, shareable HTML dashboard that shows results at a glance — entity/model-level overview PLUS per-item/per-sample detail, with optional per-item media (images) viewer. Use whenever a task produces metrics, an experiment comparison, an evaluation, a benchmark, a leaderboard, an audit, or any table of numbers-by-category that a person should be able to scan and drill into. Triggers: "dashboard", "시각화 대시보드", "결과 한눈에", "모델별/샘플별 성능", "visualize results", "results page", "per-sample viewer", "compare models/variants", "leaderboard". General-purpose (not domain-specific).'
---

# Dashboard

Turn a results table (entities × metrics, plus optional per-item rows and media)
into ONE self-contained `.html` file that a person can open, scan, and drill into
— then publish it (Claude Code: the Artifact tool; otherwise write the file and
give the path). Works for ML experiments, evals, benchmarks, audits, A/B tests,
cost reports — anything shaped "metrics by category, with items underneath."

## Non-negotiables (why dashboards fail)

1. **Self-contained.** Inline ALL data (as `<script type="application/json">`),
   CSS, and JS. Embed images as `data:` URIs. NO external URLs, CDNs, fonts, or
   fetch — artifact CSP blocks them and they break offline. System font stacks
   only (`system-ui` for text, `ui-monospace` for numbers).
2. **Honest encoding.** Show the real story, including a null/negative result.
   If three variants overlap, make the overlap legible (zoomed axis + a note
   saying "near-identical") — never zoom or truncate to manufacture a difference.
   Put a one-line **verdict banner** at the top stating the finding plainly.
3. **Two altitudes, matched to the data's job.** ALWAYS ship the whole-work
   overview plus a detail page. Numeric sample/variant detail uses distributions,
   per-item delta-vs-baseline, and a sortable table. Research-unit, capability,
   or workstream detail uses semantic cards: role, current judgment,
   evidence/completion stage, blockers, and next completion gate. If both exist,
   render unit cards first and numeric detail below. Add a **media viewer** when
   items have images.
4. **Theme-aware.** Token-based light + dark. Define palette as CSS custom
   properties on `:root`; redefine under `@media (prefers-color-scheme: dark)`
   AND `:root[data-theme="dark"]` / `[data-theme="light"]` (the viewer's toggle
   stamps `data-theme` and must win). Give dark real care, not an inversion.
   Any token that ends up as TEXT — status inks on badges and pills, a "best"
   value, a delta, secondary copy — needs 4.5:1 against the surface it sits on,
   **in both themes**, measured. Chart-hue validation does not cover this: a
   green that reads fine as a bar is 3:1 as 13px type. And never hard-code `#fff`
   on a token background (`--accent` is dark in light mode and light in dark
   mode); pair the fill with theme-dependent ink like `.chip[aria-pressed]` does.
   **Scope: this governs what YOU author.** When extending a dashboard someone
   else built, measure the whole page but only FIX your own additions — report
   pre-existing failures (element, measured ratio, proposed fix) and let the owner
   decide. Same for every other rule here. A restyle nobody asked for arrives as an
   unreviewed diff across sections the requester never opened, and it is
   indistinguishable from your intended change in the same commit. Exception:
   a pre-existing token your new content also uses — say so explicitly, since
   fixing it necessarily repaints the old surfaces too.
5. **Validated categorical colors.** For N series/variants, assign a FIXED hue
   order (never cycle) and VALIDATE it colorblind-safe — don't eyeball. Use the
   `dataviz` skill's validator: `node scripts/validate_palette.js "#h1,#h2,#h3"
   --mode light` then `--mode dark`. Fix chroma/lightness/CVD FAILs. Resolve
   `var()` to hex for SVG `fill=`/`stroke=` **presentation attributes** (they are
   unreliable cross-browser) — keep `var()` only in CSS `style=` properties.
   Re-resolve on theme toggle by re-rendering the charts.
6. **Interactive by default.** Hover tooltips on every mark; sortable tables
   (click header); filters/steppers in a row above their chart. Visible keyboard
   focus; respect `prefers-reduced-motion`.
7. **Page-level navigation.** When the dashboard has four or more major
   sections, top-level tabs must switch one full content page/panel at a time.
   Do not stack every section into one long scrolling page. Keep the artifact
   self-contained: use in-document panels and preserve the selected page in the
   URL hash; nested tabs may switch views inside the active page. Write the hash
   with `history.replaceState`, never `location.hash =` — assigning the hash makes
   the browser jump to the panel element, so the header scrolls away on every tab
   click. Switching a tab must leave the scroll position where it was (and a
   deep-linked load should open at the top). Once the tab row holds ~5+ tabs of
   more than one kind (results vs. running record, say), wrap each kind in
   `<span class="tabgroup" role="presentation" data-glabel="…" style="--gc:var(--g-a)">`
   so the row reads as groups, not a flat list. Encode the group **three ways —
   label, divider, colour** — never colour alone, and take the hue from the
   group tokens (`--g-a` / `--g-b`), never from the categorical data palette
   (`--c-*`), which would imply a series relationship that does not exist.
8. **Show what has NOT run yet.** A results dashboard that only shows finished
   numbers hides the shape of the work. When a project has a backlog — planned
   experiments, open questions, follow-ups — ship the **plan pane**
   (`#pane-plan` + `planView('planTbl', rows)`): one row per item with **`task` /
   `goal` / status+date / cost / priority / evidence links**. Rows live in a JSON
   block, so adding an experiment is a data edit. Give every row a `goal` (the
   question it answers) — a task list without goals cannot be prioritised — and
   A row marked done or running MUST carry an evidence link — `planView` throws
   without one. A finished experiment with nothing to point at is an unbacked
   assertion, and those are exactly the rows a reader trusts most; the dash
   belongs only to work that has not run yet.
   Group the rows by **which claim they support** (`group` field renders a header
   row), not by tooling area: a backlog that lists only instrument work hides the
   fact that the argument has unsupported links. If a claim in your write-up has
   no row under it, that gap is the finding — surface it. Also
   link finished rows to the day they were worked on via
   `links:[{pane,date,label}]`, which switches to that pane and filters its
   calendar to that date. Keep done rows visible: the record of what was already
   settled is half the value.
9. **Data-driven narrative panes.** When a dashboard accumulates dated records,
   do NOT hand-write entries into HTML. Put them in one JSON file per pane and
   render notes and issues with ONE shared renderer, so a new record is a JSON
   edit + rebuild — never a code change. The Record group is **exactly three
   panes**: **실험 계획** (plan) · **실험 노트** (one decision-grade experiment per
   record) · **이슈 노트** (one defect per record). No fourth pane and no daily
   roll-up schema. Multiple records may share a date. The template gates the
   group to exactly `pane-plan` / `pane-notes` / `pane-issues`, with one matching
   panel each. **The mandatory status vocabularies, exact section orders,
   unknown-value rule, and complete JSON skeletons are in
   [`references/record-panes.md`](references/record-panes.md).** Read that contract
   before authoring either record; rendering mechanics are below.
   Keep canonical record pane IDs, section keys, and lifecycle status values
   stable; localize visible pane labels, filters, status chips, date helper copy,
   plan headers, and empty states through the template's `COPY` object. Use
   `COPY.record.sectionLabels` for displayed section headings and
   `COPY.record.statusLabels` for displayed lifecycle badges/filter chips.
10. **Notes are written by hand — render their markup.** Entry text, section
   headings, and table cells go through `mdN()`, which escapes first and *then*
   renders inline `**bold**`, `` `code` ``, and `*italic*`. Escaping first is the
   whole trick: the markers survive, but a tag the author typed stays inert text.
   Without this, an author writing emphasis sees literal asterisks on the page —
   and they will write them, because they are writing prose, not HTML.
   Set the type scale for reading, not for density: body copy ≥13.5px, notes and
   table cells ≥14px. A results page people actually read at arm's length is
   worth more than one that fits more rows.
11. **Conclusion first, always.** Every dated entry MUST carry a `key` — one
   sentence stating what it means, rendered at the top of the card above every
   section. `noteView` throws without it. Write the finding, not the activity:
   "the gain survives the clean slice at +61%, p=1e-4" — not "re-ran the eval".
   A log that opens with process forces every reader to reconstruct the point
   from the steps, and the entry that most needs a conclusion (a long debugging
   day) is exactly the one where nobody writes one. If an entry genuinely has no
   conclusion yet, say so in the `key` — "no verdict yet: the token-budget
   mismatch makes this table unreadable" is a conclusion, "TODO" is not.

12. **Frame the work before the numbers or unit cards.** The overview page opens
   with `data-component="framing"` rendered from `framingdata`: 3–6 filled cards
   describing the whole research/project context, not only the latest
   implementation work. Cover the unmet need, goal, prior baseline/work, gap,
   contribution, and any not-yet-claimed boundary. A metric or unit status a
   reader cannot place is not a result.

## Procedure

1. **Get the data into the right JSON shapes.** Compute once, in the task's own eval
   path (reuse existing metric functions so numbers MATCH the report — import
   them, don't reimplement). Save: (a) `framingdata` 3–6 scope cards, (b)
   numeric per-item `data` rows
   `[{id, <baseline>_metric, <variantA>_metric, ...}]` when the detail rows are
   samples/variants, (c) semantic `unitdata` rows when the detail rows are
   capabilities/research units/workstreams, and (d) optional media map
   `{id: {panelKey: dataURI, m: {…metrics}}}`. `unitdata` uses exactly
   `id`, `title`, `subtitle`, `status`, `summary`, `completion`, `evidence`,
   `next_gate`, `blockers`, `technical_ids`. `completion` may be a legacy number
   or string, or an object `{done,total,label}`; the object form renders a
   proportional meter and fails loudly unless `0 <= done <= total` and `total > 0`.
   At least one of `data` or `unitdata` must be non-empty.
2. **Pick forms by the data's job** (see `dataviz`): magnitude→bars,
   distribution→overlaid histograms/density, polarity/change→diverging delta,
   one headline→stat tile. Entity overview = table + bars (with a baseline
   reference line) for numeric `data`. Numeric detail = distribution +
   **delta-vs-baseline scatter** (each mark one item, sorted; above/below zero
   shows who helped/hurt) + table. Semantic unit detail = cards, not charts.
   Never keep a distribution, delta plot, or generic table when the fields are
   workstreams/capabilities and the marks would not mean anything.
3. **Media viewer (when items have images).** Self-contained artifacts can't
   lazy-load, so CURATE a representative subset (~12–36 items spanning the
   difficulty/metric range — e.g. evenly spaced by input difficulty), render each
   panel to a small grayscale/RGB PNG (256px, `optimize=True`), base64-embed.
   Panels share ONE display window per item so they're directly comparable.
   UI: prev/next stepper + a dropdown, N labeled panels side by side, per-panel
   metric readout, and an outline on the best panel. `m` is a free-form metric
   dict: a key matching a PANEL name renders under that panel, every other key
   renders once in the item readout — so panel labels are user-facing copy
   (translate them) and no metric is silently dropped. Budget: keep the whole file
   under ~5 MB (24 items × 5 panels × ~256px ≈ 3 MB). Say in the UI it's a subset.
4. **Build** from `assets/template.html` (in this skill dir) — swap the data,
   palette, columns, and `COPY`. The dashboard's selected language applies to
   every user-visible UI string and record sentence; preserve raw identifiers
   only for model names, dataset IDs, tool names, commands, paths, and run IDs.
   It already ships the tabbed shell (Overview /
   Detail / Samples with `role="tablist"`/`role="tab"`/`aria-selected` + URL-hash
   restore), KPI **tiles**, left-accent **callouts** (verdict + findings), filter
   **chips** + search over the per-item table, and a light/dark toggle — keep or
   drop panes to fit the data, don't rebuild the chrome. A **Components** tab ships
   a live style guide of every reusable component (tokens, typography, tiles,
   callouts, verdict, buttons, chips, role pills, presence/verification badges,
   delta/trend indicators, meters, status pills, inline code, table group-rows,
   collapsible) — consult it for what exists and copy the markup instead of
   inventing new components, then **delete that tab (its button + `#pane-kit`)
   before publishing**; it is a build-time reference, not results. Keep standalone
   running text ~65ch — but text INSIDE a full-width box (verdict banner, card
   `.foot`) must fill that box: a measure-capped paragraph in a wide card leaves a
   ragged column of dead space and reads as a broken line-break, not a readability
   choice. Widen `line-height` instead of capping the measure. `tabular-nums` on all
   figures; `overflow-x:auto` on wide tables so the body never scrolls sideways. A scrollable
   table's own box must be viewport-relative (`max-height:min(78vh,1100px)`), not a
   fixed few-hundred px — a short box turns a long table into a porthole.
5. **VERIFY before publishing** (the validator checks color, not layout):
   - Inject data, then assert every `<script type="application/json">` block
     `JSON.parse`s and no `__PLACEHOLDER__` markers remain.
   - Re-run the aggregation logic in `node` against the data and confirm the
     numbers match the source report (catches wrong-field/units bugs).
   - Render it: headless Chromium + console-error check if available
     (`playwright-core` + a cached chrome; check `ldd` for missing libs). Assert on
     the **post-JS DOM**, not the source: no page errors, no literal `**`/backticks
     in `document.body.innerText`, tabs switch, both themes apply, and
     `scrollWidth <= clientWidth` on `<html>`. A grep over the HTML file passes
     while the browser still shows asterisks — that is how the last five defects
     shipped. If the browser can't launch, fall back to a careful JS/HTML review +
     the JSON/number checks and SAY you couldn't render.
   - Extending someone's dashboard? Re-check the sections you did NOT touch still
     render and interact — and report, don't repair, any defect that predates your
     change (see non-negotiable 4).
6. **Publish.** Claude Code: `Artifact` tool with the file path (set `<title>`,
   a `favicon` emoji, a one-line `description`; republish the SAME path to keep
   the URL). Otherwise: write the `.html` and hand over the path. Persist a copy
   into the repo (e.g. `runs/<exp>/dashboard.html`) for durability.

## What goes in each record pane

**The canonical content contract is
[`references/record-panes.md`](references/record-panes.md) — read it before
writing any plan row, experiment note, or issue.** It defines the required
fields, lifecycle semantics, exact fixed sections, unknown-value rule, nested
legacy-source blocks, and complete copy-paste JSON skeletons.

| pane | one entry = | answers |
|---|---|---|
| **실험 계획** (`experiment_plan.json`) | one planned item, open or settled | what was/is planned, and why it matters |
| **실험 노트** (`lab_notebook.json`) | one experiment or measurement supporting a decision | what decision was tested, what happened, and what changes |
| **이슈 노트** (`issues.json`) | one defect or investigation | what failed, why, how it was addressed, and how closure was verified |

The contracts are mandatory:

- Experiment lifecycle: `예정 | 진행 중 | 완료 | 중단 | 보류`.
- Experiment sections, exactly once and in order: `Decision Question` →
  `Hypothesis` → `Run Identity` → `Live Snapshot` → `Results` →
  `Interpretation` → `Decision`.
- Issue lifecycle: `신규 | 조사 중 | 완화 | 모니터링 | 해결 | 차단`.
- Issue sections, exactly once and in order: `Impact` → `Observed Symptom` →
  `Evidence` → `Hypotheses` → `Root Cause` → `Resolution` → `Verification` →
  `Closure`.

Top-level lifecycle `status` is separate from experiment `Decision` and issue
`Closure`. Never omit a fixed section: use supported `미확정 — …` or
`해당 없음 — …` when a fact is unavailable, and never invent historical facts.
Exception: an issue with top-level `status: 해결` is a closure claim. Its
`Root Cause`, `Resolution`, `Verification`, and `Closure` sections must each
contain supported direct content and must not contain any unknown marker anywhere
(`미확정`, `해당 없음`, `확인 중`, `TODO`), even inside a contextual sentence. If
any of those facts are unavailable or not applicable, the issue is not `해결`;
use `모니터링`, `완화`, or `조사 중` instead.

## Dated narrative panes (실험 노트 + 이슈 노트 — only these two)

Results dashboards accumulate decision and defect records beside the numbers.
Ship them as **data-driven panes with a month calendar**, not hand-written HTML.

**Shape.** One JSON file per pane. Each record has
`{date,time?,status,title,key,sections}`; multiple records may share a date.
Experiment and issue records use the exact status and section contracts above —
there are no free-form top-level headings. A fixed section carries direct
`items`, `table`, and/or `images`; migrated source detail may be nested in
`blocks`:

```json
{"h":"Results","items":["summary"],"blocks":[
  {"h":"original heading","items":["original bullet"],
   "table":{"head":[],"rows":[]},"images":[],"collapsed":false}
]}
```

Every original migration block is preserved verbatim exactly once. New records
normally use direct content and do not need `blocks`. Complete valid experiment
and issue JSON skeletons live in `references/record-panes.md`; do not substitute
an abbreviated free-form example here.

Use `images` when the finding IS the picture — a before/after strip, a failure case, a severity ladder,
a synthetic-vs-real comparison. Panels lay out in the same wrapping `.panels` grid the media viewer uses
(one grid system per file) and scroll inside their own box, so a wide strip never scrolls the page.
`cap`/`sub` are prose and render markdown; `src`/`alt` land in attributes and are escaped.

**`src` MUST be a `data:` URI.** The artifact CSP blocks every external request, so a remote URL renders
*nothing* — no error, no broken icon, just an empty panel. Build it as
`"data:image/png;base64," + base64(png_bytes)`. Keep the payload sane: a note strip is a handful of
panels at a few hundred px, not a whole eval set (see the media-viewer budget below). A panel with no
`src` renders a labelled "missing src" placeholder rather than a broken-image glyph; an empty or missing
`images` array renders nothing at all rather than an empty box.

Every string a pane renders — titles, `key`, bullets, table headers AND table cells — goes through the
same markdown pass, so `**bold**` and `` `code` `` work identically everywhere. If one field renders the
literal asterisks, that field is escaping instead of formatting; fix the renderer, not the content.

This has now bitten three separate surfaces (note tables, overview tables, plan rows). When you add a
renderer, route every PROSE field through the markdown pass and check the RENDERED DOM, not the source:
a static grep over the HTML file passes while the browser still shows literal asterisks.

The same applies to any table helper you write for the overview panes: render markdown in cells, and
decide **by the cell's content** whether it is a figure (mono, tabular-nums, right-aligned via `.num`)
or prose (plain, left, top-aligned). Classifying by column INDEX — "everything after the first column is
a number" — breaks the moment a table carries a verdict or an explanation column, and it will.

**Never coin a term — in any language.** If the field has a word for it, use that word as the field
writes it (`held-out`, `floor`, `paired permutation`, `cluster bootstrap`, `ordinal`, `blind-gap`). If it
does NOT, describe the thing in a plain phrase instead of minting a label. Swapping an invented Korean
word for an invented English one fixes nothing — "무-관측 전략" and "no-look strategy" are both terms the
reader has never seen; "이미지를 보지 않는 전략" is just what it is. A coined label reads as a typo to
someone who knows the field and teaches a wrong word to someone who doesn't. Translate the explanation,
never the term — and when unsure whether a term is real, write the explanation.

`time` is optional `"HH:MM"` — when that entry was last updated. Entries sort newest-first by date THEN
time, so a same-day update lands above the entry it supersedes; an entry with no time sorts last within
its day. The stamp uses `.note-stamp`, never a bare `.pill`: `.pill` sets `color:#fff` and only its
modifier classes carry a background, so a bare one renders white-on-white and vanishes.

**One renderer, two pane contracts.** Use one
`noteView(listId, calId, filterId, data, {kind,statuses,sections})` for notes and
issues. The pane-specific contract validates lifecycle status, exact heading
order, meaningful content, and nested blocks before rendering. Same calendar and
card markup, zero duplication. Two dated panes is the whole set; the gate rejects
a third day-log/changelog pane.

**Where an entry lands** — see "What goes in each record pane" above. The plan uses
its own `planView` schema; notes and issues share the `noteView` dated-entry schema.
The content contract keeps their jobs distinct.

**Required component contract.** The dated-narrative pane in
`assets/template.html` is the dashboard component, not a suggestion. When a
dashboard has dated notes, issue logs, or lab records, retain its
`data-component="dated-narrative"` shell and call `noteView(...)`; it rejects
non-`YYYY-MM-DD` data or a missing calendar/filter/sticky-rail shell. Do not
replace it with a plain chronological card list. Empty data may hide the tab;
non-empty data must expose the tab and render the full component.

**Canonical visual form.** Use the template's RadClaw calendar unchanged: a
`230px` card rail at the right, `position:sticky; top:16px`, an 18px grid gap,
and an upper stacked rail below `820px`. It uses Korean month and weekday labels,
light accent blocks for dated entries, and a solid accent only for the selected
day. Keep the dated-entry count or helper copy inside the left grid column so the
calendar starts one row above the first note card. Do not add calendar dots, a
wider gutter rail, or alternate breakpoint behavior.

**Calendar navigation** (the part that makes a long log usable):
- Month grid; days **with an entry** are highlighted (weight + accent surface)
  and clickable; empty days are `disabled`, so the highlight is not carried by
  colour alone. Clicking filters to that day and shows a "N entries · show all"
  line; clicking again clears.
- `‹ ›` step months. Open on the newest entry's month, entries newest-first.
- Place it in the **right margin, `position:sticky`** so it follows the scroll —
  NOT `position:fixed` (fixed feels pinned/detached), and NOT `absolute` (scrolls
  away); stack it above the list on narrow screens.
- Add a **back-to-top** button (appears past ~400px scroll) — dated panes get long.

**Reference material never creates an extra top-level heading.** Put commands,
raw configs, long provenance, or migrated source sections under the appropriate
fixed section. Preserved legacy material uses a nested block with
`collapsed:true` when it should render in `<details>`; the seven/eight fixed
parent sections remain visible.

**The renderer is `noteView` in `assets/template.html` — read it there, don't
re-derive it.** This section used to carry a sketch of it; the sketch drifted
(it escaped the fields the real renderer formats, used class names the template
does not have, and omitted the required `key`), and a sketch that disagrees with
the shipped code teaches the bug. Extend `noteView`; do not fork it.

Keep dates as `YYYY-MM-DD` strings and build the grid with `Date.UTC` (local-time
`new Date("YYYY-MM-DD")` shifts the day across timezones).

## Anti-patterns

- Fetching data/fonts/images at runtime (breaks CSP/offline). Inline everything.
- Dual-axis charts; rainbow sequential ramps; a hue at a diverging midpoint.
- Cycling categorical hues past the fixed set (9th series → "Other"/small-multiples).
- Coloring by rank instead of entity (a filter must not repaint survivors).
- Embedding all 300+ items' full-res images (multi-hundred-MB, unusable) — curate.
- An overview that opens straight on tiles and tables, with the goal, prior work,
  gap, and contribution left to the reader to reconstruct — fill the framing cards.
- A framing section that describes only today's implementation work instead of
  the whole research/project need, baseline, gap, and contribution.
- Copy-pasting numeric detail charts onto workstreams/capabilities. A
  distribution over "implementation units" or a fake delta chart is worse than
  no chart; use semantic unit cards.
- Translating some UI chrome while leaving tabs, filters, record helper text,
  displayed record section headings/statuses, or plan headers in another
  language. Localize through `COPY`, especially
  `COPY.record.sectionLabels`/`COPY.record.statusLabels`.
- Faking a difference on a null result via a deceptively zoomed/truncated axis
  with no "near-identical" note.
- Right-aligning or monospacing a table column because of its POSITION rather than its
  content — a prose column then renders as a ragged mono block.
- Escaping one field while formatting the others (table cells vs bullets) — `**0.694**`
  then renders its asterisks and looks like a broken value.
- Coining a label — a literal translation of an existing term, OR a new name for something
  the field never named. When no established term exists, describe it in plain words.
- A day-log pane or daily roll-up schema beside the experiment records. The same
  run then gets written twice and drifts; write one decision-grade experiment
  record, and allow multiple records to share the date.
- Aggregating multiple defects into one issue entry. Each defect has its own
  lifecycle, root-cause evidence, verification, and closure record.
- Letting issue records go stale while experiments move — check both panes before
  publishing; unresolved defects do not disappear because a newer date exists.
- Marking an issue `해결` while `Root Cause`, `Resolution`, `Verification`, or
  `Closure` contains `미확정`, `해당 없음`, `확인 중`, or `TODO` anywhere. A
  resolved issue cannot carry unknown/not-applicable closure evidence; choose
  `모니터링`, `완화`, or `조사 중` instead.
- A measure-capped (`max-width: NNch`) paragraph inside a full-width card — the text
  stops mid-box and looks like a rendering bug. Cap the CARD or fill the box.
- Numbers wearing series color; a number on every point instead of selective labels.
- Hand-writing each dated entry into the HTML (every new note becomes a code edit,
  and the panes drift apart) — one JSON per pane + one shared renderer instead.
- Replacing the dated-narrative component with a bare note list — preserve the
  calendar, highlighted entry days, day filter, sticky rail, and back-to-top control.
- A sidebar calendar that is `fixed` (pinned, detached from content) or `absolute`
  (scrolls out of view) — use `sticky`.
- Interpolating a value into an ATTRIBUTE or a URL without escaping (`alt="${key}"`,
  `<option value="${k}">`, `src="${uri}"`) — one quote in a label and the tag is
  destroyed. Prose gets the markdown pass, attributes get the escape pass, and
  anything arriving from a data block is never trusted as HTML.
- Documenting an injection marker (`/*__DATA__*/`) the file does not contain — a
  builder's replace silently no-ops and the DEMO numbers ship as results.
- Dumping raw queries/configs/provenance inline — collapse them (`<details>`).
- Putting a date in a tab label (`Issue Log · 2026-07-23`) once the pane holds
  many days — the calendar carries the date, the tab names the kind.

## Files
- `assets/template.html` — a token-themed, tabbed two-altitude skeleton. Ships
  the **plan pane** (`#pane-plan`, `planView`) and cross-pane note links
  (`data-note-link="pane:YYYY-MM-DD"`) alongside the dated-narrative component. Header
  (eyebrow/title/lede/meta-row) + verdict callout, then tabs: **Overview**
  (framing cards for whole-project need/goal/prior baseline/gap/contribution —
  then KPI tiles, summary table, entity bar charts, findings callouts when
  numeric data exists), **Detail** (semantic unit/workstream cards when
  `unitdata` is non-empty; numeric distributions, delta-vs-baseline scatter, and
  chip/search-filtered sortable table when `data` is non-empty), **Samples**
  (media viewer, auto-hidden if `imgdata` is empty),
  and **Components** (a live design-kit reference — consult when building, delete
  before publishing). Hover tooltips, working light/dark toggle, URL-hash tab
  restore. Replace the CONTENTS of the `framingdata` / `unitdata` / `data` /
  `imgdata` JSON blocks (there are no injection markers — see the anti-pattern) and the
  `VARS`/`METRICS`/`TILES`/`COPY`. Bad numeric data fails loudly: a missing
  or non-finite `<var>_<metric>` field, or a baseline present on only some rows
  throws on load naming the row and field, rather than rendering `NaN`. Unit-only
  dashboards may leave `data` empty, but then `unitdata` must be non-empty.
  The plan, notes, and issues panes already ship with their JSON blocks and renderer
  calls: populate them; do not duplicate their shells. The closing gate rejects a
  fourth Record tab, duplicate/missing panels, and malformed dated entries. See
  "Dated narrative panes".
- `references/record-panes.md` — the per-tab content template for the three record
  panes (실험 계획 / 실험 노트 / 이슈 노트): what one entry is, required fields, the
  fixed section order, copy-paste JSON skeletons, anti-patterns. Read it before
  writing an entry; the template only gates the mechanics, this is the content.
- Palette validator lives in the `dataviz` skill: `scripts/validate_palette.js`.
