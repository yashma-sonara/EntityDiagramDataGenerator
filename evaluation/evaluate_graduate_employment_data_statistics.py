import requests
import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
import time
import io


# -----------------------------------------------------------------------
# Step 1 — load real dataset
# -----------------------------------------------------------------------


def fetch_real_data(dataset_id: str) -> pd.DataFrame:
    base = "https://api-open.data.gov.sg/v1/public/api/datasets"

    session = requests.Session()

    session.get(f"{base}/{dataset_id}/initiate-download")
    time.sleep(2)

    for _ in range(5):
        poll = session.get(f"{base}/{dataset_id}/poll-download")
        data = poll.json()

        if data and data.get("data"):
            url = data["data"].get("url")
            if url:
                csv_resp = session.get(url)
                return pd.read_csv(io.StringIO(csv_resp.text))

        time.sleep(2)

    raise RuntimeError("Could not fetch dataset after retries")


real = fetch_real_data("d_3c55210de27fcccda2ed0c63fdd2b352")

# clean salary columns — replace 'na', '-', empty strings with NaN
salary_cols = [
    "gross_monthly_mean", "gross_monthly_median",
    "gross_mthly_25_percentile", "gross_mthly_75_percentile",
    "employment_rate_overall", "employment_rate_ft_perm"
]
for col in salary_cols:
    real[col] = pd.to_numeric(real[col], errors="coerce")

print("Real dataset loaded:", real.shape)


# -----------------------------------------------------------------------
# Step 2 — load generated dataset
# -----------------------------------------------------------------------


generated = pd.read_csv("out/graduate_employment/Graduate.csv")
print("Generated dataset loaded:", generated.shape)


# -----------------------------------------------------------------------
# Step 3 — comparison helpers
# -----------------------------------------------------------------------


def compare_distribution(col_real, col_gen, label):
    """Compare value_counts distributions and compute MAE."""
    real_dist = col_real.value_counts(normalize=True).sort_index()
    gen_dist  = col_gen.value_counts(normalize=True).sort_index()

    # align indices so we can subtract
    all_keys  = real_dist.index.union(gen_dist.index)
    real_dist = real_dist.reindex(all_keys, fill_value=0)
    gen_dist  = gen_dist.reindex(all_keys, fill_value=0)

    mae = (real_dist - gen_dist).abs().mean()

    df = pd.DataFrame({
        "real_%":      (real_dist * 100).round(1),
        "generated_%": (gen_dist * 100).round(1),
        "abs_error":   (real_dist - gen_dist).abs().round(4)
    })
    print(f"\n--- {label} distribution ---")
    print(df.to_string())
    print(f"MAE: {mae:.4f}")
    return mae


def compare_numeric(col_real, col_gen, label):
    """Compare mean, std, median of a numeric column."""
    stats = pd.DataFrame({
        "metric": ["mean", "std", "median", "25th_pct", "75th_pct"],
        "real":   [
            col_real.mean(), col_real.std(), col_real.median(),
            col_real.quantile(0.25), col_real.quantile(0.75)
        ],
        "generated": [
            col_gen.mean(), col_gen.std(), col_gen.median(),
            col_gen.quantile(0.25), col_gen.quantile(0.75)
        ]
    })
    stats["abs_error"] = (stats["real"] - stats["generated"]).abs()
    mae = stats["abs_error"].mean()

    print(f"\n--- {label} numeric stats ---")
    print(stats.round(2).to_string(index=False))
    print(f"MAE: {mae:.2f}")

    ks_stat, ks_pval = ks_2samp(col_real.dropna(), col_gen.dropna())
    print(f"KS Statistic: {ks_stat:.4f}, p-value: {ks_pval:.4f}")
    return mae, ks_stat, ks_pval


# -----------------------------------------------------------------------
# Step 4 — run comparisons
# -----------------------------------------------------------------------


print("\n" + "="*60)
print("EVALUATION REPORT")
print("="*60)


mae_results = {}
ks_stats    = {}
ks_pvals    = {}

# categorical distributions
mae_results["university"] = compare_distribution(
    real["university"], generated["university"], "University"
)
mae_results["year"] = compare_distribution(
    real["year"], generated["year"], "Year"
)

# numeric columns
mae_results["gross_monthly_mean"], ks_stats["gross_monthly_mean"], ks_pvals["gross_monthly_mean"] = compare_numeric(
    real["gross_monthly_mean"].dropna(),
    generated["gross_monthly_mean"],
    "Gross Monthly Mean Salary"
)
mae_results["gross_monthly_median"], ks_stats["gross_monthly_median"], ks_pvals["gross_monthly_median"] = compare_numeric(
    real["gross_monthly_median"].dropna(),
    generated["gross_monthly_median"],
    "Gross Monthly Median Salary"
)
mae_results["employment_rate_overall"], ks_stats["employment_rate_overall"], ks_pvals["employment_rate_overall"] = compare_numeric(
    real["employment_rate_overall"].dropna(),
    generated["employment_rate_overall"],
    "Employment Rate Overall"
)


# -----------------------------------------------------------------------
# Step 5 — summary table
# -----------------------------------------------------------------------


# --- 1. Calculate Individual Normalised MAEs ---
norm_mae = {
    "university":              mae_results["university"],
    "year":                    mae_results["year"],
    "gross_monthly_mean":      mae_results["gross_monthly_mean"]      / real["gross_monthly_mean"].mean(),
    "gross_monthly_median":    mae_results["gross_monthly_median"]    / real["gross_monthly_median"].mean(),
    "employment_rate_overall": mae_results["employment_rate_overall"] / 100
}

# --- 2. Calculate Overall Score (Using Mean of Normalised values) ---
overall_mae = np.mean(list(norm_mae.values()))

# --- 3. Print the Enhanced Summary Table ---
print("\n" + "="*60)
print("SUMMARY — EVALUATION METRICS")
print("="*60)

summary = pd.DataFrame({
    "Column":         list(mae_results.keys()),
    "Raw MAE":        [round(v, 4) for v in mae_results.values()],
    "Normalised MAE": [round(norm_mae[col], 4) for col in mae_results.keys()],
    "KS Stat":        ["N/A", "N/A"] + [round(ks_stats[c], 4) for c in ["gross_monthly_mean", "gross_monthly_median", "employment_rate_overall"]],
    "p-value":        ["N/A", "N/A"] + [round(ks_pvals[c], 4) for c in ["gross_monthly_mean", "gross_monthly_median", "employment_rate_overall"]],
})

print(summary.to_string(index=False))

print("-" * 60)
print(f"OVERALL MAE SCORE: {overall_mae:.4f}")
print("Interpretation: 0.0 = Perfect match, 1.0 = No similarity")
print("="*60)
