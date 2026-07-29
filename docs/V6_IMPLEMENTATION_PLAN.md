# V6 Implementation Plan — VS Code on Debian (Azure VM)

Hands-on setup and handover. Everything here is free-tier, local-first, and
runnable on one Debian box. Read `.devin/AGENTS.md` and
`.devin/CODING_STANDARDS.md` before changing analysis or forecast code.

**Companion docs**

| File | Purpose |
|---|---|
| `docs/local-dev.md` | The daily loop (`make verify`, `make research`) |
| `.devin/skills/research-suite.md` | How to add a hypothesis |
| `.devin/skills/statistical-honesty.md` | The non-negotiable rules |
| `.devin/workflows/v6-handover.md` | What to do after the tests pass |
| `.devin/memory/v6_milestone_001.json` | Where the work stands |

---

## 1. Azure VM sizing

The research suite is CPU-bound and single-threaded per permutation. It never
needs a GPU.

| Item | Choice | Why |
|---|---|---|
| Size | `Standard_B2s` (2 vCPU, 4 GB) | Burstable, cheapest that runs the suite. `B1s` will thrash on 200 permutations |
| Image | Debian 12 (bookworm) | Ships Python 3.11, matching CI's `python:3.11-slim` |
| Disk | 30 GB standard SSD | The tape is tens of MB; headroom is for the venv and node_modules |
| Networking | SSH (22) only | Do **not** open 8000/5173 to the internet — use SSH tunnels (§4) |

If you already have a VM, none of this needs changing. Any Debian 12 box with
2 vCPU works.

### Cost control

Auto-shutdown is the single highest-value setting: `az vm auto-shutdown` or the
portal's Auto-shutdown blade. A `B2s` left running all month costs materially
more than the same VM stopped nightly, and nothing in this workflow needs it up
overnight.

---

## 2. Provision

```bash
# On the VM
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-venv python3-pip git make curl

# Node only if you're touching web/
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs

git --version && python3 --version && make --version
```

Python 3.11.x confirms you're on bookworm and matched to CI.

### Clone and verify

```bash
git clone https://gitlab.com/avfsmomentoserver1/MomentoAVFSCore.git
cd MomentoAVFSCore
make venv
make verify        # lint + test, identical to CI
```

`make verify` runs exactly what the pipeline runs, so green locally means green
in CI. That's the whole point of the Makefile: CI becomes confirmation, not a
debugging loop.

---

## 3. VS Code Remote-SSH

Develop locally against the VM's filesystem. Nothing is copied.

### On your workstation

1. Install VS Code and the **Remote - SSH** extension (`ms-vscode-remote.remote-ssh`).
2. Add the host to `~/.ssh/config`:

```
Host momento-vm
    HostName <vm-public-ip>
    User <your-user>
    IdentityFile ~/.ssh/momento_azure
    ServerAliveInterval 60
```

3. `F1` → **Remote-SSH: Connect to Host** → `momento-vm`.
4. Open `~/MomentoAVFSCore`.

`ServerAliveInterval` matters — without it Azure drops idle SSH sessions and VS
Code reconnects noisily mid-edit.

### Extensions (install on the remote, not locally)

| Extension | ID | For |
|---|---|---|
| Python | `ms-python.python` | Interpreter, test discovery |
| Ruff | `charliermarsh.ruff` | Lint + format on save, same version as CI |
| GitLab Workflow | `GitLab.gitlab-workflow` | MRs, pipelines, Duo in-editor |
| Even Better TOML | `tamasfe.even-better-toml` | `pyproject.toml` |
| Makefile Tools | `ms-vscode.makefile-tools` | Run targets from the palette |

The GitLab Workflow extension is the one that matters most for handover: it gives
an in-editor agent **file access**, which chat-only sessions do not have. That is
the difference between an agent that can read `linguistics.py` and one that has
to be told what's in it.

### Workspace settings

