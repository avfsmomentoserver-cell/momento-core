# V6 Handover Workflow

## Description
What to do after the tests pass. This workflow takes over from the chat session
that scaffolded the research suite and CI, and carries V6 from "green pipeline"
to "measured platform".

## Trigger
- `/v6`
- `/v6 handover`
- `/v6 report`
- `/v6 next`

## Coordinator
ag_admin

## Specialists
ag_forecast, ag_backend, ag_qa, ag_devops, ag_docs

## Prerequisite skills
1. `statistical-honesty` — **read first, always**
2. `research-suite`
3. `debian-local-dev`

---

## Context: where the work stands

| Item | State |
|---|---|
| Research suite (`backend/research/`) | Written, **not yet executed** |
| CI pipeline | Written, **never run** — zero pipelines in project history |
| Local Debian harness (`Makefile`) | Written, not verified |
| CUDA blocker | Removed for CI and research; API server split still pending |
| Measured house edge `c` | **Unknown** — blocks #11, #12, #14 |
| Lexicon governance | Specified (#9), not built |
| Work items | #7 through #19 created |

Open MRs: !3 (research suite), !5 (CI + Makefile).

---

## Phase 1 — Verify and merge

**Owner**: ag_devops, ag_qa

```bash
make venv && make verify
```

Neither MR has been executed, so expect a plumbing bug on first run. The
statistics were written carefully; the wiring was not tested.

Most likely failures, in order:

1. `ruff check` finds pre-existing issues → `make fmt`, then narrow `select` in
   `pyproject.toml` rather than widening the MR's scope
2. Import error in `backend/research/` → fix in place on the !3 branch
3. A metric assertion off by a rounding tolerance → fix the test, not the metric,
   after confirming the metric is right

**Merge order is not optional:**

1. **!3 first.** `pyproject.toml` in !5 collects `test_research_*.py`, which only
   exists in !3. Merging !5 alone yields a green pipeline that ran zero tests —
   the worst possible outcome, because it looks like success.
2. **!5 second.**
3. Confirm green on `main`.

**Exit criteria**: `make verify` passes locally; pipeline green on `main`.

---

## Phase 2 — Produce research report 001

**Owner**: ag_forecast

The single most important step in V6.

```bash
make research CSV=clean_data.csv PERMUTATIONS=200
```

This produces the measured `c` (house edge) that #12 (ETA), #11 (orchestrator)
and #14 (promo EV) all depend on. Until it runs, those three are built on an
assumption.

```bash
mkdir -p research/reports
cp research-report.json research/reports/001-baseline-clean-data.json
git add research/reports/001-baseline-clean-data.json
git commit -m "research: report 001, baseline on clean_data.csv"
```

Also run the data audit, because G1 gates G3 — missingness biases the edge
estimate:

```bash
make audit CSV=clean_data.csv
```

### Interpreting it

| Observation | Meaning | Action |
|---|---|---|
| `skill ~ 0`, CI spans zero | **Expected and correct** | Record. Do not tune |
| Permutation percentile < 95 | No structure beyond shuffle | **Pass.** Proceed |
| Permutation percentile > 95 | Suspicious | Audit for data defects **first** |
| `c` materially off 0.97 | Interesting | Check missingness before believing it |
| Flat `dry_streak` table | Gambler's fallacy falsified | Record as a finding |
| `duplicates_removed > 0` | Cleaning missed the defect | Re-clean on 50 ms window, not ID |

**Do not iterate on a null.** See statistical-honesty Rule 3. A well-measured
null is the deliverable that makes every later claim trustworthy.

**Exit criteria**: report 001 committed; `c` known with a CI; missingness rate
known.

---

## Phase 3 — Finish removing the blocker

**Owner**: ag_devops, ag_backend

CI and research are unblocked, but `backend/requirements.txt` still can't install
on a GPU-less box, so the API server won't start on the VM.

1. Create `backend/requirements-api.txt` — FastAPI, uvicorn, pydantic, auth,
   slowapi, pyotp. No torch, tensorrt or cupy.
2. Create `backend/requirements-gpu.txt` — the GPU stack, installed only on a GPU
   host.
3. Verify the GPU modules degrade gracefully when absent.
   `gpu_intelligence/device_manager.py` exists for this; confirm the import path
   tolerates missing CUDA.
4. **Add a test asserting it.** Graceful degradation that isn't tested is an
   assumption.
5. `make dev` starts API and web on the VM.

**Exit criteria**: API server runs on a 2 vCPU no-GPU VM; a test proves the GPU
path degrades.

---

## Phase 4 — Contracts, then lexicon

**Owner**: ag_arch, ag_backend

**#8 contracts first.** Every other boundary derives from it.

- `round.schema.json` — `id`, `ts`, `multiplier`, `source`. Nothing else.
  `Points`, `Band` and `Color` belong in a presentation schema, never here.
- `event.schema.json` — CloudEvents shape as plain JSON over the existing hub
- `lexicon-term.schema.json`
- `openapi.yaml`
- CI gate on backward-incompatible changes

**#9 lexicon second.** The keystone invention. Each term becomes a record with a
predicate, support count, skill score, CI and `status`. Phrases compose:
`dry_phase AND crosses(2x) AND farming` is itself a term with its own measured
support. New terms default to `DESCRIPTIVE`; promotion requires a linked report.

**#16 third.** Pre-registration hashing, the report registry, the leakage
firewall as an assertion with a deliberate leak-injection test.

**Exit criteria**: contracts versioned with a compat gate; lexicon loads with
every term carrying a status; promotion impossible without a report ID.

---

## Phase 5 — Inventions and products

Parallel, behind the contracts.

| Issue | Owner | Note |
|---|---|---|
| #12 ETA | ag_forecast | Geometric baseline is closed-form and already correct. Ship the calibrated distribution, not a countdown |
| #13 DNA + pressure | ag_forecast | **Highest risk of false discovery.** BH + shuffled-null counts are mandatory |
| #10 MomentoFX | ag_frontend | Keep the charts, label them `DESCRIPTIVE` |
| #11 Orchestrator | ag_backend | Minimum expected loss, not doubled profit |
| #14 Promo EV | ag_backend | The only real +EV surface. Game weighting is the decisive field |
| #17 Screens | ag_frontend | Calibration Board is the flagship |
| #15 Platform | ag_arch | `import-linter` boundaries, plugin SDK |

---

## The governing rule

> No forecast reaches a user without a skill score and a permutation result
> attached. `DESCRIPTIVE` terms are free to use anywhere. `PREDICTIVE` status
> requires a committed report where the skill CI clears zero and the permutation
> percentile exceeds 95.

---

## Definition of done for V6

- [ ] Pipeline green on `main`
- [ ] Report 001 committed; `c` measured with a CI
- [ ] API server runs on a no-GPU Debian VM
- [ ] Contracts versioned with a compat gate in CI
- [ ] Lexicon loads; every term has support, skill and status
- [ ] Promotion gate enforced; leak-injection test passes
- [ ] Every user-facing claim shows its evidence class

## Handover note for the next session

Read in this order: `.devin/skills/statistical-honesty.md`, then
`docs/V6_IMPLEMENTATION_PLAN.md`, then `.devin/memory/v6_milestone_001.json` for
current state. The constraints in the honesty skill are not stylistic — they are
what keeps the platform's claims defensible, and re-litigating them per feature
wastes the work already done.
