"""dmgap: the analysis of the diabetes-TB gap study (registered plan, docs/analysis_plan.md).

Modules: panel (the extracted panel, NA rules and denominator bases, §3), reference (p_u,
§4), draws (the draw sets, §5.3), benchmark (k_b, c_b, c3_b, §5.1-§5.2, §6.4), cascade
(C1, y, C2/R, C3, E3, §5.1, §5.6), gaps (E1, E2, the total, §5.4-§5.5), priority
(P(top-5), tiers, the decomposition and the scenario, §6), trend (§7), validate (H1-H3,
the funnel, the grid, the label, §8), table (CSV writing). The run is src/run_all.py.

tbprio 1.0.1 is imported and called, never copied or modified (§10.1-§10.2).
"""
from __future__ import annotations

import importlib.metadata

TBPRIO_VERSION = "1.0.1"
SEED = 20261122
N_DRAWS = 10_000


def check_tbprio() -> str:
    """Stop unless the installed tbprio reports version 1.0.1 (plan §10.1, Review Focus 5)."""
    import tbprio
    v = getattr(tbprio, "__version__", None) or importlib.metadata.version("tbprio")
    if v != TBPRIO_VERSION:
        raise RuntimeError(f"tbprio {v} is installed; the plan pins {TBPRIO_VERSION}")
    return v
