import pandas as pd
import numpy as np
from scipy.stats import ks_2samp
import matplotlib.pyplot as plt


# -----------------------------------------------------------------------
# Step 1 & 2 — Load Datasets
# -----------------------------------------------------------------------
real = pd.read_csv("employee_salaries_2025.csv")
generated = pd.read_csv("out/employee_salary/Employee.csv")

# Standardize numerical data types
real['Base Salary'] = pd.to_numeric(real['Base Salary'], errors="coerce")
generated['base_salary'] = pd.to_numeric(generated['base_salary'], errors="coerce")

print("Real dataset loaded:", real.shape)
print("Generated dataset loaded:", generated.shape)

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
# Step 4 — Run Comparisons
# -----------------------------------------------------------------------
print("\n" + "="*60)
print("EVALUATION REPORT")
print("="*60)

mae_results = {}
ks_stats = {}
ks_pvals = {}

# [1] Categorical Distribution: Gender
# Adjust 'gender' case to match your CSV header if needed
mae_results["gender"] = compare_distribution(
    real["Gender"], generated["gender"], "Gender"
)

# [2] Numeric stats: Base Salary
mae_results["base_salary"], ks_stats["base_salary"], ks_pvals["base_salary"] = compare_numeric(
    real["Base Salary"].dropna(),
    generated["base_salary"],
    "Base Salary"
)

# -----------------------------------------------------------------------
# Step 5 — Summary Table (Same Format)
# -----------------------------------------------------------------------

# --- 1. Calculate Individual Normalised MAEs ---
norm_mae = {
    "gender":      mae_results["gender"],
    "base_salary": mae_results["base_salary"] / real["Base Salary"].mean()
}

# --- 2. Calculate Overall Score ---
overall_mae = np.mean(list(norm_mae.values()))

# --- 3. Print the Enhanced Summary Table ---
print("\n" + "="*60)
print("SUMMARY — EVALUATION METRICS")
print("="*60)

summary = pd.DataFrame({
    "Column":         ["gender", "base_salary"],
    "Raw MAE":        [round(mae_results["gender"], 4), round(mae_results["base_salary"], 4)],
    "Normalised MAE": [round(norm_mae["gender"], 4), round(norm_mae["base_salary"], 4)],
    "KS Stat":        ["N/A", round(ks_stats["base_salary"], 4)],
    "p-value":        ["N/A", round(ks_pvals["base_salary"], 4)]
})

print(summary.to_string(index=False))

print("-" * 60)
print(f"OVERALL MAE SCORE: {overall_mae:.4f}")
print("Interpretation: 0.0 = Perfect match, 1.0 = No similarity")
print("="*60)

# -----------------------------------------------------------------------
# Visualizations (Using custom col names)
# -----------------------------------------------------------------------

def plot_numeric_hist_custom(real_df, gen_df, real_col, gen_col, bins=30):
    plt.figure(figsize=(8, 4))
    plt.hist(real_df[real_col].dropna(), bins=bins, alpha=0.5, label="Real", density=True)
    plt.hist(gen_df[gen_col].dropna(), bins=bins, alpha=0.5, label="Generated", density=True)
    plt.title(f"Distribution Comparison: {real_col}")
    plt.xlabel(real_col)
    plt.ylabel("Density")
    plt.legend()
    plt.tight_layout()
    plt.show()

def plot_categorical_bar_custom(real_df, gen_df, real_col, gen_col):
    real_dist = real_df[real_col].value_counts(normalize=True)
    gen_dist = gen_df[gen_col].value_counts(normalize=True)
    all_keys = sorted(set(real_dist.index).union(set(gen_dist.index)))
    real_vals = [real_dist.get(k, 0) for k in all_keys]
    gen_vals = [gen_dist.get(k, 0) for k in all_keys]
    x = np.arange(len(all_keys))
    plt.figure(figsize=(10, 4))
    plt.bar(x - 0.2, real_vals, width=0.4, label="Real")
    plt.bar(x + 0.2, gen_vals, width=0.4, label="Generated")
    plt.xticks(x, all_keys)
    plt.ylabel("Proportion")
    plt.title(f"Categorical Distribution: {real_col}")
    plt.legend()
    plt.show()

# Run plots
plot_numeric_hist_custom(real, generated, "Base Salary", "base_salary")
plot_categorical_bar_custom(real, generated, "Gender", "gender")