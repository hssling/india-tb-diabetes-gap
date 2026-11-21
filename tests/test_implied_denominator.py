"""verification/check_implied_denominator.py reproduces the match counts of plan
section 12.1 from the committed extracts, and fails when a printed value moves."""
import copy

from verification import check_implied_denominator as cid


def test_match_counts_are_plan_12_1():
    got = cid.counts(cid.comparisons(cid.read_cells()))
    assert {k: n_in for k, (n_in, _) in got.items()} == cid.EXPECTED
    assert all(n == 37 for _, n in got.values())


def test_interval():
    assert cid.interval(921, cid.printed_pct("921 (92.1)")) == (1000, 1000)
    assert cid.interval(190, cid.printed_pct("190 (33%)")) == (568, 584)
    assert cid.interval(1, cid.printed_pct("1 (0%)"))[1] is None


def test_a_moved_value_changes_the_count():
    cells = cid.read_cells()
    bad = copy.deepcopy(cells)
    for r in bad:
        if r["table_key"] == "TBAR2022_A1.4" and r["printed_unit"] == "Kerala":
            r["value"] = str(int(r["value"]) + 500)
    before = cid.counts(cid.comparisons(cells))[(2021, "a1_4_net_main")][0]
    after = cid.counts(cid.comparisons(bad))[(2021, "a1_4_net_main")][0]
    assert (before, after) == (37, 36)
