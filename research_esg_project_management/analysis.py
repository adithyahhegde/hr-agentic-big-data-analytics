from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

df = pd.read_csv(ROOT / "published_metrics.csv")

# Dataset facts explicitly reported by the source.
N_PROJECTS = 33
TOTAL_VALUE_USD = 2_300_000_000
N_METRICS = len(df)
MIN_PROJECTS_FOR_SELECTED_METRIC = N_PROJECTS / 3  # source selection rule

coverage = (df.groupby("dimension").size()
              .reindex(["Environmental", "Social", "Governance"], fill_value=0)
              .rename("metric_count")
              .reset_index())
coverage["share_pct"] = coverage["metric_count"] / N_METRICS * 100
coverage.to_csv(OUT / "table_esg_dimension_coverage.csv", index=False)

summary = pd.DataFrame({
    "quantity": [N_PROJECTS, TOTAL_VALUE_USD, TOTAL_VALUE_USD/N_PROJECTS, N_METRICS, MIN_PROJECTS_FOR_SELECTED_METRIC],
    "unit": ["projects", "USD total construction value", "USD average project value (derived)", "quantitative benchmark metrics", "projects (one-third threshold)"],
    "source_basis": ["published study", "published study", "derived from published study", "published study", "derived from source selection rule"]
})
summary.to_csv(OUT / "table_dataset_summary.csv", index=False)

bench = df.dropna(subset=["benchmark_value"])[["metric","dimension","benchmark_value","unit"]]
bench.to_csv(OUT / "table_verified_benchmarks.csv", index=False)

# Figure: dimension coverage
fig, ax = plt.subplots(figsize=(7.2, 4.0))
ax.bar(coverage["dimension"], coverage["share_pct"])
ax.set_ylabel("Share of 12 quantitative metrics (%)")
ax.set_ylim(0, 85)
ax.set_title("Coverage of measurable ESG dimensions")
for i, v in enumerate(coverage["share_pct"]):
    ax.text(i, v + 2, f"{v:.1f}%", ha="center")
fig.tight_layout()
fig.savefig(OUT / "figure_esg_dimension_coverage.png", dpi=220, bbox_inches="tight")
plt.close(fig)

# Figure: verified published benchmark values, shown separately because units differ.
fig, axes = plt.subplots(1, 2, figsize=(8.0, 3.8))
axes[0].bar(["Water use"], [32000])
axes[0].set_ylabel("Gallons per $1M bid price")
axes[0].set_title("Published water benchmark")
axes[0].text(0, 32000 * 0.05, "32,000", ha="center")
axes[1].bar(["Vegetated area"], [28])
axes[1].set_ylabel("Percent of total area")
axes[1].set_ylim(0, 35)
axes[1].set_title("Published vegetation benchmark")
axes[1].text(0, 28 + 1, "28%", ha="center")
fig.tight_layout()
fig.savefig(OUT / "figure_verified_benchmarks.png", dpi=220, bbox_inches="tight")
plt.close(fig)

print("ESG dimension coverage")
print(coverage.to_string(index=False))
print("\nDataset summary")
print(summary.to_string(index=False))
print("\nVerified published benchmark values")
print(bench.to_string(index=False))
