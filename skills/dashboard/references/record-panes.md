# Record panes — mandatory content contracts

The Record group is **exactly three panes**:

| pane | id | data | one entry = | answers |
|---|---|---|---|---|
| **실험 계획** / plan | `#pane-plan` | `experiment_plan.json` | one planned work item, open or settled | what was/is planned, and why it matters |
| **실험 노트** / notes | `#pane-notes` | `lab_notebook.json` | one experiment or measurement supporting a decision | what decision was tested, what happened, and what changes |
| **이슈 노트** / issues | `#pane-issues` | `issues.json` | one defect or investigation | what failed, why, how it was addressed, and how closure was verified |

No fourth pane. The plan has its own `planView`; notes and issues share the dated-card renderer but have different mandatory lifecycle vocabularies and fixed section orders. A date may contain multiple experiment or issue records.

Canonical IDs, fixed section keys, and lifecycle status values stay exactly as
written here, even when the dashboard language changes. Localize only visible UI
through `COPY`: tab labels, tab-group labels, plan table headers, filter labels,
status chip labels/count labels, month navigation labels, selected-date helper
text, empty-state text, and viewer/helper copy. Record JSON section headings
remain canonical (`Decision Question`, `Hypothesis`, …; `Impact`,
`Observed Symptom`, …) so validators and cross-pane links do not drift. Display
translated record section headings through `COPY.record.sectionLabels` and
translated lifecycle badges/filter chips through `COPY.record.statusLabels`.

Every dated record uses the top-level envelope:

```json
{"date":"YYYY-MM-DD","time":"HH:MM","status":"pane-specific lifecycle state","title":"finding or issue","key":"one-sentence conclusion/current state","sections":[]}
```

`time` is optional. `status`, `title`, `key`, and every fixed section are required. The renderer must reject an unknown status, duplicate/missing/out-of-order heading, or empty section.

`status` values in JSON remain the pane-specific vocabularies below. If the
dashboard is in another language, translate visible badge text only if validation
still checks these canonical values; do not rewrite record data into a
display-only vocabulary.

---

## 실험 계획 / plan — the backlog

One row per planned item, whether `todo`, `running`, `done`, or `blocked`; finished rows stay because they record what is already settled.

| field | rule |
|---|---|
| `group` | which **claim** the row supports, not which tool it touches |
| `task` | the work itself |
| `goal` | the question it answers |
| `status` + `date` | `todo` / `running` / `done` / `blocked`, and when |
| `cost` | GPU-hours, wall-clock, money, or another real prioritisation cost |
| `priority` | P0/P1/P2 |
| `note` | optional short result or caveat shown under `task` |
| `links` | evidence. Required for `done` and `running`; every target must resolve to a real date in `pane-notes` or `pane-issues`. |

Visible plan labels are not part of the JSON contract. `task`, `goal`, `status`,
`cost`, `priority`, and `links` remain canonical field names; rendered column
headers and lifecycle labels come from `COPY.plan`.

```json
[
  {
    "group":"claim ②: the gain is image-grounded",
    "task":"seed repeat (GRPO x3)",
    "goal":"is the arm gap larger than seed noise (+-0.044)?",
    "status":"running",
    "date":"2026-07-29",
    "cost":"~6 GPU-h",
    "priority":"P0",
    "links":[{"pane":"pane-notes","date":"2026-07-28","label":"single-seed result"}]
  }
]
```

`예정` in an experiment note is a preregistered decision record linked from a plan row; it does not replace that plan row.

---

## 실험 노트 / notes — decision-grade experiment records

### Lifecycle status — exact vocabulary

`예정 | 진행 중 | 완료 | 중단 | 보류`

| status | mandatory meaning |
|---|---|
| `예정` | Decision Question, Hypothesis, and success/stop/promotion criteria are preregistered; execution has not started. |
| `진행 중` | A live process is confirmed by process/GPU/log evidence and `Live Snapshot` is current. |
| `완료` | Process termination, results, and promised artifact existence are verified. |
| `중단` | The run was intentionally stopped; reason, retained artifacts, and resume/restart condition are recorded. |
| `보류` | Execution or interpretation cannot proceed because a named external dependency or prerequisite is unresolved. |