`.vscode/settings.json` (committed, so every session inherits it):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["backend/tests"],
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": { "source.organizeImports.ruff": "explicit" }
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/.pytest_cache": true,
    "**/.ruff_cache": true
  }
}
```

---

## 4. Running the stack

```bash
make test                    # assertable suite
make lint                    # ruff check + format --check
make fmt                     # apply fixes
make research                # walk-forward + permutation null
make research CSV=eagle-eye-export-2026-07-28__1_.csv
make research PERMUTATIONS=500
```

For the API and web UI, forward ports over SSH rather than opening the firewall:

```bash
# From your workstation
ssh -L 8000:localhost:8000 -L 5173:localhost:5173 momento-vm
```

VS Code Remote-SSH forwards detected ports automatically, so usually you get
this for free.

---

## 5. Removing the blocker

### What the blocker is

`backend/requirements.txt` pins `torch`, `tensorrt` and `cupy-cuda12x`. All three
need CUDA. On a `B2s` (no GPU) and on free-tier CI runners:

- `tensorrt>=8.6.0` — not on PyPI in an installable form; needs NVIDIA's index
- `cupy-cuda12x>=13.0.0` — requires a CUDA 12 runtime
- `torch>=2.0.0` — installs, but pulls ~2 GB of CUDA wheels by default

Any job running `pip install -r backend/requirements.txt` fails at setup. This is
the most likely reason no pipeline ever ran on this project.

### How it's already removed

MR !5 splits dependencies by purpose:

| File | Contents | Needed for |
|---|---|---|
| `requirements-dev.txt` | pytest, pytest-cov, ruff | `make test`, `make lint`, CI |
| `requirements-audit.txt` | numpy, pandas, scipy | `make audit` only |
| `backend/requirements.txt` | unchanged, GPU stack included | Running the API server |

`backend/research/` is **pure standard library** by design, so the entire test
and research loop needs nothing but pytest. That is what makes the suite
runnable on a 2 vCPU box with no GPU and no network after install.

### Finishing the job

The split unblocks CI and the research loop, but `backend/requirements.txt` is
still unusable on a GPU-less box, so the API server can't start on the VM. Fix
with optional extras:

```bash
# Proposed: requirements-api.txt — the server without the GPU stack
fastapi==0.115.6
uvicorn[standard]==0.34.0
pydantic==2.10.4
python-multipart==0.0.20
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
PyJWT==2.9.0
cryptography==44.0.0
slowapi==0.1.9
pyotp==2.9.0
```

Then `backend/requirements-gpu.txt` keeps `torch`, `tensorrt` and `cupy`, and is
installed only on a GPU host. The GPU modules must already degrade gracefully —
`gpu_intelligence/device_manager.py` exists for exactly that — so verify the
import path tolerates their absence, and add a test asserting it. Tracked in #15
as graceful degradation.

**Do not `pip install -r backend/requirements.txt` on the VM.** It will consume
the disk and fail.

---

## 6. What happens after the tests pass

This is the handover point. Full detail in `.devin/workflows/v6-handover.md`.

### Step 1 — Merge in order

1. **!3** first. `pyproject.toml` in !5 collects `test_research_*.py`, which only
   exists in !3. Merging !5 alone gives a green pipeline that ran zero tests.
2. **!5** second.
3. Confirm the pipeline is green on `main`. That's the first pipeline in this
   project's history.

### Step 2 — Produce research report 001

```bash
make research CSV=clean_data.csv PERMUTATIONS=200
```

**This is the single most important command in the plan.** It produces the
measured `c` (house edge) that #12 (ETA), #11 (orchestrator) and #14 (promo EV)
all depend on. Until it runs, those three are blocked on an assumption.

Commit the output:

```bash
mkdir -p research/reports
cp research-report.json research/reports/001-baseline-clean-data.json
git add research/reports/001-baseline-clean-data.json
git commit -m "research: report 001, baseline on clean_data.csv"
```

### Step 3 — Read it correctly

This is where most projects go wrong, so it's worth being explicit.

| Observation | Meaning | Action |
|---|---|---|
| `skill ≈ 0`, CI spans zero | **Expected and correct** | Record it. Do not tune |
| Permutation percentile < 95 | No structure beyond shuffle | **Pass.** Move on |
| Permutation percentile > 95 | Suspicious | Check for data defects **first** |
| `c` materially off 0.97 | Interesting | Check missingness before believing it |
| Flat `dry_streak` table | Gambler's fallacy falsified | Record as a finding |

A well-measured null is the deliverable. It's what makes every other claim in
the platform trustworthy, and it's the thing competitors cannot show.

If the permutation percentile does clear 95, the first suspect is a data defect,
not an edge — duplicate rounds injecting artificial lag-1 autocorrelation is far
more likely than a real signal. Verify with `make audit` before acting.

### Step 4 — Then build, in order

1. **#8 contracts** — every other boundary derives from it
2. **#9 lexicon** — needs the contracts; the keystone invention
3. **#16 promotion gate** — pre-registration, leakage firewall, report registry
4. **#12 / #13 / #10** in parallel behind the contracts
5. **#11 / #14 / #17** — the end-user products

### The rule that governs all of it

> No forecast reaches a user without a skill score and a permutation result
> attached. `DESCRIPTIVE` terms are free to use anywhere; `PREDICTIVE` status
> requires a committed report.

---

## 7. Known traps

**The Δt leakage rule.** `Timestamp` is the *crash* time, so the gap to the next
row encodes the current round's flight duration and therefore its outcome. Any
model given "time since last round" scores near-perfectly in backtest and
produces nothing live. At decision time for round *n*, permitted inputs are
rounds ≤ *n−1*. This is the most expensive mistake available in this codebase.

**Derived columns.** `Points = 100 + 30·log2(Multiplier)` exactly; `Band` is a
bucketing of `Multiplier`; `Color` is a function of `Band`. Feeding them to a
model alongside `Multiplier` triples the apparent feature count and inflates
feature importance. They are checksums, validated on load, never features.

**ID order is not time order.** Always sort by timestamp.

**Duplicate ingest.** Dedup on *same multiplier within 50 ms*, not on `ID`.
Deduping on `ID` misses the real defect signature.

**Legacy test scripts.** Removed in !5. They had a `/home/pirates/...` hardcode,
printed instead of asserting, and needed a live DB. Recover from git history if
a specific check is needed; the right port is to rewrite them as strategies.

---

## 8. Verification checklist

- [ ] `make verify` passes on the VM
- [ ] VS Code Remote-SSH connects; ruff formats on save
- [ ] `make research` completes and writes `research-report.json`
- [ ] Pipeline green on `main`
- [ ] Report 001 committed to `research/reports/`
- [ ] Auto-shutdown configured on the VM
- [ ] `gilabtoke.md` reviewed — if it holds a token, rotate and purge from history
- [ ] No port other than 22 open to the internet
