"""Measure deterministic local analytics execution across increasing fixture sizes."""
from __future__ import annotations

import argparse
import json
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any

from app.services.analytics import analyze_csv
from scripts.benchmark import make_fixture, MAPPINGS

DEFAULT_SIZES = (100, 1_000, 10_000)


def run_scalability(sizes: tuple[int, ...] = DEFAULT_SIZES, seed: int = 42, scenario: str = "clean", repeats: int = 1) -> dict[str, Any]:
    if not sizes or any(int(size) < 1 for size in sizes):
        raise ValueError("sizes must contain only positive values")
    if repeats < 1 or repeats > 5:
        raise ValueError("repeats must be between 1 and 5")
    ordered_sizes = tuple(sorted(set(int(size) for size in sizes)))
    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="hr_scalability_") as tmp:
        root = Path(tmp)
        for rows in ordered_sizes:
            path = root / f"benchmark-{rows}.csv"
            make_fixture(path, rows, seed, scenario)
            timings: list[float] = []
            result: dict[str, Any] = {}
            for _ in range(repeats):
                started = time.perf_counter()
                result = analyze_csv(path, MAPPINGS)
                timings.append(time.perf_counter() - started)
            elapsed = statistics.median(timings)
            records.append({
                "rows": rows,
                "bytes": path.stat().st_size,
                "elapsed_seconds": round(elapsed, 6),
                "rows_per_second": round(rows / max(elapsed, 1e-9), 2),
                "duplicate_rows": result.get("duplicate_row_count", 0),
                "repeat_count": repeats,
            })

    baseline = records[0]["elapsed_seconds"]
    for record in records:
        record["size_multiplier"] = round(record["rows"] / ordered_sizes[0], 4)
        record["elapsed_multiplier"] = round(record["elapsed_seconds"] / max(baseline, 1e-9), 4)
    return {
        "protocol": "local_scalability_v1",
        "seed": seed,
        "scenario": scenario,
        "sizes": list(ordered_sizes),
        "repeats": repeats,
        "engine": "LOCAL",
        "records": records,
        "methodology": {
            "metric": "wall_clock_seconds_and_rows_per_second",
            "timing_scope": "CSV fixture read plus deterministic descriptive analytics",
            "ordering": "sizes sorted ascending; elapsed multipliers normalized to smallest size",
            "limitation": "CI timings are environment-dependent and are measurements, not universal performance guarantees",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=list(DEFAULT_SIZES))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--scenario", default="clean")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run_scalability(tuple(args.sizes), args.seed, args.scenario, args.repeats)
    text = json.dumps(result, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
