# Adapted from hssling/india-tb-priority-tool v1.0.1 (MIT), exhibits/make_figures.py (itself adapted
# from hssling/india-tb-acf-campaign); modified: the four figures of this paper (the national
# TB-diabetes cascade, the State cascade with the decomposition class, the 2023 tiers of the three
# gaps, and the overdispersed funnel), drawn from outputs/ in greys and one colour-blind-safe blue,
# with text labels.
"""Draw the manuscript's figures from outputs/ into <manuscript folder>/exhibits/.

Run as: python -I exhibits/make_figures.py [--manuscript-dir DIR]   (default: manuscript)

Writes figure1.pdf ... figure4.pdf (vector; the build renders each to a 1000 dpi TIFF), a PNG
preview of each (figureN.png, 200 dpi, for reading the layout only) and figureN_data.csv, the
values each figure plots, read from outputs/ by the figN_data() functions (the number check
regenerates them and requires the CSVs to be identical). Needs matplotlib (3.10.7). The PDFs carry
no creation date, so a rerun gives the same bytes on the same platform.

Figure 1  the national TB-diabetes cascade by data year: C1 screened (with the Wilson interval),
          y diabetes identified among the screened, and C3 initiated on anti-diabetic treatment
          (2018: linked to an NCD clinic, drawn apart)
Figure 2  the State cascade, 2023: screening coverage C1 against identification relative to the
          benchmark expectation (C2 = y/(k_b p_u), with its interval), marked by the decomposition
          class (screening-led, identification-led, mixed)
Figure 3  the 2023 State priorities: E1, E2 and E3 (mean and 95% interval) for every unit, units
          alphabetical, the act-now tier filled
Figure 4  the overdispersed funnel of identification against the across-unit relationship with p_u
          (2023, main; 2021 and 2019), z against the number screened, Gujarat flagged
"""
from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from exhibits.formats import NATIONAL, YEARS, count, num, one, pct, read_csv, state_rows  # noqa: E402

DEFAULT_MS_DIR = "manuscript"
WIDTH = 7.48  # inches: Elsevier full-page width (190 mm)
MAIN_YEAR = "2023"
BLUE, DARK, GREY, LIGHT = "#2166ac", "#000000", "#7f7f7f", "#c8c8c8"
CLASS_MARK = {"identification-led": ("o", True), "screening-led": ("s", False), "mixed": ("^", False)}
FLAGGED = "Gujarat"


# --------------------------------------------------------------------------------------
# The data of each figure (all from outputs/)
# --------------------------------------------------------------------------------------
def fig1_data(root: Path) -> list[dict]:
    rows = []
    for r in read_csv(root, "outputs/cascade.csv"):
        if r["unit"] != NATIONAL or r["spec"] != "main":
            continue
        c3 = r["C3"] or r["C3_linked_ncd_clinic_2018"]
        rows.append({"year": r["year"], "units": r["C1_units"], "N": r["C1_n"], "K": r["C1_x"], "C1": r["C1"],
                     "C1_lo": r["C1_lo"], "C1_hi": r["C1_hi"], "D": r["y_x"], "y": r["y"], "I": r["C3_x"], "C3": c3,
                     "C3_definition": "linked to NCD clinic" if r["C3_linked_ncd_clinic_2018"] else "initiated on treatment"})
    return sorted(rows, key=lambda r: r["year"])


def fig2_data(root: Path) -> list[dict]:
    dc = {r["unit"]: r for r in read_csv(root, "outputs/decomposition.csv")
          if r["spec"] == "main" and r["year"] == MAIN_YEAR}
    cb = one(read_csv(root, "outputs/benchmark.csv"), "c_b", kind="c_b", is_main="True")["value"]
    rows = []
    for r in state_rows(read_csv(root, "outputs/cascade.csv")):
        if r["spec"] != "main" or r["year"] != MAIN_YEAR:
            continue
        rows.append({"unit": r["unit"], "N": r["N"], "C1": r["C1"], "C2": r["C2"], "C2_lo": r["C2_lo"],
                     "C2_hi": r["C2_hi"], "below_benchmark": r["below_benchmark"], "class": dc[r["unit"]]["class"],
                     "small_total_shortfall": dc[r["unit"]]["small_total_shortfall"], "c_b": cb})
    return sorted(rows, key=lambda r: r["unit"])


