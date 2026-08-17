# Skill evaluation rubric — `making-conference-posters`

A skill document is loaded into an agent's context before it works. Its cost is context; its value is
preventing specific failures. Score it on the poster it produces, in this priority order:

| Tier | What it asks | Weight per criterion | Why it ranks here |
|---|---|---|---|
| **A. Template fidelity** | Did the poster come out as the template's design, or a dialect of it? | ×3 | A poster that drifts is not this lab's poster. Drift is invisible to every geometric check, so nothing else catches it. |
| **B. Content fidelity** | Is the source's content on it, correctly and completely? | ×2 | Assumed. The reason the poster exists. |
| **C. No filler** | Is anything on it that earns nothing? | ×1 | Real, but it costs a line, not the poster. |

**How to score.** 1–5 against the anchors, from **evidence produced during this scoring run** — a command run
and its output inspected — not from reading the prose. Rescore after any substantive edit and after any run;
several criteria can only move by use.

---

## A. Template fidelity — first priority (×3)

| # | Criterion | Anchors |
|---|---|---|
| A1 | **Does the skill force adherence?** | 1: no rule. 3: a rule in prose. 5: adherence is the path of least resistance — the value exists in one declared place and the doc routes every use through it. |
| A2 | **Is the template itself compliant?** | 1: copying the template starts you in violation of the doc. 3: minor divergence. 5: zero inline sizes or spacing literals used more than once, verified by grep. |
| A3 | **Does adherence survive format change?** | 1: holds only at the native sheet. 3: holds at other sheets with hand-tuning. 5: sheet size, orientation and column count are parameters; no format needs CSS the template does not provide. |
| A4 | **Is drift mechanically detected?** | 1: prose only. 3: a grep the agent must remember to run. 5: a command fails on a value that is not a declared template value, and the gate has been shown a drifted poster and observed to fire. |

## B. Content fidelity — middle (×2)

| # | Criterion | Anchors |
|---|---|---|
| B1 | **Source terminology preserved** | 1: paraphrase unchecked. 3: a check that can be fooled. 5: terms extracted before writing, and verified by a check that cannot pass on a near-miss. |
| B2 | **Numbers, scope and qualifiers correct** | 1: no rule. 3: digits checked, quantifiers not. 5: quantifiers, domain qualifiers and the qualifier attached to every number are checked against the source. |
| B3 | **Nothing invented** | 1: reviewer opinion allowed onto the poster. 3: a boundary stated once. 5: the boundary is stated, the legitimate/not-yours distinction is worked, and no rule elsewhere contradicts it. |
| B4 | **Nothing important lost** | 1: no rule. 3: "select fewer sentences" with no check. 5: a check that the poster carries the source's headline result, its cost, and the metric where it loses. |

## C. No filler — last (×1)

| # | Criterion | Anchors |
|---|---|---|
| C1 | **No pointers to material the reader cannot reach** | 1: no rule. 3: named as a smell. 5: a rule that separates a disclosure (keep) from a direction (cut), with the test stated. |
| C2 | **Space filled with content, not decoration** | 1: padding and type used as spacers. 3: forbidden in prose. 5: forbidden, with a fix order that puts missing source floats first and the global type knob last. |

## Enablers (×1) — these do not score the poster, they score whether the doc can be trusted

| # | Criterion | Anchors |
|---|---|---|
| E1 | Claim correctness | 5: every claim about a script, flag, exit code or template declaration checked against the file. |
| E2 | Internal consistency | 5: no contradiction found by a full read *and* by a reviewer who did not write it. |
| E3 | Verified by use | 5: run end to end at multiple configurations by parties who did not write it. |
| E4 | Findability | 5: rules grouped by the phase where they bite, not one flat list. |
| E5 | Context economy | 5: no rule has two homes; no passage without a check. |

Max raw: A 4×5×3 = 60 · B 4×5×2 = 40 · C 2×5×1 = 10 · E 5×5×1 = 25 → **135**

---

## Current score

Scored after: the source-fidelity rewrite, two independent audits and their fixes, one solo dry run, a six-arm
multi-format stress test run by parties who did not write the doc, and the subsequent A0-only scoping.

**6.4 / 10 (raw 87/135).** Per-criterion: A1 4 · A2 3 · A3 2 · A4 3 · B1 2 · B2 4 · B3 5 · B4 2 · C1 5 · C2 5 ·
E1 3 · E2 3 · E3 4 · E4 2 · E5 3.

The score fell from a self-scored 6.7 because a second reader priced in three things the author's own scoring
missed: this session's edits **added** a check that was broken against the skill's own template (a numbering
grep whose pattern silently dropped every table), **doubled down** on a check already known to return false
zeros (making an un-normalised grep authoritative), and **invalidated** the one multi-format verification by
changing the footer geometry after the arms had run.

Movements worth recording:

- **A3 (2)** — measured, not assumed. Design held with zero hand-tuning at 3 of 6 formats. The two sheets that
  failed outright have since been removed from the skill's scope, which narrows the claim rather than fixing
  the cause: 4 columns still clips the banner at A0, silently, and is no longer advertised.
- **A4 (3)** — up from 2. The rule is now a grep the agent is told to run, which is exactly anchor 3. No gate,
  so no higher. The implementable design and its broken case (the template's own `<sub>`) are named below.
- **B1 (2)** — down from 3. The check has a confirmed false-zero mode on wrapped and hyphenated source text,
  reproduced independently in 4 of 6 arms and again by the second audit. Step 2 now normalises before grepping
  and a zero is no longer actionable on its own; scored at the state that shipped, not the intent.
- **E3 (4)** — six independent arms did run, but the shipped artifact diverged from the verified one. The
  footer change has since been re-verified in both orientations (portrait 63.70 cm, landscape 90.06 cm, both
  75.7% of the sheet; landscape audits clean and exports at the correct size with no Type 3).
- **C1 (5)** — up from 4; the disclosure-vs-direction rule meets its own anchor verbatim.

## Ranked actions

1. **A4 — build the conformance gate** (`audit_fit.py`). Collect the declared `font-size` and length values from
   the live stylesheet, walk computed styles, and fail on any value that is neither declared, inherited, nor a
   declared relative factor. The broken case is the shipped template: `<sub>` has no rule, so it resolves to
   sizes matching no class. Prove the gate on that before fixing it.
2. **Close the two audit blind spots.** `clip-path` removes ink without touching any scroll metric — the largest
   type on the sheet can be decapitated with no line printed. And the dead-space loop already computes
   `inner - lowest` and discards the negative case, which is the overflow-into-padding band.
3. **`--scan-scale` is unsound three ways** — its fit predicate is decoupled from the clipping tolerance, its
   `LO=0.80` floor can return a scale below the doc's own 24 pt type floor, and when nothing fits it prints a
   measurement taken at `--s 1` in a block indistinguishable from a real audit.
4. **B4 — a completeness check.** Nothing verifies the poster carries the source's headline result, its stated
   cost, or the metric where a baseline wins.
5. **Template one-liners** — `gap:0.28cm` inline duplicating `--gap-cap`; no `sub` rule; no table primitive
   although the doc says to prefer native re-typesetting over capturing an image.
6. **E4 — group the trap table by phase.** Still the cheapest win; still 25 rows in one flat list.

## Ceiling

A3, A4, E2 and E3 cannot reach 5 from self-review. A4 needs code. The rest need a reader and a runner who did
not write the document — the contradictions found so far were introduced and read past by the same person in
the same session.
