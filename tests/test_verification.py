"""Mutation tests of the verification suite (analysis plan section 10.4;
verification/MUTATIONS.md).

Each test breaks one thing in a temporary copy of the repository (never in the repository
itself) and shows that the check that owns it fails: a headline value, the plan above
section 12 (in a temporary clone), a label, an extracted cell, an NFHS-5 prevalence, k_b in
an output, a Monte Carlo summary, an unlogged deviation or post hoc label, and a file that a
rerun does not reproduce.
"""
import ast
import csv
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from src.extract import itr_dm
from verification import (check_all, check_deviations, check_extraction_totals,
                          check_outputs, check_plan_order, check_rerun)

ROOT = Path(__file__).resolve().parents[1]


# ---- helpers -------------------------------------------------------------------------

@pytest.fixture(scope="module")
def committed_problems():
    return check_outputs.problems(ROOT)


@pytest.fixture
def root(tmp_path):
    """A copy of what the content checks read: outputs/, data/extracted/, the plan and the
    README."""
    r = tmp_path / "repo"
    shutil.copytree(ROOT / "outputs", r / "outputs")
    shutil.copytree(ROOT / "data" / "extracted", r / "data" / "extracted")
    (r / "docs").mkdir()
    shutil.copy2(ROOT / "docs" / "analysis_plan.md", r / "docs" / "analysis_plan.md")
    shutil.copy2(ROOT / "README.md", r / "README.md")
    return r


def edit_csv(path: Path, match: dict, column: str, fn) -> None:
    """Apply fn to ``column`` of every row matching ``match``; at least one must match."""
    with open(path, encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        header, rows = reader.fieldnames, list(reader)
    hits = [r for r in rows if all(r[k] == v for k, v in match.items())]
    assert hits, f"no row of {path.name} matches {match}"
    for r in hits:
        r[column] = fn(r[column])
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, header, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def fails(root: Path, *needles: str) -> list[str]:
    bad, _ = check_outputs.problems(root)
    assert bad, "check_outputs passed on a mutated copy"
    for n in needles:
        assert any(n in b for b in bad), (n, bad)
    return bad


# ---- the checks pass on the repository ---------------------------------------------------

def test_check_outputs_is_standard_library_only():
    """Plan 10.4: an independent recompute; nothing of src/, no numpy, scipy or tbprio."""
    tree = ast.parse((ROOT / "verification" / "check_outputs.py").read_text(encoding="utf-8"))
    mods = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            mods |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import"
            mods.add(node.module.split(".")[0])
    assert mods and mods <= set(sys.stdlib_module_names), mods
    r = subprocess.run([sys.executable, "-I", "-c",
                        "import runpy, sys; sys.argv = ['x']; "
                        "runpy.run_path('verification/check_outputs.py', run_name='m'); "
                        "print(sorted(m for m in sys.modules if m.split('.')[0] in "
                        "('numpy', 'scipy', 'src', 'tbprio', 'dmgap')))"],
                       cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "[]", r.stdout + r.stderr


def test_check_outputs_passes_on_the_committed_outputs(committed_problems):
    bad, ok = committed_problems
    assert bad == []
    assert [line[:3] for line in ok] == ["(a)", "(b)", "(c)", "(d)", "(e)", "(f)", "(g)",
                                         "(h)"]
    assert "H3 = 24" in ok[2] and "k = 1 = 27" in ok[2]
    assert "'supported' (12/12" in ok[7]


def test_check_deviations_passes():
    bad, ok = check_deviations.problems(ROOT)
    assert bad == [] and ok


def test_own_irls_matches_the_main_slope_to_1e_6():
    c = check_outputs.Checker(ROOT)
    f = check_outputs.h1_fit(c.panel, c.units, c.p, "2019+2021", "tested")
    with open(ROOT / "outputs" / "headline.csv", encoding="utf-8", newline="") as fh:
        h1 = next(r for r in csv.DictReader(fh) if r["estimate"] == "H1")
    assert abs(f["beta"][1] - float(h1["value"])) < 1e-6


def test_exact_beta_functions():
    assert check_outputs.betainc(2.0, 3.0, 0.5) == pytest.approx(0.6875, abs=1e-14)
    assert check_outputs.beta_ppf(0.5, 1.0, 1.0) == pytest.approx(0.5, abs=1e-12)
    q = check_outputs.beta_ppf(0.975, 5000.5, 60000.5)
    assert check_outputs.betainc(5000.5, 60000.5, q) == pytest.approx(0.975, abs=1e-12)
    # E[max(0, t - Y)] for Y ~ Uniform(0, 1) is t^2 / 2
    assert check_outputs.e_shortfall(0.4, 1.0, 1.0) == pytest.approx(0.08, abs=1e-14)
    assert check_outputs.e_max(0.4, 1.0, 1.0) == pytest.approx(0.58, abs=1e-14)


# ---- mutations: check_outputs -----------------------------------------------------------

def test_mutated_headline_value_fails(root):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H1"}, "value",
             lambda v: repr(float(v) + 0.01))
    fails(root, "(i) headline H1 value vs spec_curve main beta1",
          "(i) headline H1 value vs the own IRLS")


def test_mutated_descriptive_headline_fails(root):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H3"}, "value", lambda v: "23")
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H2"}, "lo",
             lambda v: repr(float(v) - 0.001))
    fails(root, "(i) headline H3 value vs H3_units", "(f) headline H2 lo")