def fig3_data(root: Path) -> list[dict]:
    rows = []
    for r in read_csv(root, "outputs/priority.csv"):
        if r["spec"] != "main" or r["year"] != MAIN_YEAR or r["gap"] not in ("E1", "E2", "E3"):
            continue
        rows.append({"gap": r["gap"], "unit": r["unit"], "mean": r["mean"], "lo": r["lo"], "hi": r["hi"],
                     "p_top5": r["p_top5"], "tier": r["tier"]})
    return sorted(rows, key=lambda r: (r["gap"], r["unit"]))


def fig4_data(root: Path) -> list[dict]:
    rows = []
    for r in read_csv(root, "outputs/funnel.csv"):
        rows.append({"year": r["funnel_year"], "unit": r["unit"], "tested": r["tested"], "observed": r["observed"],
                     "expected": r["expected"], "z": r["z"], "lower_95": r["lower_95"], "upper_95": r["upper_95"],
                     "lower_998": r["lower_998"], "upper_998": r["upper_998"], "position": r["position"]})
    return sorted(rows, key=lambda r: (r["year"], r["unit"]))


FIGURES = {1: fig1_data, 2: fig2_data, 3: fig3_data, 4: fig4_data}


def data_csv(rows: list[dict]) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(rows[0]), lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


# --------------------------------------------------------------------------------------
# Drawing
# --------------------------------------------------------------------------------------
def setup():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 7, "axes.titlesize": 7.5, "axes.labelsize": 7,
        "xtick.labelsize": 6.5, "ytick.labelsize": 6.5, "legend.fontsize": 6.5, "axes.linewidth": 0.6,
        "xtick.major.width": 0.5, "ytick.major.width": 0.5, "pdf.fonttype": 42, "svg.hashsalt": "dmgap",
        "axes.spines.top": False, "axes.spines.right": False,
    })
    return plt


def draw1(rows: list[dict], plt):
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 2.7))
    years = [int(r["year"]) for r in rows]
    panels = [("A  Screened (C1)\nknown diabetes status among notified", "C1"),
              ("B  Identified (y)\ndiabetes among those screened", "y"),
              ("C  Initiated (C3)\ndiabetes treatment among identified", "C3")]
    for ax, (title, key) in zip(axes, panels):
        for r, yr in zip(rows, years):
            v = 100 * float(r[key])
            open_ = key == "C3" and r["C3_definition"] != "initiated on treatment"
            ax.bar(yr, v, width=0.7, color="white" if open_ else BLUE, edgecolor=BLUE, lw=0.8,
                   hatch="////" if open_ else None)
            if key == "C1":
                ax.plot([yr, yr], [100 * float(r["C1_lo"]), 100 * float(r["C1_hi"])], color=DARK, lw=0.8)
            ax.annotate(f"{num(v, 1)}%", (yr, v), xytext=(0, 2), textcoords="offset points", ha="center",
                        va="bottom", fontsize=6.3)
        ax.set_xticks(years)
        ax.set_xticklabels([str(y) for y in years])
        ax.set_title(title, loc="left", fontweight="bold", fontsize=6.8)
        top = 100 if key != "y" else 10
        ax.set_ylim(0, top * 1.1)
        ax.set_ylabel("Per cent")
        ax.set_xlabel("Data year")
    axes[2].annotate("2018: linked to\nan NCD clinic", (2018, 100 * float(rows[0]["C3"]) + 7), xytext=(2018, 88),
                     ha="center", va="bottom", fontsize=5.6,
                     arrowprops=dict(arrowstyle="-", lw=0.5, color=DARK))
    fig.subplots_adjust(left=0.065, right=0.99, top=0.84, bottom=0.15, wspace=0.32)
    return fig


