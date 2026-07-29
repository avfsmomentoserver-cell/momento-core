# Local development on Debian

Everything runs on one machine with `apt`, `venv` and SQLite. No Docker, no
cloud account, no paid service. Verified target: **Debian 12 (bookworm)**, which
ships Python 3.11.

## Setup

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git make

git clone https://gitlab.com/avfsmomentoserver1/MomentoAVFSCore.git
cd MomentoAVFSCore

make venv    # creates .venv, installs pytest + ruff
make verify  # lint + test, exactly what CI runs
```

That is the whole setup. `make help` lists every target.

## Why the dependencies are split

`backend/requirements.txt` pins `torch`, `tensorrt` and `cupy-cuda12x`. Those
require CUDA and **will not install** on a free-tier CI runner or a Debian box
without an NVIDIA GPU, which is why the test loop uses its own file:

| File | Contents | Needed for |
|---|---|---|
| `requirements-dev.txt` | pytest, pytest-cov, ruff | `make test`, `make lint` — the default loop |
| `requirements-audit.txt` | numpy, pandas, scipy | `make audit` only |
| `backend/requirements.txt` | FastAPI, auth, GPU stack | Running the actual API server |

`backend/research/` is **pure standard library** by design, so the research suite
and its tests need nothing beyond pytest. That is what keeps the loop fast and
fully offline after install.

## Daily loop

```bash
make test              # assertable suite
make lint              # ruff check + format --check
make fmt               # apply formatting and safe fixes
make cov               # tests with the coverage gate
make verify            # lint + test together
```

## Running the research suite

```bash
make research                              # against clean_data.csv
make research CSV=eagle-eye-export-2026-07-28__1_.csv
make research PERMUTATIONS=500             # tighter null, slower
```

Writes `research-report.json`. The permutation test re-runs the entire
walk-forward pipeline once per shuffle, so 200 permutations on 15k rounds takes
real CPU time. This is exactly why it belongs on local hardware rather than in
CI, and why the CI `research` job is `when: manual`.

### Reading the output

```
=== momento research suite ===
rounds: 15469 (read 15469, dupe ids 0)
span: ... -> ...
id order == time order: True
target: moonshot >= 20.0x within the next 10 rounds
scorable points: 15459 (base rate 0.xxxx)

-- base_rate
   skill 0.0000 (95% CI ...)
-- dry_streak
   skill -0.00xx (95% CI ...)
   permutation: observed ... vs null mean ..., percentile ..., p=...
   -> Observed skill is inside the shuffled null: ... This is a pass.
```

**A skill score near zero with a CI spanning zero is the expected, correct
result** for a provably fair game. It is not a bug and must not be tuned away.
The suite exists to falsify structure, not to find it, and a well-measured null
is what makes every other claim in the platform trustworthy.

What *would* be worth investigating: a permutation percentile above 95. Before
believing it, check for a data defect first — duplicate rounds injecting
artificial lag-1 autocorrelation is far more likely than a real edge.

## Free-tier CI budget

GitLab free tier allows 400 compute minutes/month, so the pipeline is
deliberately minimal:

- `lint` and `test` only; both should finish in a couple of minutes.
- `interruptible: true`, so pushing again cancels the superseded pipeline.
- `workflow:rules` produce **one** pipeline per change, not both an MR and a
  branch pipeline.
- pip cache keyed on `requirements-dev.txt`.
- `research` is `when: manual` and never runs automatically.

Since `make verify` runs the same commands as CI, catch failures locally and CI
becomes confirmation rather than a debugging loop.

## Troubleshooting

**`ensurepip is not available`** — install `python3-venv`:

```bash
sudo apt install -y python3-venv
```

**pytest collects nothing** — expected. `pyproject.toml` limits collection to
`test_research_*.py`, because the six legacy scripts in `backend/tests/` are
print-based and depend on a live database. They are excluded until ported.

**`ModuleNotFoundError: momento`** — run through `make`, or ensure `backend/` is
on `sys.path`. `backend/tests/conftest.py` handles this for tests.

**Lint fails on untouched files** — the ruff rule set in `pyproject.toml` is
intentionally narrow so the gate passes on the existing tree. Widen it in a
dedicated MR rather than mixing a cleanup into a feature change.