def test_flipped_label_fails(root):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H1"}, "label",
             lambda v: "not established")
    fails(root, "(h) headline H1 label")


def test_label_on_a_descriptive_estimate_fails(root):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H3"}, "label",
             lambda v: "supported")
    fails(root, "(h) headline H3 label")


def test_spec_curve_sign_flip_fails(root):
    edit_csv(root / "outputs" / "spec_curve.csv",
             {"reference": "simple", "year_set": "2023", "weights": "unweighted"}, "beta1",
             lambda v: repr(-float(v)))
    fails(root, "(e) spec_curve simple 2023 unweighted beta1")


def test_changed_extracted_cell_fails_check_outputs(root):
    edit_csv(root / "data" / "extracted" / "dm_panel.csv",
             {"unit": "Bihar", "year": "2023", "measure": "diabetic"}, "value",
             lambda v: str(int(v) + 1))
    fails(root, "(c) Bihar 2023 D", "(d) 2023 empirical-Bayes prior a2")


def test_changed_extracted_cell_fails_check_extraction_totals():
    cells = check_extraction_totals._read("dm_cells.csv")
    assert itr_dm.unrecorded_gaps(check_extraction_totals.printed_totals(cells)) == []
    r = next(r for r in cells if r["printed_unit"] == "Bihar" and r["value"].isdigit())
    r["value"] = str(int(r["value"]) + 1)
    assert itr_dm.unrecorded_gaps(check_extraction_totals.printed_totals(cells))


def test_changed_panel_cell_fails_the_coarsening_check():
    cells = check_extraction_totals._read("dm_cells.csv")
    panel = check_extraction_totals._read("dm_panel.csv")
    assert check_extraction_totals.coarsening(cells, panel) == []
    r = next(r for r in panel if r["unit"] == "Bihar" and r["year"] == "2023"
             and r["measure"] == "diabetic")
    r["value"] = str(int(r["value"]) + 1)
    assert any("2023 diabetic" in b for b in check_extraction_totals.coarsening(cells, panel))


def test_changed_nfhs_prevalence_fails(root):
    edit_csv(root / "data" / "extracted" / "nfhs_dm.csv", {"unit": "Kerala", "sex": "women"},
             "prevalence_pct", lambda v: f"{float(v) + 0.1:.1f}")
    fails(root, "(a) Kerala w", "(a) Kerala p_sex_weighted", "(c) Kerala 2023 R_k1:",
          "(d) Kerala E1 point")


def test_changed_kb_in_benchmark_fails(root):
    edit_csv(root / "outputs" / "benchmark.csv",
             {"kind": "k_b", "percentile": "p75", "pool": "2021+2022",
              "reference": "sex_weighted", "prior": "empirical_bayes"}, "value",
             lambda v: repr(float(v) * 1.001))
    fails(root, "(b) k_b p75 2021+2022 sex_weighted empirical_bayes:")


def test_changed_kb_in_cascade_fails(root):
    edit_csv(root / "outputs" / "cascade.csv",
             {"spec": "main", "unit": "Kerala", "year": "2023"}, "k_b",
             lambda v: repr(float(v) + 0.01))
    fails(root, "(b) cascade main Kerala 2023 k_b")


