from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path
from typing import Any

NUMERIC_FIELDS = {"age", "tenure_years", "salary", "performance_rating", "bonus", "monthly_hours", "satisfaction_score", "engagement_score"}


def _to_number(value: str) -> float | None:
    text = value.strip().replace(",", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def analyze_csv(path: Path, mappings: dict[str, str], max_categories: int = 5) -> dict[str, Any]:
    source_to_canonical = {source: canonical for source, canonical in mappings.items() if canonical != "unknown"}
    numeric: dict[str, list[float]] = {}
    categorical: dict[str, Counter[str]] = {}
    missing: Counter[str] = Counter()
    row_count = 0
    duplicate_rows = 0
    previous_rows: set[tuple[str, ...]] = set()

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise ValueError("The stored dataset has no header row.")
        headers = list(reader.fieldnames)
        canonical_to_source = {canonical: source for source, canonical in source_to_canonical.items()}
        for row in reader:
            row_count += 1
            row_tuple = tuple((row.get(header) or "") for header in headers)
            if row_tuple in previous_rows:
                duplicate_rows += 1
            else:
                previous_rows.add(row_tuple)
            for canonical, source in canonical_to_source.items():
                value = (row.get(source) or "").strip()
                if not value:
                    missing[canonical] += 1
                elif canonical in NUMERIC_FIELDS:
                    number = _to_number(value)
                    if number is not None:
                        numeric.setdefault(canonical, []).append(number)
                    else:
                        missing[canonical] += 1
                else:
                    categorical.setdefault(canonical, Counter())[value] += 1

    numeric_summary = []
    for field, values in sorted(numeric.items()):
        numeric_summary.append({"field": field, "count": len(values), "min": round(min(values), 4), "max": round(max(values), 4), "mean": round(sum(values) / len(values), 4)})

    categorical_summary = []
    for field, counts in sorted(categorical.items()):
        total = sum(counts.values())
        categorical_summary.append({"field": field, "count": total, "distinct": len(counts), "top_values": [{"value": value, "count": count, "share": round(count / total, 4)} for value, count in counts.most_common(max_categories)]})

    insights: list[dict[str, Any]] = []
    for field, count in sorted(missing.items()):
        if row_count and count / row_count >= 0.20:
            insights.append({"type": "DATA_QUALITY", "severity": "WARNING", "title": f"High missingness in {field}", "evidence": f"{count:,} of {row_count:,} rows are missing or non-numeric for this mapped field."})
    if row_count and duplicate_rows:
        insights.append({"type": "DATA_QUALITY", "severity": "WARNING", "title": "Duplicate records detected", "evidence": f"{duplicate_rows:,} duplicate rows were observed ({duplicate_rows / row_count:.1%} of the dataset)."})

    attrition_source = canonical_to_source.get("attrition")
    if attrition_source:
        counts: Counter[str] = Counter()
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                value = (row.get(attrition_source) or "").strip().lower()
                if value:
                    counts[value] += 1
        total = sum(counts.values())
        if total:
            positive = sum(v for k, v in counts.items() if k in {"yes", "y", "true", "1", "left", "terminated", "attrition"})
            if positive:
                insights.append({"type": "WORKFORCE", "severity": "INFO", "title": "Attrition signal available", "evidence": f"{positive:,} of {total:,} non-empty attrition labels are in the positive class ({positive / total:.1%})."})
            categorical_summary.append({"field": "attrition", "count": total, "distinct": len(counts), "top_values": [{"value": k, "count": v, "share": round(v / total, 4)} for k, v in counts.most_common(max_categories)]})

    return {"row_count": row_count, "duplicate_row_count": duplicate_rows, "numeric_summary": numeric_summary, "categorical_summary": categorical_summary, "missing_by_field": [{"field": field, "missing": count, "rate": round(count / row_count, 4) if row_count else 0} for field, count in sorted(missing.items())], "insights": insights}
