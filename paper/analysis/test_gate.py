#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest>=8"]
# ///
"""
Reproduction test for the criterion-validity gate against the frozen
seed summary. Locks the committed ADR 0011/0012 numbers as assertions:

- {6..10}  → ratio ≈ 2.7257, PASS  (ADR 0011 resolution)
- {11..20} → ratio ≈ 1.8027, FAIL  (ADR 0012 resolution)
- tally_M({6..10}) = 3              (ADR 0011 M' = 3/5)
- tally_M over any subset containing a gate-gated seed raises.

If any of these fail, the frozen CSV or the gate logic has drifted
from the committed record — STOP and investigate before trusting
gate_distribution.py.

Run:  uv run paper/analysis/test_gate.py
"""

import math

from gate import gate_verdict, tally_M, load_frozen, T, GATE_THRESHOLD

ORIGINAL = [6, 7, 8, 9, 10]
ESCALATION = list(range(11, 21))


def test_original_subset_passes_at_2_73():
    v = gate_verdict(ORIGINAL)
    # isclose, not ==: the median is a computed float (single element here,
    # mean-of-two for the escalation subset) and exact equality is brittle.
    assert math.isclose(v["sigma_init_median"], 0.023918, abs_tol=1e-9), v["sigma_init_median"]
    assert math.isclose(v["ratio"], 2.7257, abs_tol=5e-4), v["ratio"]
    assert v["passed"] is True


def test_escalation_subset_fails_at_1_80():
    v = gate_verdict(ESCALATION)
    assert math.isclose(v["sigma_init_median"], 0.036166, abs_tol=1e-9), v["sigma_init_median"]
    assert math.isclose(v["ratio"], 1.8027, abs_tol=5e-4), v["ratio"]
    assert v["passed"] is False


def test_M_prime_is_3_of_5():
    assert tally_M(ORIGINAL) == 3


def test_tally_refuses_gate_gated_seeds():
    raised = False
    try:
        tally_M([6, 11])  # 11 is gate-gated
    except ValueError:
        raised = True
    assert raised, "tally_M must refuse a gate-gated seed, not silently count it"


def test_gate_threshold_is_2():
    assert GATE_THRESHOLD == 2.0
    assert T == 0.0922


if __name__ == "__main__":
    # Minimal runner (no pytest dependency needed for the smoke path).
    frozen = load_frozen()
    results = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                results.append((name, "PASS", ""))
            except AssertionError as e:
                results.append((name, "FAIL", str(e)))
            except Exception as e:  # noqa: BLE001
                results.append((name, "ERROR", f"{type(e).__name__}: {e}"))
    width = max(len(n) for n, _, _ in results)
    for n, status, detail in results:
        print(f"  {n.ljust(width)}  {status}  {detail}".rstrip())
    n_pass = sum(1 for _, s, _ in results if s == "PASS")
    print(f"\n{n_pass}/{len(results)} tests passed")
    raise SystemExit(0 if n_pass == len(results) else 1)
