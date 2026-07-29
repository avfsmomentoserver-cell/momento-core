# Debian Local Development Skill

## Description
Running and testing the platform on a Debian 12 box (Azure VM or bare metal) with
apt, venv and SQLite only. No Docker, no cloud services, no GPU.

## Related Technologies
- Debian 12 (bookworm)
- Python 3.11
- SQLite
- VS Code Remote-SSH
- GNU Make

## Use Cases
- Setting up a fresh VM
- Running the test or research loop
- Diagnosing an install failure
- Reproducing a CI failure locally

## Primary Agent
DevOps Engineer (ag_devops)

## Entry Point Configuration
- Auto-detect: enabled
- Coordinated by: ag_admin

---

## Setup

```bash
sudo apt install -y python3 python3-venv python3-pip git make
make venv
make verify
```

That is the whole setup. `make help` lists every target. Full guide in
`docs/local-dev.md`; VM sizing and VS Code config in
`docs/V6_IMPLEMENTATION_PLAN.md`.

## Dependency layout — and why

| File | Contents | Needed for |
|---|---|---|
| `requirements-dev.txt` | pytest, pytest-cov, ruff | `make test`, `make lint`, CI |
| `requirements-audit.txt` | numpy, pandas, scipy | `make audit` only |
| `backend/requirements.txt` | FastAPI + auth + **GPU stack** | API server on a GPU host |

**Never run `pip install -r backend/requirements.txt` on a GPU-less box.** It
pins `torch`, `tensorrt` and `cupy-cuda12x`, all of which need CUDA.
`tensorrt` is not installable from PyPI at all. This is the blocker that kept
pipelines from ever running on this project.

`backend/research/` is pure standard library, so the whole test and research loop
needs only pytest. That is what makes a 2 vCPU VM sufficient.

## Make targets

| Target | Does |
|---|---|
| `make venv` | Creates `.venv`, installs dev deps. Rebuilds only when deps change |
| `make lint` | `ruff check` + `ruff format --check` — same as CI |
| `make fmt` | Applies formatting and safe fixes |
| `make test` | The assertable suite — same as CI |
| `make cov` | Tests with the coverage gate |
| `make research` | Walk-forward + permutation null, writes JSON |
| `make audit` | Data-quality audit; installs numeric extras on demand |
| `make verify` | `lint` + `test`, i.e. everything CI checks |
| `make clean` | Removes venv, caches, generated reports |

`make verify` runs exactly what CI runs, so a green local run means a green
pipeline. Catch failures here and CI becomes confirmation rather than a
debugging loop.

## Free-tier CI budget

400 compute minutes/month, so the pipeline is deliberately minimal:

- `lint` and `test` only; `research` is `when: manual`
- `interruptible: true` — pushing again cancels the superseded pipeline
- `workflow:rules` produce **one** pipeline per change, not both an MR and a
  branch pipeline. That alone halves consumption
- pip cache keyed on `requirements-dev.txt`

The permutation test re-runs the entire walk-forward pipeline once per shuffle.
Run it locally; that is what the VM is for.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ensurepip is not available` | Missing venv package | `sudo apt install python3-venv` |
| pytest collects nothing | Collection limited to `test_research_*.py` | Expected; see `pyproject.toml` |
| `ModuleNotFoundError: momento` | `backend/` not on path | Run via `make`; `conftest.py` handles tests |
| `No matching distribution for tensorrt` | Installed the GPU requirements | Use `requirements-dev.txt` |
| Lint fails on untouched files | Rule set widened | Narrow `select` in `pyproject.toml`, or `make fmt` |
| SSH drops mid-edit | Azure idle timeout | Add `ServerAliveInterval 60` to `~/.ssh/config` |
| Disk full after pip install | Pulled CUDA wheels | `make clean`, then use the dev requirements |

## Security on the VM

- Open port 22 only. Reach the API and web UI over SSH tunnels, not the firewall.
- Configure auto-shutdown; nothing here needs the VM up overnight.
- `backend/.env` is gitignored. Keep it that way.
- Review `gilabtoke.md` in the repo root — if it contains a token, rotate it and
  purge it from history.
