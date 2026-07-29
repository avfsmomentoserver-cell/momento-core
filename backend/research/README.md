# Research Suite — Edge Falsification

This suite answers one question, on which the entire commercial strategy
depends:

> Does a recorded round tape deviate measurably from independent draws from a
> fixed house-edge distribution?

The answer determines which products are viable. It is deliberately built so
that "no edge" is the expected result and an edge claim has to survive several
independent gates.

## Running it

```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install pytest        # not requirements.txt
.venv/bin/python -m pytest tests -v
.venv/bin/python -m research.report # writes research-report.json
```

No database, no network and no GPU stack required. Every statistic is
implemented on the standard library in `research/stats.py`, so the suite runs
in CI and inside an audit unchanged. Installing `requirements.txt` is
unnecessary and slow: it pulls torch, TensorRT and CuPy, none of which this
suite imports.

### Cost and the free tier

Permutation testing is the only expensive part. Each iteration reshuffles the
whole outcome vector, and five signals over ~15,400 decision points adds up
quickly. The smallest p-value a permutation test can report is
`1 / (iterations + 1)`, so 400 iterations already resolves the 0.01 threshold
every gate uses.

| Path | Permutations | Command |
| --- | --- | --- |
| CI / free tier | 400 | `pytest tests -m "not slow"` |
| Release / audit | 2,000 | `pytest tests` |

The GitLab free tier allows 400 compute minutes per month. The `research:suite`
job skips the slow battery, caches pip, sets `interruptible: true` so a
superseded pipeline is cancelled rather than paid for, and uses `rules:changes`
so unrelated commits spend nothing. The full battery lives in `research:full`,
which is `when: manual`.

To avoid using the quota entirely, register a local runner with the shell
executor and the same jobs run on your machine for free.

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/research/tape` | Validate the root export against the semantic layer |
| `GET /api/v1/research/report` | Full verdict (`tape=csv` or `tape=live`) |
| `GET /api/v1/research/cashout-profile` | Return per unit staked at each cashout target |
| `GET /api/v1/research/independence` | Pressure, serial and gap independence tests |

The two endpoints that permute default to 400 iterations and cap at 2,000, so a
single request cannot stall the event loop on a full-tape run.

## The theory being tested

A provably-fair crash curve draws its multiplier so that

```
P(X >= x) = p / x        for x >= 1,  p = 1 - house_edge
```

Three consequences follow, and each is tested separately:

1. **`1/X` is uniform.** Tested by KS in `distribution.probability_integral_transform`.
2. **The tail index is 1.** Tested by the Hill estimator in `distribution.tail_conformance`.
3. **Expected value is `p` at every cashout target.** Because a flat stake
   cashing out at `x` returns `x * P(X >= x) = x * p/x = p`. Tested empirically
   in `distribution.cashout_expected_values`.

The third is the commercially decisive one. Expected value does not depend on
the exit point, so no choice of target creates an edge. And because rounds are
independent draws, no function of prior rounds changes the next round's
distribution, so nothing that merely selects *when* to bet can create one
either. Bet sizing changes variance and probability of ruin, never expected
value.

## Why the Forex framing does not carry over

Accumulation, resistance and release are real mechanisms in a currency market
because there is a continuous auction underneath: an order book, inventory, and
participants whose unfilled interest persists across time. Price is the output
of that process, so past price genuinely informs future price.

A crash multiplier has no order book. Each round is an independent draw from a
fixed CDF, generated before any bet is placed and verifiable afterwards. There
is no medium in which pressure can accumulate between rounds. This is why
`independence.test_pressure_release` expresses the hypothesis as five concrete
signals and tests them properly rather than assuming either answer:

| Signal | Reading of "pressure is building" |
| --- | --- |
| `drought_no_10x_in_lookback` | No 10x in 40 rounds |
| `variance_compression_shelf` | Recent range collapsed to a shelf |
| `repeated_ceiling_rejection` | Three or more rejections just under 10x |
| `ascending_floor_accumulation` | Rising median with no release |
| `cold_streak_ten_sub_2x` | Ten consecutive sub-2x rounds |

## How a false result is prevented

The suite is designed so that both kinds of error are caught.

**Against false positives:**

- **Structural causality.** In `independence.signal_lift` the signal sees
  `multipliers[i - lookback:i]` and the outcome is drawn from
  `multipliers[i:i + horizon]`. The windows abut but never overlap, so a signal
  cannot see its own outcome. `NextBandStrategy` likewise folds each outcome
  into its lookup tables only *after* predicting it.
- **Interval separation.** A lift only counts if the Wilson intervals of the
  fired and idle arms are disjoint.
- **Permutation testing.** The signal-to-outcome pairing is shuffled 2,000
  times, which destroys real timing while preserving both marginals. This stops
  a signal being credited for having fired during a lucky stretch.
- **Corroboration for anomalies.** `report.run_report` only returns
  `anomaly_detected` when deviations appear on multiple axes, because across
  this many tests a single low p-value is expected under the null.

**Against false negatives**, which matter just as much, since a suite that
always answers "no edge" is worthless:

- `tests/conftest.py::synthetic_dependent_tape` plants a real rule (after 15
  rounds without a 10x, the next round is forced high). `TestDetectionPower`
  asserts the suite finds it.
- `TestCausality::test_future_peeking_signal_is_flagged` gives a signal the
  answer and asserts it is flagged as actionable.
- `synthetic_fair_tape` inverts the fair CDF; the suite must certify it as fair.

## Reading the verdict

- **`conforming_no_edge`** — The tape is a fair independent draw. Betting
  guidance is not a viable product on this data. The defensible products are
  verification, compliance and harm-reduction tooling.
- **`anomaly_detected`** — The tape deviates from the fair law. This is an RNG
  or operator defect. Reproduce it on an independent sample and follow
  responsible disclosure. Do not ship it as a consumer betting feature: a
  defect that is publicised gets patched, and a defect that is monetised
  quietly is a legal problem.
- **`inconclusive`** — Not enough data, or the tape failed validation.

## The exports

Both root CSVs share the schema `ID,Timestamp,Multiplier,Color,Band,Points,Ingest Method`,
and `Band`, `Color` and `Points` are pure functions of `Multiplier` defined in
`momento.linguistics`. `Points` is exactly `100 + 30 * log2(multiplier)`. The
loader verifies every row against those functions, so a hand-edited or
re-sorted export fails loudly.

| File | Rounds | Contents |
| --- | --- | --- |
| `eagle-eye-export-2026-07-28__1_.csv` | ~15,469 | Clean full tape, all ten bands |
| `eagle-eye-export-2026-07-28.csv` | ~1,484 | The same data filtered to >= 10x |

The second file is a labelled positive class, not an independent sample.
Fitting a distribution to it would produce a badly biased house edge, so
`loader.load_clean_tape` raises `TruncatedExportError` if the tape it loads
looks filtered.

## Adding a strategy

Implement `features.base.BaseFeature` in `research/strategies.py` and add it to
`STRATEGIES`. `compute` produces the live metric and `backtest` produces the
evidence, so the two cannot drift apart. Anything that survives testing ports
into `backend/features/` and the plugin inventory without a rewrite.

A new strategy must return an `actionable` verdict derived from the gates above.
Do not add a strategy that reports a hit rate without a baseline comparison and
a resampling test.