CODE = {  # two-letter codes of the 33 units (Figure 2; the key is in the caption)
    "Andaman and Nicobar Islands": "AN", "Andhra Pradesh": "AP", "Arunachal Pradesh": "AR", "Assam": "AS",
    "Bihar": "BR", "Chandigarh": "CH", "Chhattisgarh": "CG", "Delhi": "DL", "Goa": "GA", "Gujarat": "GJ",
    "Haryana": "HR", "Himachal Pradesh": "HP", "Jammu and Kashmir": "JK", "Jharkhand": "JH", "Karnataka": "KA",
    "Kerala": "KL", "Madhya Pradesh": "MP", "Maharashtra": "MH", "Manipur": "MN", "Meghalaya": "ML", "Mizoram": "MZ",
    "Nagaland": "NL", "Odisha": "OD", "Puducherry": "PY", "Punjab": "PB", "Rajasthan": "RJ", "Sikkim": "SK",
    "Tamil Nadu": "TN", "Telangana": "TG", "Tripura": "TR", "Uttar Pradesh": "UP", "Uttarakhand": "UK",
    "West Bengal": "WB",
}


def place_labels(ax, pts: list[tuple[float, float, str]], fig) -> None:
    """Two-letter labels beside the points, each in the first free place among right, left, above
    and below (display coordinates, so that no two labels overlap and none covers a marker)."""
    fig.canvas.draw()
    tr = ax.transData
    disp = [tr.transform((x, y)) for x, y, _ in pts]
    w, h, gap = 10.5, 7.0, 4.5  # label box (pixels at 100 dpi) and the gap to the marker
    boxes: list[tuple[float, float, float, float]] = [(px - 3.5, py - 3.5, px + 3.5, py + 3.5) for px, py in disp]

    def free(b) -> bool:
        return all(b[2] <= o[0] or b[0] >= o[2] or b[3] <= o[1] or b[1] >= o[3] for o in boxes)

    order = sorted(range(len(pts)), key=lambda k: (disp[k][0], disp[k][1]))
    for k in order:
        px, py = disp[k]
        cands = [(px + gap, py - h / 2, "left", "center", gap, 0), (px - gap - w, py - h / 2, "right", "center", -gap, 0),
                 (px - w / 2, py + gap, "center", "bottom", 0, gap), (px - w / 2, py - gap - h, "center", "top", 0, -gap),
                 (px + gap, py + gap, "left", "bottom", gap, gap), (px + gap, py - gap - h, "left", "top", gap, -gap),
                 (px - gap - w, py + gap, "right", "bottom", -gap, gap), (px - gap - w, py - gap - h, "right", "top", -gap, -gap)]
        chosen = cands[0]
        for c in cands:
            b = (c[0], c[1], c[0] + w, c[1] + h)
            if free(b):
                chosen = c
                break
        x0, y0 = chosen[0], chosen[1]
        boxes.append((x0, y0, x0 + w, y0 + h))
        x, y, lab = pts[k]
        dpi = fig.dpi / 72.0
        ax.annotate(lab, (x, y), xytext=(chosen[4] / dpi, chosen[5] / dpi), textcoords="offset points", fontsize=5.6,
                    ha=chosen[2], va=chosen[3])


