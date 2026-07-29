"""Momento research suite — hypothesis testing against recorded tapes.

The purpose of this package is falsification, not signal generation. It asks
whether a recorded round tape deviates measurably from an independent
house-edge draw, because every downstream claim the platform makes depends on
the answer:

* If the tape matches `P(X >= x) = p / x` with independent draws, then no
  function of prior rounds can shift the next round's distribution. Expected
  value is `p` at every cashout target, and the honest product is verification
  and harm-reduction tooling rather than betting guidance.
* If the tape deviates, that is an RNG or operator defect. It is a security
  finding to be disclosed, and the evidence needs to survive an audit.

Every module here is pure and dependency-light: no database, no network, no
GPU stack. Give it a list of rounds and it returns plain dictionaries.
"""

from __future__ import annotations

__all__ = [
    "distribution",
    "independence",
    "loader",
    "report",
    "stats",
    "strategies",
]

__version__ = "1.0.0"
