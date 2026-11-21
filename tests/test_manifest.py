"""Every source in data/source_manifest.csv is present in data_raw/ with the
recorded size and SHA-256 (the copies made by tools/fetch_sources.py), and the
manifest lists exactly the sources the plan names (seven files, plan
section 3.1, ITR 2020 included), with the NFHS-5 digests
given in the design (section 3)."""
import csv
import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "source_manifest.csv"
COLUMNS = ["path", "origin", "bytes", "sha256"]

EXPECTED_PATHS = {
    "data_raw/india_tb_report/India-TB-Report-2019.pdf",
    "data_raw/india_tb_report/ITR2020.pdf",
    "data_raw/india_tb_report/TBAnnaulReport2022.pdf",
    "data_raw/india_tb_report/ITR2023.pdf",
    "data_raw/india_tb_report/ITR2024.pdf",
    "data_raw/nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-I.pdf",
    "data_raw/nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-II.pdf",
}
# Design, section 3 (pinned when the compendiums were downloaded, 21 Nov 2026).
NFHS_DIGESTS = {
    "data_raw/nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-I.pdf":
        "5bcc2a37b13ffc0203d736803f72aece88b4beb0bc168d1f069e110178ab2bd7",
    "data_raw/nfhs5/NFHS-5_India_and_State_Factsheet_Compendium_Phase-II.pdf":
        "3e8ee12bb4a59e9ec2e7bebc736b2252d61e9ed98ce322717debe11dd73c52b7",
}


def _rows() -> list[dict]:
    with open(MANIFEST, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == COLUMNS
        return list(reader)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def test_manifest_has_rows_and_unique_paths():
    rows = _rows()
    paths = [r["path"] for r in rows]
    assert len(paths) == len(set(paths))
    assert set(paths) == EXPECTED_PATHS
    assert len(paths) == 7
    for r in rows:
        assert r["path"].startswith("data_raw/"), r["path"]
        assert len(r["sha256"]) == 64 and r["origin"], r


def test_manifest_nfhs_digests_are_the_designs():
    by_path = {r["path"]: r["sha256"] for r in _rows()}
    for path, digest in NFHS_DIGESTS.items():
        assert by_path[path] == digest, path


def test_manifest_digests_match():
    if not (ROOT / "data_raw").is_dir():
        pytest.skip("data_raw/ is not distributed; run python -I tools/fetch_sources.py")
    for r in _rows():
        path = ROOT / r["path"]
        assert path.is_file(), f"missing: {r['path']}"
        assert path.stat().st_size == int(r["bytes"]), r["path"]
        assert _sha256(path) == r["sha256"], r["path"]


def test_manifest_itr2020_digest_is_the_plans():
    by_path = {r["path"]: r["sha256"] for r in _rows()}
    assert by_path["data_raw/india_tb_report/ITR2020.pdf"] == (
        "63b9408015dae510858e0eef2711e809d398bfe3149dd21c94390b258c007e7e")
