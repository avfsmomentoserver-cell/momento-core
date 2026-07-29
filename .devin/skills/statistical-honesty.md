# Statistical Honesty Skill

## Description
The non-negotiable rules for any claim the platform makes. Read this before
touching analysis, forecast, backtest or user-facing copy. Violating any rule
here produces confident nonsense that is expensive to unwind later.

## Related Technologies
- Statistics
- Forecasting
- QA

## Use Cases
- Reviewing a forecast or backtest claim
- Writing acceptance criteria for a predictive feature
- Deciding whether a result is publishable
- Reviewing user-facing copy

## Primary Agent
Forecast Engineer (ag_forecast)

## Entry Point Configuration
- Auto-detect: enabled
- Coordinated by: ag_admin
- Consulted by: ag_qa, ag_backend, ag_frontend, ag_docs

---

## Rule 1 — EV is constant across cashout targets

For a provably fair crash game, survival is `P(M >= x) = c/x` with `c ~ 0.97`.
Cashing out at target `T` wins with probability `c/T` and pays `T`:

```
EV per unit staked = T * (c/T) - 1 = c - 1 ~ -3%
```

Identical for every `T`. Because rounds are independent, conditioning on history
does not change it. No entry rule, cashout target or staking plan alters the
sign. Martingale included — it converts a small frequent loss into a rare
catastrophic one at the same EV.

**Consequence**: never ship a feature whose value proposition is positive
expected return from betting. Reframe as minimum expected loss and quantified
survival. The one genuine +EV surface is external to the game: operator bonuses
and cashback (#14).

## Rule 2 — Accuracy is not skill

A forecaster that always emits `P = 0.485` is perfectly calibrated and completely
useless. Always report both:

- **Calibration**: Brier, log loss, reliability diagram, PIT
- **Skill**: `SS = 1 - BS_model / BS_reference`, with a bootstrap CI

A positive point-estimate skill score whose CI crosses zero is **not a finding**.

## Rule 3 — Nulls are results

The research suite exists to *falsify* structure, not to find it. If Ljung-Box,
runs, band chi-square, the conditional table and the permutation test all return
null, it is working correctly.

**Do not tune a null away.** Do not adjust thresholds until something passes. Ten
rigorous nulls plus a measured house edge is the deliverable — it is what makes
every other claim in the platform trustworthy, and it is exactly what
competitors cannot show.

## Rule 4 — The shuffle baseline is mandatory

Any strategy or pattern claim must be re-run on row-shuffled data. Shuffling
preserves the marginal distribution exactly and destroys temporal structure. If
real performance sits inside the shuffled distribution, the strategy learned
nothing.

Cheapest and highest-value check in the codebase. See
`backend/research/significance.py`.

## Rule 5 — The Δt leakage firewall

`Timestamp` is the **crash** time, so the interval between consecutive rows
contains the flight duration of the current round, and flight duration is a
monotone function of the crash point.

> `dt[i]` is a decoded readout of `multiplier[i]`.

At decision time for round *n*, permitted inputs are multipliers and timestamps
for rounds **<= n-1**. Any model given "time since last round" scores
near-perfectly in backtest and produces nothing live.

Enforce as an assertion, not a convention.

## Rule 6 — Derived columns are checksums, never features

| Column | Relationship |
|---|---|
| `Points` | `100 + 30*log2(Multiplier)`, exact |
| `Band` | Fixed bucketing of `Multiplier`, lower bound inclusive |
| `Color` | Function of `Band` |

Only `ID`, `Timestamp` and `Multiplier` carry information. Feeding the derived
columns to a model alongside `Multiplier` triples the apparent feature count and
inflates feature importance. Validate them on load; never train on them.

## Rule 7 — Multiple testing must be corrected

Mining motifs over a 10-symbol band alphabet on 15k rounds will find thousands
of "significant" patterns by chance. Any batch of hypotheses requires
Benjamini-Hochberg, reported alongside raw p-values, plus the shuffled-null
count for comparison. Compare **counts of survivors**, not individual patterns.

## Rule 8 — Claim safety in user-facing copy

Forbidden in any user-visible string: `will crash`, `due for`, `guaranteed`,
`next round will`, `hot streak`, `cold streak`, `profit strategy`, `sure bet`,
`beat the game`, `can't lose`.

Selling predictions for a provably random game is consumer-protection exposure
(UK ASA, EU UCPD, FTC) regardless of intent.

Technical indicators (RSI, MACD, Bollinger, Stochastic) presume autocorrelated
price series. On an i.i.d. sequence they are decoration — keep them as history
visualisation, never as signals or guidance.

## Rule 9 — Status is rendered, never hidden

Every lexicon term carries `DESCRIPTIVE`, `PREDICTIVE` or `RETIRED`.
`DESCRIPTIVE` terms are fully usable for UI, grouping, search and explanation.
Only `PREDICTIVE` terms may drive forward guidance, and promotion requires a
committed research report where the skill CI lies strictly above zero **and** the
permutation percentile clears 95.

The user must always be able to see the evidence class of what they are looking
at.

---

## Review checklist

Before approving any MR that touches a claim:

- [ ] Skill score reported with a CI, not just accuracy
- [ ] Permutation or shuffle baseline included
- [ ] No feature reads `dt[i]` or any round >= the decision index
- [ ] Derived columns not used as model inputs
- [ ] BH correction applied if multiple hypotheses were tested
- [ ] User-facing strings free of forbidden phrasing
- [ ] Lexicon `status` respected in every consumer
- [ ] A null result is recorded as a result, not iterated away