Lifecycle `status` is not the experiment conclusion. A record can be `status: 완료` while its `Decision` is `추가 검증`.

### Fixed sections — exactly once and in this order

1. **Decision Question** — decision supported; success, stop, and promotion criteria.
2. **Hypothesis** — expected result; falsification condition; comparison baseline; floor/trivial baseline where applicable.
3. **Run Identity** — run ID, code/data versions, environment, seed, resolved settings, exact command, log/checkpoint paths.
4. **Live Snapshot** — observation time, phase/progress, PID/GPU/OOM/watchdog state, completed and remaining work. For a completed historical record with no live evidence, state why it is `해당 없음`; do not invent it.
5. **Results** — primary metrics, baseline change, FP/FN and subgroups, parse/completion rate, valid sample count, failure cases, and verified artifact status.
6. **Interpretation** — confirmed facts, inferences, counter-interpretations/confounders, and what the experiment does not show.
7. **Decision** — `채택 / 기각 / 보류 / 추가 검증`, why it is or is not final, and exactly one next experiment.

`title` states the finding or decision question, not the activity. `key` is the current one-sentence conclusion and is rendered before every section.

### Complete JSON skeleton

```json
[
  {
    "date":"2026-07-30",
    "time":"14:20",
    "status":"완료",
    "title":"type reward improves held-out type accuracy beyond the measured floor",
    "key":"The completed run improved type accuracy from 0.367 to 0.551, but one seed is insufficient for promotion.",
    "sections":[
      {
        "h":"Decision Question",
        "items":[
          "Decision: promote the type reward into the combined objective or reject it.",
          "Success criterion: held-out type accuracy exceeds the 0.329 floor and zero-shot baseline.",
          "Stop criterion: parse rate below 0.95 or a preflight contract failure.",
          "Promotion criterion: positive paired effect with no material IoU regression."
        ]
      },
      {
        "h":"Hypothesis",
        "items":[
          "Expected: type reward increases type accuracy relative to the same-seed IoU-only arm.",
          "Falsified if the paired effect is non-positive.",
          "Baseline: zero-shot 0.367; trivial floor: 0.329."
        ]
      },
      {
        "h":"Run Identity",
        "items":[
          "run_id: `type-arm-seed42`; code: `abc123`; data: `ca_synthmask_mix_v2`.",
          "environment: Python 3.12, seed 42, LoRA r16.",
          "command: `python train.py experiment=type_arm seed=42`.",
          "log: `runs/type-arm-seed42/train.log`; checkpoint: `runs/type-arm-seed42/checkpoint-520`."
        ]
      },
      {
        "h":"Live Snapshot",
        "items":[
          "Observed 2026-07-30 14:20 after process exit 0.",
          "520/520 steps complete; no OOM or watchdog intervention.",
          "Evaluation and artifact checks complete; remaining work: none for this run."
        ]
      },
      {
        "h":"Results",
        "table":{
          "head":["arm","valid n","parse rate","type accuracy"],
          "rows":[
            ["trivial floor","49","1.00","0.329"],
            ["zero-shot","49","1.00","0.367"],
            ["type reward","49","1.00","0.551"]
          ]
        },
        "items":["Checkpoint and evaluation dump exist at the recorded paths."]
      },
      {
        "h":"Interpretation",
        "items":[
          "Confirmed: the measured type score increased beyond the floor and baseline.",
          "Inference: the type channel contributes signal not supplied by IoU alone.",
          "Counter-interpretation: one seed may overstate the effect.",
          "Does not show: cross-model or clinical generalisation."
        ]
      },
      {
        "h":"Decision",
        "items":[
          "추가 검증 — do not promote from one seed.",
          "Next experiment: repeat the identical comparison over three preregistered seeds."
        ]
      }
    ]
  }
]
```