def test_monte_carlo_summaries_are_checked(root):
    """A draw-based value moved beyond its Monte Carlo tolerance fails."""
    edit_csv(root / "outputs" / "gaps.csv",
             {"unit": "Bihar", "year": "2023", "gap": "E2", "spec": "main"}, "mean",
             lambda v: repr(float(v) * 1.02))
    edit_csv(root / "outputs" / "scenario.csv", {"spec": "main", "row": "national"}, "mean",
             lambda v: repr(float(v) + 500.0))
    edit_csv(root / "outputs" / "cascade.csv",
             {"spec": "main", "unit": "Kerala", "year": "2023"}, "R_k1_hi",
             lambda v: repr(float(v) * 1.05))
    fails(root, "(d) Bihar E2 mean", "(g) national A mean", "(c) Kerala 2023 R_k1_hi")


def test_flipped_h3_flag_fails(root):
    edit_csv(root / "outputs" / "cascade.csv",
             {"spec": "main", "unit": "Bihar", "year": "2023"}, "below_benchmark",
             lambda v: "False" if v == "True" else "True")
    fails(root, "(c) Bihar 2023 below_benchmark")


def test_check_outputs_main_exits_1_on_a_mutation(root, capsys):
    edit_csv(root / "outputs" / "headline.csv", {"estimate": "H1"}, "label",
             lambda v: "not established")
    assert check_outputs.main(["--root", str(root)]) == 1
    assert "FAIL: (h) headline H1 label" in capsys.readouterr().out


# ---- mutations: check_plan_order (temporary clone) ----------------------------------------

def test_edit_above_section12_fails_in_a_clone(tmp_path):
    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", "-q", str(ROOT), str(clone)], check=True)
    assert check_plan_order.problems(clone) == []
    plan = clone / "docs" / "analysis_plan.md"
    text = plan.read_bytes().decode("utf-8")
    old = "Main k_b = the 75th percentile of g_u"
    assert text.index(old) < text.index("## 12. Deviations (dated)")
    plan.write_bytes(text.replace(old, "Main k_b = the 80th percentile of g_u", 1)
                     .encode("utf-8"))
    bad = check_plan_order.problems(clone)
    assert len(bad) == 1 and "uncommitted edit" in bad[0], bad
    subprocess.run(["git", "-C", str(clone), "-c", "user.name=m", "-c", "user.email=m@x",
                    "-c", "commit.gpgsign=false", "commit", "-qam",
                    "mutation: edit above section 12"], check=True)
    bad = check_plan_order.problems(clone)
    assert len(bad) == 1 and "above section 12 differs" in bad[0], bad
    assert check_plan_order.main(clone) == 1


# ---- mutations: check_deviations --------------------------------------------------------

def _append_line(path: Path, line: str) -> None:
    with open(path, "a", encoding="utf-8", newline="") as f:
        f.write(line + "\n")


@pytest.mark.parametrize("line, ok", [
    ("H9,0.1,,,,,,,post hoc check", False),
    ("H9,0.1,,,,,,,exploratory (plan §12.1)", False),        # 12.1 is not exploratory
    ("H9,0.1,,,,,,,see plan §12.9", False),                  # no such entry
    ("H9,0.1,,,,,,,see plan_12.7_sensitivity", False),       # no such entry
    ("H9,0.1,,,,,,,a deviation from the plan", False),
    ("H9,0.1,,,,,,,a deviation from the plan (§12.2)", False),  # 12.2 is a naming note
    ("H9,0.1,,,,,,,the C1 denominator deviation (plan §12.1)", True),
    ("H9,0.1,,,,,,,deviations are dated in plan §12", True),
])
def test_unlogged_labels_fail(root, line, ok):
    _append_line(root / "outputs" / "headline.csv", line)
    bad, _ = check_deviations.problems(root)
    assert (bad == []) is ok, bad


