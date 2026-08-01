"""
CLI entry point for the pre-validation stratified sampling stage.

Draws a topic_group-stratified random sample of `idx` (equal allocation,
without replacement), expands it into a 9-record review pack per idx
(1 neutral + 8 emotional variants), and writes:

- ``sampling/sampled_idx.csv``         minimal idx -> topic_group table
- ``sampling/human_validation_pack.csv`` long-form 9-row-per-idx pack
- ``sampling/sampling_report.md``      reproducibility report
- ``sampling/manifest.json``           machine-readable sidecar for downstream

Downstream runners (`run_validation.py`, `run_reliability.py`) consume
``sampled_idx.csv`` via the ``--use-sample`` flag.

Usage:
  python run_stratified_sampling.py
  python run_stratified_sampling.py --per-stratum 20 --seed 20260514
  python run_stratified_sampling.py --output-dir ./sampling --reference /path/to/topic.csv
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from config import (
    HUMAN_VALIDATION_PACK_CSV,
    NEUTRAL_CSV,
    PER_STRATUM_DEFAULT,
    SAMPLED_IDX_CSV,
    SAMPLE_SEED,
    SAMPLING_DIR,
    SAMPLING_MANIFEST_JSON,
    SAMPLING_REPORT_MD,
    TOPIC_REFERENCE_CSV,
    VARIANT_FILES,
    ensure_dirs,
)
from dataset_loader import load_variants
from sampling import (
    IDX_COL,
    NEUTRAL_MODEL_TAG,
    TOPIC_COL,
    build_review_pack,
    collect_source_file_stats,
    compute_eligible_idx,
    load_topic_reference,
    missing_idx_by_source,
    stratified_sample,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _format_source_table(stats) -> str:
    header = "| model_tag | role | source_file | n_in_file | n_with_text | n_idx_matched |"
    sep = "|---|---|---|---:|---:|---:|"
    rows = [header, sep]
    for s in stats:
        rows.append(
            f"| {s.model_tag} | {s.role} | {s.source_file} | "
            f"{s.n_in_file} | {s.n_with_text} | {s.n_idx_matched} |"
        )
    return "\n".join(rows)


def _format_stratum_table(
    eligible: pd.DataFrame,
    sample: pd.DataFrame,
    pack: pd.DataFrame,
) -> str:
    pop = eligible.groupby(TOPIC_COL).size().rename("population_size")
    drawn = sample.groupby(TOPIC_COL).size().rename("drawn")
    topic_text_len = (
        pack[pack["role"] == "neutral"]
        .assign(_len=lambda d: d["situation"].astype(str).str.len())
        .groupby("topic_group")["_len"]
        .mean()
        .round(1)
        .rename("mean_topic_len_chars")
    )
    table = pd.concat([pop, drawn, topic_text_len], axis=1).fillna(0).astype(
        {"population_size": int, "drawn": int}
    )
    table = table.sort_index()

    header = "| stratum | population_size | drawn | mean_topic_len_chars |"
    sep = "|---|---:|---:|---:|"
    rows = [header, sep]
    for stratum, row in table.iterrows():
        rows.append(
            f"| {stratum} | {int(row['population_size'])} | {int(row['drawn'])} | "
            f"{float(row['mean_topic_len_chars']):.1f} |"
        )
    return "\n".join(rows)


def _format_missing_section(missing: dict[str, list[str]]) -> str:
    lines = []
    for tag, ids in missing.items():
        lines.append(f"- **{tag}**: {len(ids)} missing idx")
        if ids:
            preview = ", ".join(ids[:10])
            more = "" if len(ids) <= 10 else f" (... +{len(ids) - 10} more)"
            lines.append(f"  - first: {preview}{more}")
    return "\n".join(lines) if lines else "(none)"


def _write_sampled_idx_csv(
    sample: pd.DataFrame,
    *,
    seed: int,
    per_stratum: int,
    drawn_at: str,
    path: Path,
) -> None:
    out = sample.copy()
    out["seed"] = seed
    out["per_stratum_quota"] = per_stratum
    out["drawn_at_iso"] = drawn_at
    out = out[[IDX_COL, TOPIC_COL, "seed", "per_stratum_quota", "drawn_at_iso"]]
    out.to_csv(path, index=False)


def _write_manifest(
    *,
    seed: int,
    per_stratum: int,
    sample: pd.DataFrame,
    drawn_at: str,
    path: Path,
) -> None:
    sources = [
        {
            "model_tag": NEUTRAL_MODEL_TAG,
            "role": "neutral",
            "source_path": str(NEUTRAL_CSV),
            "sha256": _sha256_file(NEUTRAL_CSV),
        }
    ]
    for tag, src in VARIANT_FILES:
        sources.append(
            {
                "model_tag": tag,
                "role": "emotional",
                "source_path": str(src),
                "sha256": _sha256_file(src),
            }
        )
    payload = {
        "seed": seed,
        "per_stratum": per_stratum,
        "n_sampled_idx": int(len(sample)),
        "n_strata": int(sample[TOPIC_COL].nunique()),
        "drawn_at_iso": drawn_at,
        "sources": sources,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_report(
    *,
    path: Path,
    seed: int,
    per_stratum: int,
    drawn_at: str,
    n_reference: int,
    n_eligible: int,
    stats,
    missing: dict[str, list[str]],
    stratum_table: str,
    sample: pd.DataFrame,
    pack: pd.DataFrame,
    command: str,
) -> None:
    lines: list[str] = []
    lines.append("# Stratified Sampling Report")
    lines.append("")
    lines.append(f"- Run timestamp (UTC): `{drawn_at}`")
    lines.append(f"- Sample seed: `{seed}`")
    lines.append(f"- Per-stratum quota: `{per_stratum}`")
    lines.append(f"- Strata: `{sample[TOPIC_COL].nunique()}`")
    lines.append(f"- Reference idx (unique): `{n_reference}`")
    lines.append(f"- Eligible idx (intersection across neutral + 8 variants): `{n_eligible}`")
    lines.append(f"- Sampled idx: `{len(sample)}`")
    lines.append(
        f"- Review pack rows: `{len(pack)}` "
        f"(= {len(sample)} idx x 9 rows = {len(sample) * 9})"
    )
    lines.append("")
    lines.append("## Source files (1 neutral + 8 emotional)")
    lines.append("")
    lines.append(_format_source_table(stats))
    lines.append("")
    lines.append("## Reference idx missing from each source")
    lines.append("")
    lines.append(_format_missing_section(missing))
    lines.append("")
    lines.append("## Per-stratum draw")
    lines.append("")
    lines.append(stratum_table)
    lines.append("")
    lines.append("## Final totals")
    lines.append("")
    lines.append(
        f"- {len(sample)} idx x 9 rows = {len(sample) * 9} rows in `human_validation_pack.csv`"
    )
    lines.append(
        f"- Main census calls if `--use-sample`: {len(sample)} x 8 = {len(sample) * 8}"
    )
    lines.append("")
    lines.append("## Reproducibility")
    lines.append("")
    lines.append(f"- Command: `{command}`")
    lines.append(f"- Seed: `{seed}` (config.SAMPLE_SEED)")
    lines.append(
        "- Method: equal-allocation stratified sample on `topic_group`, "
        "without replacement, via `numpy.random.default_rng(seed)` -> "
        "`DataFrame.sample(random_state=...)`."
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _print_summary(
    *,
    stats,
    n_eligible: int,
    sample: pd.DataFrame,
    pack: pd.DataFrame,
    out_idx: Path,
    out_pack: Path,
    out_report: Path,
    out_manifest: Path,
) -> None:
    print("Source files:")
    print(_format_source_table(stats))
    print()
    print(f"Eligible idx (intersection): {n_eligible}")
    print(f"Sampled idx: {len(sample)} across {sample[TOPIC_COL].nunique()} strata")
    print(f"Review pack rows: {len(pack)}")
    print()
    print("Per-stratum draw:")
    counts = sample.groupby(TOPIC_COL).size().sort_index()
    for stratum, n in counts.items():
        print(f"  {stratum}: drawn={n}")
    print()
    print("Outputs:")
    print(f"  {out_idx}")
    print(f"  {out_pack}")
    print(f"  {out_report}")
    print(f"  {out_manifest}")


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Draw a topic_group-stratified random sample of idx and build "
            "the 9-row-per-idx human validation pack."
        )
    )
    parser.add_argument(
        "--per-stratum",
        type=int,
        default=PER_STRATUM_DEFAULT,
        help="Number of idx to draw per stratum (default %(default)s).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=SAMPLE_SEED,
        help="RNG seed (default config.SAMPLE_SEED = %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=SAMPLING_DIR,
        help="Where to write outputs (default %(default)s).",
    )
    parser.add_argument(
        "--reference",
        type=Path,
        default=TOPIC_REFERENCE_CSV,
        help="Topic-stratification reference CSV (default %(default)s).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    ensure_dirs()
    out_dir: Path = args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    out_idx = (
        SAMPLED_IDX_CSV if out_dir == SAMPLING_DIR else out_dir / SAMPLED_IDX_CSV.name
    )
    out_pack = (
        HUMAN_VALIDATION_PACK_CSV
        if out_dir == SAMPLING_DIR
        else out_dir / HUMAN_VALIDATION_PACK_CSV.name
    )
    out_report = (
        SAMPLING_REPORT_MD
        if out_dir == SAMPLING_DIR
        else out_dir / SAMPLING_REPORT_MD.name
    )
    out_manifest = (
        SAMPLING_MANIFEST_JSON
        if out_dir == SAMPLING_DIR
        else out_dir / SAMPLING_MANIFEST_JSON.name
    )

    drawn_at = _now_iso()
    reference = load_topic_reference(args.reference)
    variants, neutral, _coverage = load_variants()
    eligible = compute_eligible_idx(reference, variants, neutral)
    eligible_idx_set = set(eligible[IDX_COL].astype(str))

    if eligible.empty:
        print("ERROR: zero eligible idx after intersection.", file=sys.stderr)
        return 4

    sample = stratified_sample(
        eligible, per_stratum=args.per_stratum, seed=args.seed
    )
    pack = build_review_pack(sample, neutral, variants)

    _write_sampled_idx_csv(
        sample,
        seed=args.seed,
        per_stratum=args.per_stratum,
        drawn_at=drawn_at,
        path=out_idx,
    )
    pack.to_csv(out_pack, index=False)
    _write_manifest(
        seed=args.seed,
        per_stratum=args.per_stratum,
        sample=sample,
        drawn_at=drawn_at,
        path=out_manifest,
    )

    stats = collect_source_file_stats(variants, neutral, eligible_idx_set)
    missing = missing_idx_by_source(variants, neutral, reference)
    stratum_table = _format_stratum_table(eligible, sample, pack)
    command = (
        f"python run_stratified_sampling.py --per-stratum {args.per_stratum} "
        f"--seed {args.seed}"
    )
    _write_report(
        path=out_report,
        seed=args.seed,
        per_stratum=args.per_stratum,
        drawn_at=drawn_at,
        n_reference=len(reference),
        n_eligible=len(eligible),
        stats=stats,
        missing=missing,
        stratum_table=stratum_table,
        sample=sample,
        pack=pack,
        command=command,
    )

    _print_summary(
        stats=stats,
        n_eligible=len(eligible),
        sample=sample,
        pack=pack,
        out_idx=out_idx,
        out_pack=out_pack,
        out_report=out_report,
        out_manifest=out_manifest,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
