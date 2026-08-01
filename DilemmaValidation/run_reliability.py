"""
Test-retest reliability runner.

For each variant:
  1. Read run-1 JSONL from results/raw/<variant>.jsonl.
  2. Compute item_quality per item.
  3. Stratify by item_quality quartile and sample 10% per variant with the
     seeded RNG (random_state=20260519).
  4. Re-run those items via the same call_gemini path.
  5. Write to results/raw/<variant>_retest.jsonl.

Usage:
  python run_reliability.py
  python run_reliability.py --variants CN,CT --workers 8
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from tqdm import tqdm

from config import (
    CB_CONSECUTIVE,
    CB_FAILURE_RATE,
    CB_MIN_SAMPLES,
    CB_WINDOW,
    DEFAULT_WORKERS,
    RANDOM_STATE,
    RELIABILITY_FRACTION,
    RUN_LOG,
    SAMPLED_IDX_CSV,
    VARIANT_KEYS,
    W_COHERENCE,
    W_NATURALNESS,
    W_SEMANTIC,
    ensure_dirs,
    get_api_key,
    raw_jsonl_path,
)
from dataset_loader import build_join_table, load_variants
from run_validation import (
    CircuitBreaker,
    _append_failure,
    _load_done_idx,
    _load_sampled_idx,
    _open_jsonl,
    _process_item,
    _trip_and_cancel,
)


def _configure_logging() -> None:
    RUN_LOG.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(RUN_LOG, encoding="utf-8"),
            logging.StreamHandler(sys.stderr),
        ],
    )


def _read_run1(variant: str) -> pd.DataFrame:
    path = raw_jsonl_path(variant, run=1)
    if not path.is_file():
        raise FileNotFoundError(
            f"Run-1 JSONL missing for variant {variant}: {path}. "
            "Run run_validation.py first."
        )
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    df = pd.DataFrame(rows)
    return df


def _compute_item_quality(df: pd.DataFrame) -> pd.DataFrame:
    """Add an item_quality column on a copy of df. NaN-tolerant."""
    out = df.copy()
    sim = pd.to_numeric(out.get("semantic_sim"), errors="coerce")
    nat = pd.to_numeric(out.get("emotion_naturalness"), errors="coerce")
    coh = pd.to_numeric(out.get("emotion_coherence"), errors="coerce")
    out["item_quality"] = (
        W_SEMANTIC * sim + W_NATURALNESS * (nat / 5.0) + W_COHERENCE * (coh / 5.0)
    )
    return out


def _stratified_sample(
    df: pd.DataFrame,
    *,
    fraction: float,
    seed: int,
) -> pd.DataFrame:
    """
    Stratify df by item_quality quartile and draw a per-stratum proportional sample.
    Items with missing item_quality are placed in a separate stratum and sampled too.
    """
    rng = np.random.default_rng(seed)
    scored = df.dropna(subset=["item_quality"]).copy()
    unscored = df[df["item_quality"].isna()].copy()

    sampled_parts: list[pd.DataFrame] = []

    if not scored.empty:
        try:
            scored["_quartile"] = pd.qcut(
                scored["item_quality"], q=4, labels=False, duplicates="drop"
            )
        except ValueError:
            scored["_quartile"] = 0
        for _, group in scored.groupby("_quartile"):
            n_take = max(1, int(round(len(group) * fraction)))
            n_take = min(n_take, len(group))
            picked = group.sample(n=n_take, random_state=int(rng.integers(0, 2**32 - 1)))
            sampled_parts.append(picked.drop(columns=["_quartile"]))

    if not unscored.empty:
        n_take = max(1, int(round(len(unscored) * fraction)))
        n_take = min(n_take, len(unscored))
        picked = unscored.sample(n=n_take, random_state=int(rng.integers(0, 2**32 - 1)))
        sampled_parts.append(picked)

    if not sampled_parts:
        return df.head(0)

    sample = pd.concat(sampled_parts, ignore_index=True)
    return sample.sort_values(by="idx", kind="stable").reset_index(drop=True)


def _select_retest_items(
    variants_to_run: list[str],
    *,
    fraction: float,
    seed: int,
    resume: bool,
    sample_idx: set[str] | None = None,
) -> dict[str, list[str]]:
    """Return dict {variant -> list of idx strings to retest}.

    When ``sample_idx`` is provided, the run-1 frame is filtered to that idx
    set before the item_quality-quartile stratification runs, so the retest
    pool is drawn from the sampled idx only (not the full 1,360).
    """
    out: dict[str, list[str]] = {}
    for variant in variants_to_run:
        df = _read_run1(variant)
        if df.empty:
            out[variant] = []
            continue
        if sample_idx is not None:
            df = df[df["idx"].astype(str).isin(sample_idx)].copy()
            if df.empty:
                out[variant] = []
                continue
        df = _compute_item_quality(df)
        sample = _stratified_sample(df, fraction=fraction, seed=seed)
        ids = [str(x) for x in sample["idx"].tolist()]
        if resume:
            done = _load_done_idx(raw_jsonl_path(variant, run=2))
            ids = [x for x in ids if x not in done]
        out[variant] = ids
    return out


def _interleave(items_by_variant: dict[str, list[tuple[str, dict]]]) -> list[tuple[str, dict]]:
    iters = {k: iter(v) for k, v in items_by_variant.items() if v}
    out: list[tuple[str, dict]] = []
    while iters:
        for key in list(iters.keys()):
            try:
                out.append(next(iters[key]))
            except StopIteration:
                iters.pop(key)
    return out


def run_retest(
    variants_to_run: list[str],
    *,
    workers: int,
    fraction: float,
    seed: int,
    resume: bool,
    sample_idx: set[str] | None = None,
    breaker: CircuitBreaker | None = None,
) -> dict[str, int]:
    ensure_dirs()
    api_key = get_api_key()
    if breaker is None:
        breaker = CircuitBreaker(enabled=False)

    variants, neutral, _coverage = load_variants()
    joins = build_join_table(variants, neutral)

    selected = _select_retest_items(
        variants_to_run=variants_to_run,
        fraction=fraction,
        seed=seed,
        resume=resume,
        sample_idx=sample_idx,
    )

    items_by_variant: dict[str, list[tuple[str, dict]]] = {}
    for variant in variants_to_run:
        ids_to_retest = set(selected.get(variant, []))
        if not ids_to_retest:
            items_by_variant[variant] = []
            continue
        df = joins[variant]
        rows = [r for r in df.to_dict(orient="records") if str(r["idx"]) in ids_to_retest]
        items_by_variant[variant] = [(variant, r) for r in rows]

    work_queue = _interleave(items_by_variant)
    total = len(work_queue)
    if total == 0:
        logging.info("Nothing to retest. Did you forget to run run_validation.py?")
        return {v: 0 for v in variants_to_run}

    writers: dict[str, Any] = {
        v: _open_jsonl(raw_jsonl_path(v, run=2)) for v in variants_to_run
    }
    writer_locks: dict[str, threading.Lock] = {
        v: threading.Lock() for v in variants_to_run
    }
    written: dict[str, int] = {v: 0 for v in variants_to_run}

    started = time.time()
    logging.info(
        "Retest run starting: variants=%s total=%d workers=%d sample_mode=%s",
        variants_to_run,
        total,
        workers,
        "on" if sample_idx is not None else "off",
    )

    progress = tqdm(total=total, desc="retest", unit="item", dynamic_ncols=True)
    aborted = False
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_item,
                    variant,
                    row,
                    run=2,
                    api_key=api_key,
                ): (variant, row)
                for variant, row in work_queue
            }
            for fut in as_completed(futures):
                variant, row = futures[fut]
                try:
                    record = fut.result()
                except Exception as exc:
                    logging.exception(
                        "Retest worker exception variant=%s idx=%s", variant, row.get("idx")
                    )
                    _append_failure(
                        {
                            "timestamp": "",
                            "variant": variant,
                            "idx": str(row.get("idx", "")),
                            "run": 2,
                            "error": repr(exc),
                            "qc_flag": "worker_exception",
                        }
                    )
                    progress.update(1)
                    if breaker.record("worker_exception"):
                        aborted = _trip_and_cancel(breaker, futures, progress)
                        break
                    continue

                line = json.dumps(record, ensure_ascii=False)
                with writer_locks[variant]:
                    writers[variant].write(line + "\n")
                    writers[variant].flush()
                written[variant] += 1
                progress.update(1)
                if breaker.record(record.get("qc_flag")):
                    aborted = _trip_and_cancel(breaker, futures, progress)
                    break
    finally:
        progress.close()
        for fh in writers.values():
            try:
                fh.close()
            except Exception:
                pass

    elapsed = time.time() - started
    logging.info(
        "Retest done %d items in %.1fs. Counts: %s%s",
        sum(written.values()),
        elapsed,
        written,
        " [ABORTED by circuit breaker]" if aborted else "",
    )
    if aborted:
        logging.error("Circuit breaker tripped: %s. Stats: %s", breaker.reason, breaker.stats())
    return written


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Retest 10% of items for reliability.")
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Worker threads (default %(default)s).",
    )
    parser.add_argument(
        "--variants",
        type=str,
        default=",".join(VARIANT_KEYS),
        help="Comma-separated variant keys (default all 8).",
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=RELIABILITY_FRACTION,
        help="Sampling fraction per variant (default %(default)s).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=RANDOM_STATE,
        help="RNG seed (default %(default)s).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip idx already present in <variant>_retest.jsonl.",
    )
    parser.add_argument(
        "--use-sample",
        action="store_true",
        help=(
            "Restrict the retest pool to idx listed in --sample-from before "
            "the item_quality quartile stratification."
        ),
    )
    parser.add_argument(
        "--sample-from",
        type=Path,
        default=SAMPLED_IDX_CSV,
        help=(
            "Path to sampled_idx.csv (used only when --use-sample is set; "
            "default %(default)s)."
        ),
    )
    parser.add_argument(
        "--no-abort",
        action="store_true",
        help="Disable the circuit breaker (run will not auto-stop on failures).",
    )
    parser.add_argument(
        "--abort-window",
        type=int,
        default=CB_WINDOW,
        help="Rolling window size for failure-rate check (default %(default)s).",
    )
    parser.add_argument(
        "--abort-rate",
        type=float,
        default=CB_FAILURE_RATE,
        help="Abort when failure rate over the window reaches this fraction (default %(default)s).",
    )
    parser.add_argument(
        "--abort-consecutive",
        type=int,
        default=CB_CONSECUTIVE,
        help="Abort after N consecutive failures (default %(default)s).",
    )
    parser.add_argument(
        "--abort-min-samples",
        type=int,
        default=CB_MIN_SAMPLES,
        help="Minimum results before the rate check can trip (default %(default)s).",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    _configure_logging()

    requested = [v.strip() for v in args.variants.split(",") if v.strip()]
    unknown = [v for v in requested if v not in VARIANT_KEYS]
    if unknown:
        print(
            f"ERROR: unknown variant(s) {unknown}. Valid keys: {VARIANT_KEYS}",
            file=sys.stderr,
        )
        return 2

    try:
        get_api_key()
    except EnvironmentError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    sample_idx: set[str] | None = None
    if args.use_sample:
        sample_idx = _load_sampled_idx(args.sample_from)
        print(
            f"[sample mode] restricting retest pool to {len(sample_idx)} idx "
            f"from {args.sample_from}"
        )
        logging.info(
            "Sample mode ON: %d idx loaded from %s", len(sample_idx), args.sample_from
        )
    else:
        print("[full-census mode] no idx filter applied to retest pool")
        logging.info("Sample mode OFF: retest pool drawn from full run-1 set")

    breaker = CircuitBreaker(
        window=args.abort_window,
        rate=args.abort_rate,
        consecutive=args.abort_consecutive,
        min_samples=args.abort_min_samples,
        enabled=not args.no_abort,
    )
    if breaker.enabled:
        print(
            f"[circuit breaker] ON: trips on {args.abort_consecutive} "
            f"consecutive failures or >={args.abort_rate:.0%} failure rate "
            f"over last {args.abort_window} results (min {args.abort_min_samples})."
        )
    else:
        print("[circuit breaker] OFF")

    written = run_retest(
        variants_to_run=requested,
        workers=args.workers,
        fraction=args.fraction,
        seed=args.seed,
        resume=args.resume,
        sample_idx=sample_idx,
        breaker=breaker,
    )
    print("Retest records written per variant:")
    for variant in requested:
        print(f"  {variant}: {written.get(variant, 0)}")
    if breaker.tripped:
        print(f"\n[circuit breaker] Retest aborted: {breaker.reason}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