---

## 이슈 노트 / issues — one defect per record

### Lifecycle status — exact vocabulary

`신규 | 조사 중 | 완화 | 모니터링 | 해결 | 차단`

| status | mandatory meaning |
|---|---|
| `신규` | Evidence was received; investigation has not started. |
| `조사 중` | Discriminating checks are being run. |
| `완화` | A temporary mitigation reduces impact; the structural cause remains. |
| `모니터링` | A fix was applied; recurrence and downstream progress are under observation. |
| `해결` | Root cause, permanent fix, original symptom removal, normal progress, and final artifact completion are verified. |
| `차단` | Investigation cannot continue because of a named external resource, permission, or dependency. |

Lifecycle `status` is not issue disposition. An issue can be `status: 모니터링` while `Closure` says the permanent resolution is not yet verified. `완화` must never be reported as `해결`.

High-visibility closure rule: an issue with top-level `status: 해결` is claiming
verified closure. `Root Cause`, `Resolution`, `Verification`, and `Closure` must
each contain supported direct content and must not contain any unknown marker
anywhere: `미확정`, `해당 없음`, `확인 중`, or `TODO`. This includes contextual
sentences such as “해당 없음 — no rollback needed”; the marker still makes the
resolved record invalid. If any of those four sections need an unknown or
not-applicable marker, use `모니터링`, `완화`, or `조사 중` instead of `해결`.

### Fixed sections — exactly once and in this order

1. **Impact** — affected experiments/users/artifacts, urgency, workaround availability.
2. **Observed Symptom** — observation/time, verbatim error, expected versus actual behavior.
3. **Evidence** — logs/reproduction command, process/GPU state, last known-good point, dashboard versus actual state.
4. **Hypotheses** — candidate causes, supporting/refuting evidence, highest-information next check.
5. **Root Cause** — direct cause, structural cause, why monitoring/tests missed it.
6. **Resolution** — applied change, temporary versus permanent status, rollback method.
7. **Verification** — original symptom removal, normal progress, final artifact, recurrence-monitoring condition.
8. **Closure** — `해결 / 모니터링 / 미해결`, follow-up/owner, and reopen condition.

### Complete JSON skeleton

```json
[
  {
    "date":"2026-07-30",
    "time":"15:10",
    "status":"조사 중",
    "title":"training log stopped while the GPU process remained alive",
    "key":"No progress has occurred since step 420; OOM and disk exhaustion are excluded, but root cause is not established.",
    "sections":[
      {
        "h":"Impact",
        "items":[
          "Affected: `motion-seed42`, its checkpoint schedule, and the dependent evaluation.",
          "Urgency: P0 because the GPU remains allocated.",
          "Workaround: stop and resume from checkpoint-400 after preserving logs."
        ]
      },
      {
        "h":"Observed Symptom",
        "items":[
          "Observed 2026-07-30 15:10: train.log has no new step after 420 for 18 minutes.",
          "Verbatim error: 해당 없음 — no exception was emitted.",
          "Expected: one step every 7–9 seconds; actual: process alive with no log or checkpoint progress."
        ]
      },
      {
        "h":"Evidence",
        "items":[
          "Reproduce/check: `python scripts/check_progress.py runs/motion-seed42`.",
          "PID 18422 alive; GPU memory allocated; utilization 0%; no OOM event.",
          "Last known-good: checkpoint-400; dashboard still displays 진행 중, matching process state but not progress."
        ]
      },
      {
        "h":"Hypotheses",
        "items":[
          "Dataloader deadlock — supported by zero GPU utilization; not yet reproduced.",
          "GPU OOM — refuted by process state and absence of OOM logs.",
          "Disk full — refuted by 1.2 TB free.",
          "Next discriminating check: resume checkpoint-400 with dataloader workers set to 0."
        ]
      },
      {
        "h":"Root Cause",
        "items":[
          "미확정 — available evidence does not yet distinguish a worker deadlock from an upstream read stall.",
          "Why monitoring missed it: watchdog checks process existence, not step-age progress."
        ]
      },
      {
        "h":"Resolution",
        "items":[
          "Applied change: 해당 없음 — investigation is still in progress.",
          "Temporary mitigation: preserve logs and stop the idle process if the workers=0 check reproduces normal progress.",
          "Rollback: restart from checkpoint-400 with the original worker count."
        ]
      },
      {
        "h":"Verification",
        "items":[
          "Original symptom removed: 미확정 — no fix has been applied.",
          "Normal progress and final artifact: 미확정.",
          "Monitoring condition: alert when step age exceeds five expected intervals."
        ]
      },
      {
        "h":"Closure",
        "items":[
          "미해결 — root cause and permanent fix are not verified.",
          "Owner: training operator; follow-up: run the workers=0 discriminating check.",
          "Reopen condition: 해당 없음 — the issue is already open."
        ]
      }
    ]
  }
]
```

