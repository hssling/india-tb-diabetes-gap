# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), manuscript/make_graphical_abstract.py
# (private there); modified: committed here, and drawn from outputs/ only: the 2023 national
# TB-diabetes cascade, where the shortfall lies, the units that start fewer than half of those
# identified on diabetes treatment, and the act-now units of the three gaps.
"""Draw the optional graphical abstract from outputs/ into <manuscript folder>/exhibits/.

Run as: python -I exhibits/make_graphical_abstract.py [--manuscript-dir DIR]   (default: manuscript)

Writes graphical_abstract.pdf (vector), graphical_abstract.png (preview) and
graphical_abstract_data.csv (every value it prints, read from outputs/; the number check
regenerates the CSV). The page is 13.28 x 5.31 inches, so the build's 300 dpi TIFF is 3984 x 1593
pixels, more than Elsevier's minimum of 1328 x 531, and the text stays readable at 13 x 5 cm.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exhibits.formats import NATIONAL, count, one, pct, read_csv  # noqa: E402
from exhibits.make_figures import BLUE, DARK, GREY, data_csv, setup  # noqa: E402

DEFAULT_MS_DIR = "manuscript"
SIZE = (13.28, 5.31)  # inches
YEAR = "2023"


def ga_data(root: Path) -> list[dict]:
    """(item, value) rows: every value the graphical abstract prints."""
    ca = read_csv(root, "outputs/cascade.csv")
    n = one(ca, "national 2023", unit=NATIONAL, year=YEAR, spec="main")
    rows = [{"item": "units", "value": n["C1_units"]},
            {"item": "notified", "value": n["C1_n"]}, {"item": "screened", "value": n["C1_x"]},
            {"item": "C1", "value": n["C1"]}, {"item": "identified", "value": n["y_x"]},
            {"item": "y", "value": n["y"]}, {"item": "initiated", "value": n["C3_x"]}, {"item": "C3", "value": n["C3"]}]
    dc = [r for r in read_csv(root, "outputs/decomposition.csv") if r["spec"] == "main" and r["year"] == YEAR]
    for c in ("identification-led", "screening-led", "mixed"):
        rows.append({"item": f"class {c}", "value": str(sum(r["class"] == c for r in dc))})
    st = [r for r in ca if r["unit"] != NATIONAL and r["spec"] == "main" and r["year"] == YEAR]
    rows.append({"item": "C3 below half", "value": str(sum(float(r["C3"]) < 0.5 for r in st))})
    pr = [r for r in read_csv(root, "outputs/priority.csv") if r["spec"] == "main" and r["year"] == YEAR]
    for g in ("E1", "E2", "E3"):
        names = sorted(r["unit"] for r in pr if r["gap"] == g and r["tier"] == "act now")
        rows.append({"item": f"act now {g}", "value": "; ".join(names)})
    sc = one(read_csv(root, "outputs/scenario.csv"), "scenario", spec="main", row="national")
    rows.append({"item": "scenario", "value": sc["mean"]})
    return rows


def draw(rows: list[dict], plt):
    v = {r["item"]: r["value"] for r in rows}
    red = "#b2182b"
    fig = plt.figure(figsize=SIZE)
    fig.text(0.015, 0.93, f"The TB–diabetes care cascade in India's States, {YEAR}", fontsize=24, fontweight="bold",
             va="center")
    fig.text(0.015, 0.855, f"{v['units']} States and Union Territories; India TB Report tables and NFHS-5; "
             "pre-registered; observational", fontsize=15, color=GREY, va="center")
    # Panel 1: the national cascade
    steps = [("Screened for diabetes", float(v["C1"]), f"{count(v['screened'])} of {count(v['notified'])} notified"),
             ("Diabetes identified", float(v["y"]), f"{count(v['identified'])} of those screened"),
             ("Started on treatment", float(v["C3"]), f"{count(v['initiated'])} of those identified")]
    for i, (lab, share, sub) in enumerate(steps):
        top = 0.755 - i * 0.235
        fig.text(0.02, top, lab, fontsize=16, fontweight="bold", va="center")
        fig.text(0.02, top - 0.165, sub, fontsize=12.5, color=GREY, va="center")
        ax = fig.add_axes((0.02, top - 0.13, 0.355, 0.085))
        ax.barh(0, 1.0, height=1, color="#e6eef7", edgecolor="none")
        ax.barh(0, share, height=1, color=BLUE if i != 2 else red, edgecolor="none")
        inside = share >= 0.3
        ax.text(0.02 if inside else share + 0.02, 0, pct(share), fontsize=19, fontweight="bold", va="center",
                color="white" if inside else DARK)
        ax.set_xlim(0, 1)
        ax.set_ylim(-0.5, 0.5)
        ax.axis("off")
    # Panel 2: where the shortfall lies
    fig.text(0.415, 0.74, "Where the shortfall lies", fontsize=18, fontweight="bold", va="center")
    lines = [(v["class identification-led"], "units identification-led", "check testing and recording", BLUE),
             (v["class screening-led"], "units screening-led", "screen more TB patients", BLUE),
             (v["class mixed"], "units mixed", "", BLUE),
             (v["C3 below half"], "units start fewer than half", "of those identified on treatment", red)]
    for i, (n, what, act, col) in enumerate(lines):
        y = 0.61 - i * 0.135
        fig.text(0.415, y, n, fontsize=25, fontweight="bold", color=col, va="center")
        fig.text(0.46, y + (0.022 if act else 0), what, fontsize=14, va="center")
        if act:
            fig.text(0.46, y - 0.03, act, fontsize=12.5, color=GREY, va="center", style="italic")
    # Panel 3: act now
    fig.text(0.725, 0.74, "Act now (tiers, not ranks)", fontsize=18, fontweight="bold", va="center")
    for i, (g, lab) in enumerate((("E1", "Screening gap"), ("E2", "Identification gap"), ("E3", "Linkage gap"))):
        y = 0.64 - i * 0.185
        fig.text(0.725, y, lab, fontsize=14.5, fontweight="bold", va="center", color=red if g == "E3" else DARK)
        names = v[f"act now {g}"].split("; ")
        fig.text(0.725, y - 0.035, ", ".join(names[:3]) + ",\n" + ", ".join(names[3:]), fontsize=12, va="top",
                 linespacing=1.15)
    fig.text(0.415, 0.06, f"Illustration, not a forecast: about {count(round(float(v['scenario']), -2))} more TB "
             "patients with diabetes\nidentified per year if every unit reached the benchmark coverage and yield.",
             fontsize=12.5, color=GREY, va="center")
    return fig


def write(ms_dir: Path, root: Path = ROOT) -> str:
    plt = setup()
    ex = ms_dir / "exhibits"
    ex.mkdir(parents=True, exist_ok=True)
    rows = ga_data(root)
    (ex / "graphical_abstract_data.csv").write_bytes(data_csv(rows))
    fig = draw(rows, plt)
    fig.savefig(ex / "graphical_abstract.pdf", metadata={"CreationDate": None, "Creator": None, "Producer": None})
    fig.savefig(ex / "graphical_abstract.png", dpi=100)
    plt.close(fig)
    return f"graphical_abstract.pdf: {len(rows)} values"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    ap.add_argument("--manuscript-dir", default=DEFAULT_MS_DIR)
    a = ap.parse_args(argv)
    d = Path(a.manuscript_dir)
    print(write(d if d.is_absolute() else ROOT / d))
    return 0


if __name__ == "__main__":
    sys.exit(main())