def draw2(rows: list[dict], plt):
    fig, ax = plt.subplots(figsize=(WIDTH, 4.4), dpi=100)
    cb = 100 * float(rows[0]["c_b"])
    ax.axhline(1.0, color=BLUE, ls="--", lw=1.0, zorder=1)
    ax.axvline(cb, color=GREY, ls=":", lw=0.9, zorder=1)
    pts = []
    for r in rows:
        x = 100 * float(r["C1"])
        y, lo, hi = float(r["C2"]), float(r["C2_lo"]), float(r["C2_hi"])
        m, filled = CLASS_MARK[r["class"]]
        ax.plot([x, x], [lo, hi], color=LIGHT, lw=0.8, zorder=2)
        ax.plot(x, y, marker=m, ms=4.5, mfc=DARK if filled else "white", mec=DARK, mew=0.8, ls="", zorder=3)
        pts.append((x, y, CODE[r["unit"]]))
    ax.set_yscale("log")
    ticks = [0.3, 0.5, 0.7, 1.0, 1.5, 2.0]
    ax.set_yticks(ticks)
    ax.set_yticklabels([num(t, 1) for t in ticks])
    ax.minorticks_off()
    xs = [100 * float(r["C1"]) for r in rows]
    ax.set_xlim(min(xs) - 3, 100.5)
    ax.set_ylim(0.22, 2.3)
    ax.set_xlabel("C1: TB patients screened for diabetes, per cent of notified (2023)")
    ax.set_ylabel("C2: identification relative to the benchmark (log scale)")
    ax.text(min(xs) - 2.6, 1.03, "identification at the benchmark (C2 = 1)", color=BLUE, fontsize=6, va="bottom")
    ax.text(cb - 0.3, 0.23, f"benchmark coverage {num(cb, 1)}%", color=GREY, fontsize=6, ha="right", va="bottom")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], marker=CLASS_MARK[c][0], ls="", mfc=DARK if CLASS_MARK[c][1] else "white", mec=DARK, ms=4.5)
         for c in ("identification-led", "screening-led", "mixed")]
    n = {c: sum(r["class"] == c for r in rows) for c in CLASS_MARK}
    ax.legend(h, [f"identification-led ({n['identification-led']})", f"screening-led ({n['screening-led']})",
                  f"mixed ({n['mixed']})"], loc="upper left", frameon=False, title="Where the shortfall lies, 2023",
              title_fontsize=6.5)
    fig.subplots_adjust(left=0.08, right=0.985, top=0.97, bottom=0.11)
    place_labels(ax, pts, fig)
    return fig


GAP_TITLE = {"E1": "A  E1, screening gap|expected among those not screened",
             "E2": "B  E2, identification gap|expected among those screened",
             "E3": "C  E3, linkage gap|identified, not started on treatment"}


def draw3(rows: list[dict], plt):
    units = sorted({r["unit"] for r in rows})
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 6.4), sharey=True)
    for ax, g in zip(axes, ("E1", "E2", "E3")):
        cell = {r["unit"]: r for r in rows if r["gap"] == g}
        for i, u in enumerate(units):
            r = cell[u]
            act = r["tier"] == "act now"
            mean, lo, hi = float(r["mean"]), float(r["lo"]), float(r["hi"])
            ax.plot([lo, hi], [i, i], color=DARK, lw=1.0, solid_capstyle="butt")
            ax.plot(mean, i, marker="o", ms=3.6 if act else 2.8, mfc=BLUE if act else "white", mec=BLUE if act else GREY,
                    mew=0.7, ls="")
            if act:
                ax.annotate("act now", (hi, i), xytext=(3, 0), textcoords="offset points", va="center", fontsize=5.6,
                            color=BLUE)
        ax.set_ylim(len(units) - 0.4, -0.6)
        ax.set_yticks(range(len(units)))
        ax.set_yticklabels(units)
        xmax = max(float(r["hi"]) for r in cell.values())
        ax.set_xlim(0, xmax * 1.3)
        ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.tick_params(axis="x", labelrotation=0)
        ax.set_title(GAP_TITLE[g].replace("|", chr(10)), loc="left", fontweight="bold", fontsize=6.4)
        ax.set_xlabel("TB patients with diabetes, 2023")
        ax.grid(axis="y", color="#eeeeee", lw=0.5)
        ax.set_axisbelow(True)
    fig.subplots_adjust(left=0.2, right=0.985, top=0.94, bottom=0.07, wspace=0.12)
    return fig