---

## Fixed-section unknown / not-applicable rule

A fixed section is never omitted. Missing historical or current facts must be explicit:

- `미확정 —` followed by existing evidence, eliminated hypotheses, or the next discriminating check.
- `해당 없음 —` followed by the concrete reason it does not apply.

A bare `미확정`, `해당 없음`, `확인 중`, or `TODO` is not meaningful content. Do not reconstruct missing success criteria, causes, live state, or verification after the fact.

Example:

```json
{"h":"Root Cause","items":[
  "미확정 — GPU OOM and disk exhaustion are excluded.",
  "Next discriminating check: resume the same checkpoint with dataloader workers set to 0."
]}
```

---

## Nested `blocks` — legacy source preservation

During migration, every original legacy section is copied **verbatim and exactly once** into one fixed V2 section's `blocks` array. Preserve its heading, bullets, table, images, `collapsed` value, and any other original payload. Generated V2 summary content stays in the parent section.

```json
{
  "h":"Results",
  "items":["summary derived only from recorded evidence"],
  "blocks":[
    {
      "h":"original heading",
      "items":["original bullet"],
      "table":{"head":[],"rows":[]},
      "images":[],
      "collapsed":false
    }
  ]
}
```

`blocks` are for preserved source detail, not extra top-level sections. New records normally write direct `items`, `table`, and `images` and do not need `blocks`.

### Legacy migration context only

Legacy experiment headings such as `Design`, `Result`, `Test`, `Verdict`, `What this does NOT show`, and `Decision / Next`, and aggregated daily issue sections prefixed `[해결]`/`[미해결]`/`[차단]`, are **source formats to migrate, not current authoring templates**. Copy each original section into exactly one V2 parent `blocks` array; split each legacy issue section into its own V2 issue record while retaining the source date. Never silently drop or rewrite a source block.

---

## Anti-patterns

- Omitting or reordering a fixed section.
- Using a status outside the pane-specific vocabulary.
- Treating experiment `Decision` or issue `Closure` as the lifecycle `status`.
- Calling a temporary mitigation `해결`.
- Marking an issue `해결` while `Root Cause`, `Resolution`, `Verification`, or
  `Closure` contains `미확정`, `해당 없음`, `확인 중`, or `TODO` anywhere.
- Inventing missing historical criteria, root causes, or verification.
- Writing a bare `미확정`, `해당 없음`, `확인 중`, or `TODO` with no reason/evidence/next check.
- Aggregating multiple defects into one issue record.
- Adding a day-log pane beside the experiment log.
- Hand-writing entries into HTML instead of the pane JSON.
- Putting dates in tab labels; the calendar carries dates.
- Renaming canonical section keys or lifecycle status values to match the UI
  language. Translate visible labels through `COPY.record.sectionLabels` and
  `COPY.record.statusLabels`; keep JSON values stable for validation.
- Localizing only the tab captions while leaving filters, status helpers, empty
  states, plan headers, or viewer copy in the template's default language.
- Losing, duplicating, summarising away, or altering a legacy source block during migration.
