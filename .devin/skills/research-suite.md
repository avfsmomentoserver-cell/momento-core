# Research Suite Skill

## Description
How to add and evaluate a forecasting hypothesis using `backend/research/`. The
suite is CSV-first, DB-free and pure standard library, so it runs offline on any
Debian box with no GPU.

## Related Technologies
- Python (stdlib only)
- pytest
- Statistics

## Use Cases
- Testing whether a pattern predicts anything
- Producing a committed research report
- Promoting a lexicon term to PREDICTIVE
- Porting a legacy print script into an assertable strategy

## Primary Agent
Forecast Engineer (ag_forecast)

## Entry Point Configuration
- Auto-detect: enabled
- Coordinated by: ag_admin
- Prerequisite skill: statistical-honesty

---

## Module map

| Module | Role |
|---|---|
| `loader.py` | Parses exports, dedupes by ID, sorts by timestamp, asserts invariants |
| `labels.py` | `moonshot >= Nx within H rounds`, O(n), trailing horizon excluded |
| `splitter.py` | Expanding-window walk-forward folds, `assert_causal` guard |
| `strategies.py` | Hypotheses on the `features.base.BaseFeature` contract |
| `metrics.py` | Brier, skill + bootstrap CI, calibration, hit rate, paper EV, drawdown |
| `significance.py` | Permutation test over round order |
| `runner.py` | CLI writing a JSON artifact |

## Running it

```bash
make research                                  # clean_data.csv, 200 permutations
make research CSV=other.csv PERMUTATIONS=500

# Or directly
cd backend
python -m research.runner ../clean_data.csv --permutations 200 --json ../report.json
```

## Adding a hypothesis

Subclass `ResearchStrategy` and implement three methods. The split between
`features` and `predict_from_feature` exists so causality is auditable in one
place, and so the permutation test stays affordable (features computed once per
shuffled tape in O(n), not rebuilt per decision point).

```python
class MyHypothesis(ResearchStrategy):
    name = "my_hypothesis"
    description = "One sentence stating the claim precisely enough to falsify."

    def features(self, values):
        """features(v)[i] may read v[:i+1] ONLY. This is the leakage boundary."""
        return [some_causal_transform(values[: i + 1]) for i in range(len(values))]

    def fit(self, feats, labels):
        """Learn from training data. labels may contain None — skip those."""
        ...

    def predict_from_feature(self, feat):
        """Return a probability in [0, 1]."""
        ...
```

Register it in `STRATEGY_REGISTRY`, then:

```bash
make research   # it now appears in the report alongside base_rate
```

### Non-negotiables when writing `features`

- Index `i` reads `values[:i+1]` and nothing beyond. Test by truncating the
  series: earlier values must not change.
- Never derive anything from `dt[i]` — it encodes the outcome of round `i`.
- Never use `Points`, `Band` or `Color` as inputs; they are transforms of
  `Multiplier`.
- Thin buckets fall back to the base rate rather than reporting a probability
  computed from a handful of rounds. See `DryStreakStrategy.MIN_SUPPORT`.

## Reading the report

```
-- dry_streak
   brier 0.xxxx vs reference 0.xxxx
   skill -0.0021 (95% CI -0.0104 .. 0.0067)
   signals 0 precision None recall None
   permutation: observed -0.0021 vs null mean -0.0019, percentile 52.0, p=0.48
   -> Observed skill is inside the shuffled null ... This is a pass.
```

| Field | Read it as |
|---|---|
| `skill` | Better than the base rate? Only if the **CI** clears zero |
| `skill_ci` | Spans zero -> not a finding, regardless of the point estimate |
| `percentile_vs_null` | Below 95 -> no structure beyond shuffle. **A pass** |
| `signals 0` | Never crossed the decision threshold. Expected for a flat table |
| `learned_table` | The actual object of interest. Flat across buckets = falsified |

**A skill score near zero with a CI spanning zero is the expected, correct
result.** Record it and move on. See statistical-honesty Rule 3.

If `percentile_vs_null` exceeds 95, suspect a data defect before an edge —
duplicate rounds injecting artificial lag-1 autocorrelation is far more likely
than real signal. Confirm with `make audit` first.

## Promotion to PREDICTIVE

Both conditions, no exceptions:

1. Skill CI lies **strictly above zero**
2. Permutation percentile **clears 95**

Then commit the report to `research/reports/NNN-slug.json` and reference its ID
in the lexicon term's `promoted_by` field. A term cannot reach `PREDICTIVE`
without that link.

## Porting a legacy script

The six removed print scripts tested real ideas — ladder detection, vocabulary
processing, forecast accuracy — but printed numbers with nothing to compare them
against. To port one:

1. State its claim as a single falsifiable sentence.
2. Implement it as a `ResearchStrategy`.
3. Run it against `base_rate` with a permutation test.
4. Commit the report, whichever way it lands.

Recover the originals from git history before !5 if needed.