def test_unlogged_label_in_readme_and_data_flags_fail(root):
    _append_line(root / "README.md", "A post hoc analysis of C3.")
    edit_csv(root / "data" / "extracted" / "dm_panel.csv",
             {"unit": "Bihar", "year": "2023", "measure": "diabetic"}, "flag",
             lambda v: v + ";deviation_plan_12.9")
    bad, _ = check_deviations.problems(root)
    assert any(b.startswith("README.md line") for b in bad), bad
    assert any(b.startswith("data/extracted/dm_panel.csv line") for b in bad), bad


def test_undated_section12_entry_fails(root):
    _append_line(root / "docs" / "analysis_plan.md",
                 "\n**12.5 (soon), a post hoc analysis.** Text.")
    bad, _ = check_deviations.problems(root)
    assert any("12.5 has no date" in b for b in bad), bad


def test_post_hoc_line_covered_by_a_dated_post_hoc_entry_passes(root):
    _append_line(root / "docs" / "analysis_plan.md",
                 "\n**12.5 (22 November 2026), a post hoc analysis.** Text.")
    _append_line(root / "outputs" / "headline.csv", "H9,0.1,,,,,,,post hoc (plan §12.5)")
    bad, _ = check_deviations.problems(root)
    assert bad == []


# ---- check_rerun and check_all ----------------------------------------------------------

def test_rerun_compares_every_file_byte_for_byte(tmp_path, monkeypatch):
    for d in ("outputs", "data/extracted"):
        (tmp_path / d).mkdir(parents=True)
    (tmp_path / "outputs" / "a.csv").write_bytes(b"x\n1\n")
    (tmp_path / "outputs" / "README.md").write_bytes(b"not generated\n")
    (tmp_path / "data" / "extracted" / "p.csv").write_bytes(b"p\n")
    made = {"a.csv": b"x\n1\n"}
    extracted = {"p.csv": b"p\n"}

    def fake(files):
        def run(root, tmp):
            tmp.mkdir(parents=True, exist_ok=True)
            for name, data in files.items():
                (tmp / name).write_bytes(data)
            return {name: tmp / name for name in files}
        return run

    monkeypatch.setattr(check_rerun, "rerun_analysis", fake(made))
    monkeypatch.setattr(check_rerun, "rerun_extraction", fake(extracted))
    monkeypatch.setattr(check_rerun, "extraction_inputs_present", lambda root: True)
    bad, notes = check_rerun.problems(tmp_path)
    assert bad == [] and len(notes) == 2 and all(n.startswith("OK") for n in notes)
    made["a.csv"] = b"x\n2\n"
    assert check_rerun.problems(tmp_path)[0] == [
        "outputs/a.csv differs from the analysis rerun"]
    del made["a.csv"]
    assert check_rerun.problems(tmp_path)[0] == [
        "outputs/a.csv is not reproduced by the analysis rerun"]
    made.update({"a.csv": b"x\n1\n", "c.csv": b"c\n"})
    assert check_rerun.problems(tmp_path)[0] == [
        "the analysis rerun produces c.csv, which is not in outputs/"]
    del made["c.csv"]
    extracted["p.csv"] = b"q\n"
    assert check_rerun.problems(tmp_path)[0] == [
        "data/extracted/p.csv differs from the extraction rerun"]
    monkeypatch.setattr(check_rerun, "extraction_inputs_present", lambda root: False)
    bad, notes = check_rerun.problems(tmp_path)
    assert bad == [] and notes[0].startswith("SKIPPED: extraction rerun")


def test_check_all_steps_and_manuscript_skips(tmp_path, monkeypatch):
    names = [n for n, _ in check_all.STEPS]
    assert names == ["pytest -q", "check_plan_order", "check_deviations",
                     "check_extraction_totals", "check_implied_denominator", "check_outputs",
                     "check_rerun", "check_online_material", "check_manuscript_numbers", "check_docx_tie",
                     "mutate_manuscript"]
    monkeypatch.setattr(check_all, "ROOT", tmp_path)
    for name in check_all.MANUSCRIPT_STEPS:
        assert check_all.skip_reason(name).startswith("SKIPPED")
    assert check_all.skip_reason("check_outputs") is None
    (tmp_path / "manuscript" / "v2").mkdir(parents=True)
    (tmp_path / "manuscript" / "v2" / "manuscript.md").write_text("x", encoding="utf-8")
    assert check_all.skip_reason("check_docx_tie") is None
    assert check_all.skip_reason("mutate_manuscript") is None