def draw4(rows: list[dict], plt):
    fig, axes = plt.subplots(1, 3, figsize=(WIDTH, 3.1), sharey=True)
    titles = {"2023": "A  2023 (main; 2023 regression)", "2021": "B  2021 (2019 and 2021 regression)",
              "2019": "C  2019 (2019 and 2021 regression)"}
    ymax = max(abs(float(r["z"])) for r in rows) * 1.15
    for ax, y in zip(axes, ("2023", "2021", "2019")):
        rs = [r for r in rows if r["year"] == y]
        l95, l998 = float(rs[0]["upper_95"]), float(rs[0]["upper_998"])
        xs = [float(r["tested"]) for r in rs]
        x0, x1 = min(xs) / 1.6, max(xs) * 1.6
        ax.set_xscale("log")
        ax.axhline(0, color=GREY, lw=0.7)
        for lim, ls in ((l95, ":"), (l998, "-")):
            ax.plot([x0, x1], [lim, lim], color=BLUE, ls=ls, lw=0.9)
            ax.plot([x0, x1], [-lim, -lim], color=BLUE, ls=ls, lw=0.9)
        for r in rs:
            z, x = float(r["z"]), float(r["tested"])
            beyond = r["position"] in ("below the 99.8% limit", "above the 99.8% limit")
            flagged = r["unit"] == FLAGGED
            ax.plot(x, z, marker="v" if flagged else "o", ms=5 if flagged else 3.2,
                    mfc=DARK if beyond else "white", mec=DARK if beyond else GREY, mew=0.7, ls="", zorder=3)
            if beyond:
                ax.annotate(r["unit"], (x, z), xytext=(-4, 0), textcoords="offset points", ha="right", va="center",
                            fontsize=6, fontweight="bold" if flagged else "normal")
        ax.set_xlim(x0, x1)
        ax.set_ylim(-ymax, ymax)
        ax.set_title(titles[y], loc="left", fontweight="bold", fontsize=6.6)
        ax.set_xlabel("TB patients screened (log scale)")
    axes[0].set_ylabel("z: identified minus expected, standardised")
    from matplotlib.lines import Line2D
    h = [Line2D([], [], color=BLUE, lw=0.9), Line2D([], [], color=BLUE, ls=":", lw=0.9),
         Line2D([], [], marker="o", ls="", mfc=DARK, mec=DARK, ms=3.2), Line2D([], [], marker="v", ls="", mfc=DARK,
                                                                             mec=DARK, ms=5)]
    fig.legend(h, ["99.8% limits, widened for overdispersion", "95% limits, widened", "beyond the 99.8% limits",
                   f"{FLAGGED}"], loc="lower center", ncol=4, frameon=False, fontsize=6.2)
    fig.subplots_adjust(left=0.08, right=0.99, top=0.9, bottom=0.25, wspace=0.08)
    return fig


DRAW = {1: draw1, 2: draw2, 3: draw3, 4: draw4}


def write(ms_dir: Path, root: Path = ROOT, png: bool = True) -> list[str]:
    plt = setup()
    ex = ms_dir / "exhibits"
    ex.mkdir(parents=True, exist_ok=True)
    out = []
    for k, fn in FIGURES.items():
        rows = fn(root)
        (ex / f"figure{k}_data.csv").write_bytes(data_csv(rows))
        fig = DRAW[k](rows, plt)
        fig.savefig(ex / f"figure{k}.pdf", metadata={"CreationDate": None, "Creator": None, "Producer": None})
        if png:
            fig.savefig(ex / f"figure{k}.png", dpi=200)
        plt.close(fig)
        out.append(f"figure{k}.pdf: {len(rows)} data rows")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    ap.add_argument("--manuscript-dir", default=DEFAULT_MS_DIR)
    a = ap.parse_args(argv)
    d = Path(a.manuscript_dir)
    d = d if d.is_absolute() else ROOT / d
    for ln in write(d):
        print(ln)
    return 0


if __name__ == "__main__":
    sys.exit(main())
