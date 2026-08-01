"""
Main census runner for the DilemmaValidation experiment.

Dispatches all (variant, idx) pairs through a ThreadPoolExecutor against
Gemini, writes one JSON record per result to results/raw/<variant>.jsonl
(flushed each line), and supports `--resume` by skipping already-completed
idx values found in those JSONL files.

Variants are interleaved (round-robin) so a slow variant does not stall
the others. Failures are appended to logs/failed_items.csv for re-run.

Usage:
  python run_validation.py                          # full census, all 8 variants
  python run_validation.py --variants CN,CT         # subset of variants
  python run_validation.py --workers 16             # bump concurrency
  python run_validation.py --resume                 # skip done idx, append more
  python run_validation.py --variants CN --limit 5  # smoke test
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import sys
import threading
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from tqdm import tqdm

from config import (
    CB_CONSECUTIVE,
    CB_FAILURE_RATE,
    CB_MIN_SAMPLES,
    CB_WINDOW,
    DEFAULT_WORKERS,
    FAILED_ITEMS_CSV,
    MODEL_NAME,
    RAW_TEXT_TRUNCATE_BYTES,
    RUN_LOG,
    SAMPLED_IDX_CSV,
    VARIANT_KEYS,
    ensure_dirs,
    get_api_key,
    raw_jsonl_path,
)
import pandas as pd

from dataset_loader import build_join_table, load_variants
from gemini_client import GeminiCallError, call_gemini
from prompts import SYSTEM, render_user_prompt


def _load_sampled_idx(path: Path) -> set[str]:
    """Return the set of idx (as strings) from a sampled_idx.csv file."""
    if not path.is_file():
        raise FileNotFoundError(
            f"--use-sample requested but {path} does not exist. "
            "Run run_stratified_sampling.py first."
        )
    df = pd.read_csv(path)
    if "idx" not in df.columns:
        raise ValueError(f"Sample CSV missing 'idx' column: {path}")
    return {str(x).strip() for x in df["idx"].tolist() if str(x).strip()}


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


def _prompt_hash(neutral_text: str, emotional_text: str, action1: str, action2: str) -> str:
    rendered = render_user_prompt(neutral_text, emotional_text, action1, action2)
    payload = SYSTEM + "\n\n" + rendered
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _truncate(text: str | None, max_bytes: int = RAW_TEXT_TRUNCATE_BYTES) -> str:
    if not text:
        return ""
    encoded = text.encode("utf-8")
    if len(encoded) <= max_bytes:
        return text
    return encoded[:max_bytes].decode("utf-8", errors="ignore")


def _load_done_idx(path: Path) -> set[str]:
    """Read an existing JSONL and return the set of idx already recorded."""
    if not path.is_file():
        return set()
    done: set[str] = set()
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            idx_val = rec.get("idx")
            if idx_val is not None:
                done.add(str(idx_val))
    return done


def _interleave_round_robin(
    items_by_variant: dict[str, list[tuple[str, dict]]]
) -> list[tuple[str, dict]]:
    """
    Round-robin merge across variants so workers process variants in lockstep.
    Each item is (variant_key, row_dict).
    """
    iters = {k: iter(v) for k, v in items_by_variant.items()}
    out: list[tuple[str, dict]] = []
    while iters:
        for key in list(iters.keys()):
            try:
                out.append(next(iters[key]))
            except StopIteration:
                iters.pop(key)
    return out


def _open_jsonl(path: Path) -> Any:
    path.parent.mkdir(parents=True, exist_ok=True)
    return path.open("a", encoding="utf-8")


def _trip_and_cancel(
    breaker: "CircuitBreaker",
    futures: dict[Any, Any],
    progress: Any,
) -> bool:
    """Log the trip, cancel queued futures, advance the bar for cancelled ones."""
    stats = breaker.stats()
    cancelled = 0
    for f in futures:
        if not f.done() and f.cancel():
            cancelled += 1
    if progress is not None and cancelled:
        progress.update(cancelled)
    print(
        f"\n[circuit breaker] ABORTING: {breaker.reason}. "
        f"Cancelled {cancelled} queued items, finishing in-flight. "
        f"Stats: {stats}",
        file=sys.stderr,
    )
    logging.error(
        "Circuit breaker tripped: %s. Cancelled %d queued futures. Stats: %s",
        breaker.reason,
        cancelled,
        stats,
    )
    return True


def _append_failure(row: dict[str, Any]) -> None:
    new_file = not FAILED_ITEMS_CSV.is_file()
    FAILED_ITEMS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with FAILED_ITEMS_CSV.open("a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["timestamp", "variant", "idx", "run", "error", "qc_flag"],
        )
        if new_file:
            writer.writeheader()
        writer.writerow(row)


class CircuitBreaker:
    """Auto-abort a run when recent results look structurally broken.

    Two independent trip conditions:

    - **Streak**: ``consecutive`` failures in a row.
    - **Rate**: failure rate over the last ``window`` results is at least
      ``rate``, evaluated only after ``min_samples`` results have been seen.

    A failure is any qc_flag in :attr:`FAILURE_FLAGS`. ``ok`` and ``clipped``
    both count as successes (clipped means the JSON parsed and only had
    out-of-range numbers nudged back into the valid scale).

    Thread-safe via an internal lock; safe to call from the as_completed loop
    even though our main thread is the only consumer today.

    Set any of ``window``, ``consecutive``, ``rate`` to ``0`` (or pass
    ``enabled=False``) to disable the corresponding check or the whole breaker.
    """

    FAILURE_FLAGS: frozenset[str] = frozenset(
        {"parse_error", "refusal", "network_failed", "worker_exception"}
    )

    def __init__(
        self,
        *,
        window: int = CB_WINDOW,
        rate: float = CB_FAILURE_RATE,
        consecutive: int = CB_CONSECUTIVE,
        min_samples: int = CB_MIN_SAMPLES,
        enabled: bool = True,
    ) -> None:
        self._enabled = enabled and window > 0 and (rate > 0 or consecutive > 0)
        self._window: deque[int] = deque(maxlen=max(window, 1))
        self._rate = rate
        self._consecutive_limit = consecutive
        self._min_samples = min_samples
        self._consecutive = 0
        self._tripped = False
        self._reason = ""
        self._lock = threading.Lock()
        self._total_seen = 0
        self._total_failed = 0

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def tripped(self) -> bool:
        return self._tripped

    @property
    def reason(self) -> str:
        return self._reason

    def stats(self) -> dict[str, Any]:
        with self._lock:
            window_size = len(self._window)
            window_failed = sum(self._window)
            return {
                "total_seen": self._total_seen,
                "total_failed": self._total_failed,
                "consecutive_failures": self._consecutive,
                "window_size": window_size,
                "window_failed": window_failed,
                "window_rate": window_failed / window_size if window_size else 0.0,
            }

    def record(self, qc_flag: str | None) -> bool:
        """Register one result and return True iff this call caused a trip."""
        if not self._enabled or self._tripped:
            return False
        failed = (qc_flag or "worker_exception") in self.FAILURE_FLAGS
        with self._lock:
            self._total_seen += 1
            self._window.append(1 if failed else 0)
            if failed:
                self._total_failed += 1
                self._consecutive += 1
            else:
                self._consecutive = 0

            if (
                self._consecutive_limit > 0
                and self._consecutive >= self._consecutive_limit
            ):
                self._tripped = True
                self._reason = (
                    f"{self._consecutive} consecutive failures "
                    f"(limit {self._consecutive_limit})"
                )
                return True

            if (
                self._rate > 0
                and len(self._window) >= self._min_samples
            ):
                rate = sum(self._window) / len(self._window)
                if rate >= self._rate:
                    self._tripped = True
                    self._reason = (
                        f"failure rate {rate:.0%} over last "
                        f"{len(self._window)} results "
                        f">= threshold {self._rate:.0%}"
                    )
                    return True

            return False


def _process_item(
    variant: str,
    row: dict[str, Any],
    *,
    run: int,
    api_key: str,
) -> dict[str, Any]:
    """Run a single API call and return the JSONL record (parsed result or error)."""
    idx = str(row["idx"])
    neutral_text = str(row["neutral_situation"])
    emotional_text = str(row["variant_situation"])
    action1 = str(row["action1"])
    action2 = str(row["action2"])
    phash = _prompt_hash(neutral_text, emotional_text, action1, action2)

    record: dict[str, Any] = {
        "variant": variant,
        "idx": idx,
        "run": run,
        "timestamp": _now_iso(),
        "model": MODEL_NAME,
        "prompt_hash": phash,
    }

    try:
        parsed, qc_flag, raw_text = call_gemini(
            neutral_text=neutral_text,
            emotional_text=emotional_text,
            action1=action1,
            action2=action2,
            api_key=api_key,
        )
        record.update(
            {
                "semantic_sim": parsed.get("semantic_sim"),
                "semantic_justification": parsed.get("semantic_justification", ""),
                "emotions": parsed.get("emotions", []),
                "emotion_naturalness": parsed.get("emotion_naturalness"),
                "emotion_coherence": parsed.get("emotion_coherence"),
                "emotion_justification": parsed.get("emotion_justification", ""),
                "qc_flag": qc_flag,
                "raw_text": _truncate(raw_text),
                "error": None,
            }
        )
    except GeminiCallError as exc:
        record.update(
            {
                "semantic_sim": None,
                "semantic_justification": "",
                "emotions": [],
                "emotion_naturalness": None,
                "emotion_coherence": None,
                "emotion_justification": "",
                "qc_flag": "network_failed",
                "raw_text": "",
                "error": str(exc),
            }
        )

    return record


def _build_work_queue(
    variants_to_run: list[str],
    joins: dict[str, Any],
    *,
    resume: bool,
    limit: int | None,
    run: int,
    sample_idx: set[str] | None = None,
) -> list[tuple[str, dict]]:
    """Build the round-robin work queue, honoring --use-sample/--resume/--limit."""
    items_by_variant: dict[str, list[tuple[str, dict]]] = {}
    for variant in variants_to_run:
        df = joins[variant]
        rows = df.to_dict(orient="records")
        if sample_idx is not None:
            rows = [r for r in rows if str(r["idx"]) in sample_idx]
        if resume:
            done = _load_done_idx(raw_jsonl_path(variant, run=run))
            rows = [r for r in rows if str(r["idx"]) not in done]
        if limit is not None:
            rows = rows[:limit]
        items_by_variant[variant] = [(variant, r) for r in rows]
    return _interleave_round_robin(items_by_variant)


def run_census(
    variants_to_run: list[str],
    *,
    workers: int,
    resume: bool,
    limit: int | None,
    run: int = 1,
    sample_idx: set[str] | None = None,
    breaker: CircuitBreaker | None = None,
) -> dict[str, int]:
    """
    Drive the census for the requested variants.

    Returns a dict {variant -> number of new records written}. If a
    ``CircuitBreaker`` is supplied and trips mid-run, queued futures are
    cancelled, in-flight calls finish, and the function returns the partial
    counts.
    """
    ensure_dirs()
    api_key = get_api_key()
    if breaker is None:
        breaker = CircuitBreaker(enabled=False)

    variants, neutral, _coverage = load_variants()
    joins = build_join_table(variants, neutral)
    for variant in variants_to_run:
        if variant not in joins:
            raise KeyError(f"Unknown variant: {variant}")

    work_queue = _build_work_queue(
        variants_to_run=variants_to_run,
        joins=joins,
        resume=resume,
        limit=limit,
        run=run,
        sample_idx=sample_idx,
    )
    total = len(work_queue)
    if total == 0:
        logging.info("Nothing to do (all items already complete or limit=0).")
        return {v: 0 for v in variants_to_run}

    writer_locks: dict[str, threading.Lock] = {
        v: threading.Lock() for v in variants_to_run
    }
    writers: dict[str, Any] = {
        v: _open_jsonl(raw_jsonl_path(v, run=run)) for v in variants_to_run
    }
    written: dict[str, int] = {v: 0 for v in variants_to_run}

    started = time.time()
    logging.info(
        "Starting %d calls across variants=%s workers=%d resume=%s limit=%s run=%d "
        "sample_mode=%s",
        total,
        variants_to_run,
        workers,
        resume,
        limit,
        run,
        "on" if sample_idx is not None else "off",
    )

    progress = tqdm(total=total, desc="validation", unit="item", dynamic_ncols=True)
    aborted = False
    try:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(
                    _process_item,
                    variant,
                    row,
                    run=run,
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
                        "Worker exception variant=%s idx=%s",
                        variant,
                        row.get("idx"),
                    )
                    _append_failure(
                        {
                            "timestamp": _now_iso(),
                            "variant": variant,
                            "idx": str(row.get("idx", "")),
                            "run": run,
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

                if record.get("qc_flag") in ("parse_error", "refusal", "network_failed"):
                    _append_failure(
                        {
                            "timestamp": record["timestamp"],
                            "variant": variant,
                            "idx": record["idx"],
                            "run": run,
                            "error": record.get("error") or record.get("qc_flag"),
                            "qc_flag": record["qc_flag"],
                        }
                    )

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
        "Completed %d items in %.1fs (%.2f items/sec). Counts: %s%s",
        sum(written.values()),
        elapsed,
        sum(written.values()) / elapsed if elapsed > 0 else 0.0,
        written,
        " [ABORTED by circuit breaker]" if aborted else "",
    )
    if aborted:
        stats = breaker.stats()
        logging.error(
            "Circuit breaker tripped: %s. Stats: %s",
            breaker.reason,
            stats,
        )
    return written


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the DilemmaValidation main census against Gemini."
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=DEFAULT_WORKERS,
        help="Number of concurrent worker threads (default %(default)s).",
    )
    parser.add_argument(
        "--variants",
        type=str,
        default=",".join(VARIANT_KEYS),
        help="Comma-separated variant keys to run (default: all 8).",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip idx already present in results/raw/<variant>.jsonl.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on items per variant (smoke test).",
    )
    parser.add_argument(
        "--run",
        type=int,
        default=1,
        choices=(1, 2),
        help="1 = main census (default), 2 = retest pass.",
    )
    parser.add_argument(
        "--use-sample",
        action="store_true",
        help=(
            "Restrict the work queue to idx listed in --sample-from "
            "(default: config.SAMPLED_IDX_CSV). Off => full census."
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
        help=(
            "Abort when failure rate over --abort-window reaches this fraction "
            "(default %(default)s)."
        ),
    )
    parser.add_argument(
        "--abort-consecutive",
        type=int,
        default=CB_CONSECUTIVE,
        help=(
            "Abort after N consecutive failures regardless of window "
            "(default %(default)s)."
        ),
    )
    parser.add_argument(
        "--abort-min-samples",
        type=int,
        default=CB_MIN_SAMPLES,
        help=(
            "Minimum results before the rate check can trip "
            "(default %(default)s)."
        ),
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
            f"[sample mode] restricting to {len(sample_idx)} idx "
            f"from {args.sample_from}"
        )
        logging.info(
            "Sample mode ON: %d idx loaded from %s", len(sample_idx), args.sample_from
        )
    else:
        print("[full-census mode] no idx filter applied")
        logging.info("Sample mode OFF: running full census")

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

    written = run_census(
        variants_to_run=requested,
        workers=args.workers,
        resume=args.resume,
        limit=args.limit,
        run=args.run,
        sample_idx=sample_idx,
        breaker=breaker,
    )
    print("Written records per variant:")
    for variant in requested:
        print(f"  {variant}: {written.get(variant, 0)}")
    if breaker.tripped:
        print(f"\n[circuit breaker] Run aborted: {breaker.reason}", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
