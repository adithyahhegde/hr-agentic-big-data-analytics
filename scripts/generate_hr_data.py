"""Generate deterministic HR datasets for evaluation and scalability experiments."""
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path

FIELDS = ["Employee ID", "Age", "Department", "Job Satisfaction", "Monthly Income", "Years at Company", "Overtime", "Attrition"]
DEPARTMENTS = ["Sales", "Research & Development", "Human Resources"]


def generate(path: Path, rows: int, messy: bool = False, duplicate_rate: float = 0.0, seed: int = 42) -> None:
    rng = random.Random(seed)
    path.parent.mkdir(parents=True, exist_ok=True)
    data: list[list[object]] = []
    for i in range(rows):
        age = rng.randint(20, 60)
        income = rng.randint(2500, 18000)
        years = rng.randint(0, min(25, age - 18))
        overtime = rng.choice(["Yes", "No"])
        satisfaction = rng.randint(1, 4)
        department = rng.choice(DEPARTMENTS)
        attrition = "Yes" if (overtime == "Yes" and satisfaction <= 2 and rng.random() < 0.28) else "No"
        row = [f"E{i+1:07d}", age, department, satisfaction, income, years, overtime, attrition]
        if messy and rng.random() < 0.08:
            row[2] = department.lower().replace(" ", "_")
        if messy and rng.random() < 0.05:
            row[4] = ""
        if messy and rng.random() < 0.03:
            row[7] = ""
        data.append(row)
    duplicates = int(rows * duplicate_rate)
    for _ in range(duplicates):
        if data:
            data.append(list(rng.choice(data)))
    headers = FIELDS if not messy else ["Employee_ID", "employee age", "dept", "satisfaction", "monthly_income", "tenure", "Over Time", "left_company"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--rows", type=int, default=1000)
    parser.add_argument("--messy", action="store_true")
    parser.add_argument("--duplicate-rate", type=float, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    generate(args.output, args.rows, args.messy, args.duplicate_rate, args.seed)
